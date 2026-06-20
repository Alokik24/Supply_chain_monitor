# tests/test_scoring_worker.py

import pytest
import numpy as np

from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import select

from redis import Redis

from src.database import AsyncSessionLocal
from src.models import SensorReading, AnomalyCase
from src.workers.scoring_worker import (
    run_scoring_cycle,
    WATERMARK_KEY,
)

redis_client = Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
)


@pytest.mark.asyncio
async def test_scoring_worker_advances_watermark():
    """
    Verify worker processes new rows and advances Redis watermark.
    """

    redis_client.delete(WATERMARK_KEY)

    line_id = f"Test_Watermark_{uuid4().hex[:8]}"

    async with AsyncSessionLocal() as session:

        now = datetime.now(timezone.utc)

        readings = [
            SensorReading(
                line_id=line_id,
                sensor_type="torque",
                value=100.0,
                timestamp=now,
            ),
            SensorReading(
                line_id=line_id,
                sensor_type="conveyor_speed",
                value=50.0,
                timestamp=now,
            ),
            SensorReading(
                line_id=line_id,
                sensor_type="fill_level",
                value=25.0,
                timestamp=now,
            ),
        ]

        result = await session.execute(
            select(SensorReading.id)
            .order_by(SensorReading.id.desc())
            .limit(1)
        )

        last_id = result.scalar() or 0

        redis_client.set(WATERMARK_KEY, last_id)

        session.add_all(readings)
        await session.commit()

        reading_ids = [r.id for r in readings]

    await run_scoring_cycle()

    new_watermark = redis_client.get(WATERMARK_KEY)

    assert new_watermark is not None
    assert int(new_watermark) >= max(reading_ids)


@pytest.mark.asyncio
async def test_scoring_worker_creates_case_when_model_flags_anomaly():
    """
    Verify worker inserts anomaly case when model predicts anomaly.
    """

    redis_client.delete(WATERMARK_KEY)

    line_id = f"Test_Alpha_{uuid4().hex[:8]}"

    async with AsyncSessionLocal() as session:

        now = datetime.now(timezone.utc)

        readings = [
            SensorReading(
                line_id=line_id,
                sensor_type="torque",
                value=999.9,
                timestamp=now,
            ),
            SensorReading(
                line_id=line_id,
                sensor_type="conveyor_speed",
                value=10.0,
                timestamp=now,
            ),
            SensorReading(
                line_id=line_id,
                sensor_type="fill_level",
                value=50.0,
                timestamp=now,
            ),
        ]

        result = await session.execute(
            select(SensorReading.id)
            .order_by(SensorReading.id.desc())
            .limit(1)
        )

        last_id = result.scalar() or 0

        redis_client.set(WATERMARK_KEY, last_id)

        session.add_all(readings)
        await session.commit()

    with (
        patch(
            "src.workers.scoring_worker.model.predict",
            return_value=np.array([1]),
        ),
        patch(
            "src.workers.scoring_worker.model.predict_proba",
            return_value=np.array([[0.0, 1.0]]),
        ),
    ):
        await run_scoring_cycle()

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(AnomalyCase)
            .where(AnomalyCase.line_id == line_id)
        )

        cases = result.scalars().all()

        assert len(cases) >= 1
        assert cases[-1].status == "FLAGGED"

    new_watermark = redis_client.get(WATERMARK_KEY)

    assert new_watermark is not None