# src/workers/scoring_worker.py
import asyncio
import logging
import joblib
import pandas as pd
from sqlalchemy import select
from redis import Redis
from src.database import AsyncSessionLocal
from src.models import SensorReading, AnomalyCase
from src.features import (
    fetch_historical_window_dataframe,
    build_feature_matrix,
    MODEL_FEATURE_COLUMNS,
)
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ScoringWorker")

# Connect to our synchronized Redis instance to track the watermark
redis_client = Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True,
)

WATERMARK_KEY = "scoring_watermark:last_processed_id"

# Safely load the pre-trained ML model artifact
try:
    model = joblib.load("models/anomaly_detector.pkl")
except FileNotFoundError:
    logger.warning(
        "Model file models/anomaly_detector.pkl missing. Using fallback Z-score logic."
    )
    model = None


async def run_scoring_cycle():
    """
    Executes a single continuous out-of-band machine scoring run.
    """
    # 1. Fetch our progress watermark location from Redis
    last_id_str = redis_client.get(WATERMARK_KEY)
    last_processed_id = int(last_id_str) if last_id_str else 0

    logger.info("=" * 60)
    logger.info(f"WORKER TICK | Watermark={last_processed_id}")

    async with AsyncSessionLocal() as db_session:
        # 2. Extract new, un-analyzed records using the fast indexed id sequence
        stmt = (
            select(SensorReading)
            .where(SensorReading.id > last_processed_id)
            .order_by(SensorReading.id.asc())
            .limit(1000)
        )
        result = await db_session.execute(stmt)
        batch_readings = result.scalars().all()

        if not batch_readings:
            logger.info("No new readings found.")
            return  # The ingestion script hasn't streamed any new data yet

        logger.info(
            f"Pulled {len(batch_readings)} new raw rows. Processing feature store matrix..."
        )

        # 3. Pull lookback history from the database
        df_historical = await db_session.run_sync(fetch_historical_window_dataframe)

        # 4. Construct the complete wide dataset context matrix
        df_current_batch = pd.DataFrame(
            [
                {
                    "id": r.id,
                    "line_id": r.line_id,
                    "sensor_type": r.sensor_type,
                    "value": r.value,
                    "timestamp": r.timestamp,
                }
                for r in batch_readings
            ]
        )

        df_combined = pd.concat([df_historical, df_current_batch]).drop_duplicates(
            subset=["id"]
        )

        # 5. Extract wide engineering columns
        feature_df = build_feature_matrix(df_combined)

        # 6. Isolate rows that belong to our new unscored chunk
        new_row_ids = [r.id for r in batch_readings]
        fallback_series = pd.Series(False, index=feature_df.index)

        chunk_mask = (
            feature_df.get("conveyor_speed_reading_id", fallback_series).isin(
                new_row_ids
            )
            | feature_df.get("fill_level_reading_id", fallback_series).isin(new_row_ids)
            | feature_df.get("torque_reading_id", fallback_series).isin(new_row_ids)
        )
        eval_df = feature_df[chunk_mask].copy()

        if eval_df.empty:
            return

        # Ensure all columns exist before passing arrays to the model
        for col in MODEL_FEATURE_COLUMNS:
            if col not in eval_df.columns:
                eval_df[col] = 0.0

        X = eval_df[MODEL_FEATURE_COLUMNS].values

        # 7. ML Inference Step
        if model:
            predictions = model.predict(X)
            if hasattr(model, "decision_function"):
                eval_df["is_anomaly"] = (predictions == -1).astype(int)
                eval_df["score"] = -model.decision_function(X)
            else:
                eval_df["is_anomaly"] = predictions.astype(int)

                probabilities = model.predict_proba(X)
                eval_df["score"] = probabilities[:, 1]
        else:
            # Fallback mathematical heuristic if model is missing
            eval_df["is_anomaly"] = (
                (eval_df["torque_z_score"].abs() > 3.0)
                | (eval_df["conveyor_speed_z_score"].abs() > 3.0)
            ).astype(int)
            eval_df["score"] = eval_df["torque_z_score"].abs()

        # 8. Flag anomalies and write clean machine-state tickets
        anomalies_caught = eval_df[eval_df["is_anomaly"] == 1]

        logger.info(
            f"Rows evaluated={len(eval_df)} | "
            f"Anomalies detected={len(anomalies_caught)}"
        )

        for _, row in anomalies_caught.iterrows():
            new_case = AnomalyCase(
                line_id=str(row["line_id"]),
                timestamp=pd.to_datetime(row["timestamp"]).to_pydatetime(),
                status="FLAGGED",
                score=float(row["score"]),
            )
            try:
                db_session.add(new_case)
                await db_session.flush()
            except Exception as e:
                logger.error(f"INSERT FAILED: {e}")
                await db_session.rollback()
                continue

            # 9. Cache features in Redis for Phase 3 toolkits
            for sensor in ["conveyor_speed", "fill_level", "torque"]:
                cache_key = f"features:{row['line_id']}:{sensor}"
                redis_client.hset(
                    cache_key,
                    mapping={
                        "rolling_mean_30m": float(row[f"{sensor}_rolling_mean"]),
                        "rolling_std_30m": float(row[f"{sensor}_rolling_std"]),
                        "z_score": float(row[f"{sensor}_z_score"]),
                    },
                )
                redis_client.expire(cache_key, 600)

        # Commit cases and advance our high-watermark pointer safely
        await db_session.commit()

        highest_id_processed = max(new_row_ids)
        redis_client.set(WATERMARK_KEY, highest_id_processed)
        logger.info(
            f"Cold-path run complete. Watermark set to: {highest_id_processed}. Flagged {len(anomalies_caught)} machine incidents."
        )


async def start_worker_daemon(interval_seconds: int = 10):
    """Continuous loop wrapper managing background scheduling."""
    while True:
        try:
            await run_scoring_cycle()
        except Exception as e:
            logger.error(f"Error caught inside cold-path execution engine loop: {e}")
        await asyncio.sleep(interval_seconds)
