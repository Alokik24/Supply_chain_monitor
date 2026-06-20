# src/main.py

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import text
from src.db import get_db_connection, redis_client
import asyncio
from src.schemas import SensorReadingCreate
from src.models import SensorReading
from src.database import get_db
from src.workers.scoring_worker import start_worker_daemon
from contextlib import asynccontextmanager
from src.routes.anomalies import router as anomaly_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup: Spawn the out-of-band machine scoring daemon
    # Set interval_seconds=5 for local development so anomalies process immediately
    scoring_task = asyncio.create_task(start_worker_daemon(interval_seconds=5))
    print(" Cold-path ML scoring worker initialized and running in background.")
    
    yield
    
    # 2. Shutdown: Cancel the loop cleanly when turning off the server
    scoring_task.cancel()
    print(" Cold-path ML scoring worker shut down cleanly.")

app = FastAPI(title="Supply Chain Anomaly Detection API", version="1.0", lifespan=lifespan)


app.include_router(anomaly_router)

@app.get("/")
def read_root():
    health_status = {"api_status": "Live-Reload Activated"}

    # Test Redis Channel Connection
    try:
        redis_client.ping()
        health_status["redis_cache"] = "Connected"
    except Exception:
        health_status["redis_cache"] = "Disconnected"

    # Test Postgres Database Connection
    db_conn = get_db_connection()
    if db_conn:
        health_status["postgres_db"] = "Connected"
        db_conn.close()
    else:
        health_status["postgres_db"] = "Disconnected"

    return health_status


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed : {str(e)}",
        )


@app.post("/readings", status_code=status.HTTP_200_OK)
async def ingest_sensor_reading(
    payload: SensorReadingCreate, db: AsyncSession = Depends(get_db)
):
    """
    Ingests single raw sensor events strictly using an idempotent atomic operation.
    If the event is a network duplicate retry, ignores the write command gracefully.
    """
    # Build clean upsert block targeting Postgres dialect rules
    stmt = insert(SensorReading).values(
        line_id=payload.line_id,
        sensor_type=payload.sensor_type,
        value=payload.value,
        timestamp=payload.timestamp,
    )

    # Enforce atomic engine deduplication via constraint check
    idempotent_stmt = stmt.on_conflict_do_nothing(constraint="uq_line_sensor_timestamp")

    try:
        result = await db.execute(idempotent_stmt)
        await db.commit()

        # Verify if record was actually written to ledger or safely skipped
        if result.rowcount == 0:
            return {
                "status": "ignored",
                "detail": "Duplicate reading processed idempotently.",
            }

        return {"status": "success", "detail": "Reading captured successfully."}

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline ingestion failure: {str(e)}",
        )
