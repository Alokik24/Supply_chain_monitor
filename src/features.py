# src/features.py
import pandas as pd
import numpy as np

SENSOR_TYPES = ["conveyor_speed", "fill_level", "torque"]
WINDOW = 30  # 30 observations representing our historical tracking window context

# Shared source-of-truth feature list for both train.py and scoring_worker.py
MODEL_FEATURE_COLUMNS = []
for sensor in SENSOR_TYPES:
    MODEL_FEATURE_COLUMNS.extend(
        [f"{sensor}_rolling_std", f"{sensor}_z_score", f"{sensor}_rate_of_change"]
    )


def pivot_to_wide(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts narrow entity-attribute-value (EAV) rows from the DB into a wide matrix.
    Safely enforces chronological sorting to ensure rolling calculations run forward.
    Tolerates missing ID columns to maintain full backward-compatibility with training splits.
    """
    if df.empty:
        return pd.DataFrame(columns=["timestamp", "line_id"] + SENSOR_TYPES)

    # 1. Pivot the raw sensor values cleanly
    df_wide = df.pivot(
        index=["timestamp", "line_id"], columns="sensor_type", values="value"
    ).reset_index()
    df_wide.columns.name = None

    # 2. FIXED: Conditional ID Guard pattern preserves the return path for training data frames
    if "id" in df.columns:
        df_ids = df.pivot(
            index=["timestamp", "line_id"], columns="sensor_type", values="id"
        ).reset_index()
        df_ids.columns.name = None

        for sensor in SENSOR_TYPES:
            if sensor in df_ids.columns:
                df_wide[f"{sensor}_reading_id"] = df_ids[sensor]

    # 3. FIXED: Moved outside the conditional block to guarantee valid outputs for all paths
    return df_wide.sort_values(by=["line_id", "timestamp"]).reset_index(drop=True)


def compute_rolling_features(df_wide: pd.DataFrame) -> pd.DataFrame:
    """
    Computes rolling metrics grouped by line_id to prevent cross-factory contamination.
    """
    df = df_wide.copy()

    for sensor in SENSOR_TYPES:
        if sensor not in df.columns:
            df[sensor] = np.nan

        grouped_roll = df.groupby("line_id")[sensor].transform(
            lambda x: x.rolling(window=WINDOW, min_periods=1).mean()
        )
        grouped_std = (
            df.groupby("line_id")[sensor]
            .transform(lambda x: x.rolling(window=WINDOW, min_periods=1).std())
            .fillna(0.0)
        )

        df[f"{sensor}_rolling_mean"] = grouped_roll
        df[f"{sensor}_rolling_std"] = grouped_std

        df[f"{sensor}_z_score"] = (df[sensor] - df[f"{sensor}_rolling_mean"]) / (
            df[f"{sensor}_rolling_std"] + 1e-6
        )

    return df


def compute_rate_of_change(df_wide: pd.DataFrame) -> pd.DataFrame:
    df = df_wide.copy()
    for sensor in SENSOR_TYPES:
        if sensor in df.columns:
            df[f"{sensor}_rate_of_change"] = (
                df.groupby("line_id")[sensor].diff().fillna(0.0)
            )
    return df


def compute_delta_from_baseline(df_wide: pd.DataFrame) -> pd.DataFrame:
    df = df_wide.copy()
    for sensor in SENSOR_TYPES:
        if sensor in df.columns:
            line_mean = df.groupby("line_id")[sensor].transform("mean")
            df[f"{sensor}_delta_from_baseline"] = df[sensor] - line_mean
    return df


def build_feature_matrix(df_narrow: pd.DataFrame) -> pd.DataFrame:
    if df_narrow.empty:
        raise ValueError("Cannot build feature matrix from empty telemetry DataFrame.")

    df = pivot_to_wide(df_narrow)
    df = compute_rolling_features(df)
    df = df.dropna(subset=[f"{s}_rolling_std" for s in SENSOR_TYPES]).copy()
    df = compute_rate_of_change(df)
    df = compute_delta_from_baseline(df)
    return df


def generate_window_fetch_query(window_size: int = 30) -> str:
    history_limit = window_size + 5
    query = f"""
    WITH ranked_readings AS (
        SELECT 
            id, 
            line_id, 
            sensor_type, 
            value, 
            timestamp,
            ROW_NUMBER() OVER (
                PARTITION BY line_id, sensor_type 
                ORDER BY timestamp DESC
            ) as rank
        FROM sensor_readings
    )
    SELECT id, line_id, sensor_type, value, timestamp
    FROM ranked_readings
    WHERE rank <= {history_limit}
    ORDER BY line_id, sensor_type, timestamp ASC;
    """
    return query


def fetch_historical_window_dataframe(
    sync_session,
    window_size: int = 30,
) -> pd.DataFrame:

    sql_query_string = generate_window_fetch_query(window_size=window_size)

    connection = sync_session.connection()

    df_narrow = pd.read_sql_query(
        sql=sql_query_string,
        con=connection,
        parse_dates=["timestamp"],
    )

    return df_narrow
