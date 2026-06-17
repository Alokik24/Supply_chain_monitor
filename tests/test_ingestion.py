import os
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

from src.database import get_db
from src.main import app

load_dotenv()

user = os.getenv("POSTGRES_USER", "postgres")
password = os.getenv("POSTGRES_PASSWORD", "postgres")
host = os.getenv("POSTGRES_HOST", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")

TEST_DATABASE_URL = (
    f"postgresql+asyncpg://{user}:{password}@{host}:{port}/test_anomaly_db"
)


# ==========================================================
# DATABASE SETUP
# ==========================================================

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    SessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def override_db(db_session):

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.clear()


# ==========================================================
# TESTS
# ==========================================================

@pytest.mark.asyncio
async def test_successful_hot_path_ingestion(override_db):

    payload = {
        "line_id": "Line_Test_1",
        "sensor_type": "torque",
        "value": 142.85,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:

        response = await client.post("/readings", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "success"


@pytest.mark.asyncio
async def test_pydantic_validation_gate_rejection(override_db):

    payload = {
        "line_id": "Line_Test_1",
        "sensor_type": "conveyor_speed",
        "value": "FAULT_TEXT_DUMP",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:

        response = await client.post("/readings", json=payload)

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_ingest_idempotency_deduplication(override_db):

    shared_timestamp = datetime.now(timezone.utc).isoformat()

    payload = {
        "line_id": "Line_Duplicate_Zone",
        "sensor_type": "fill_level",
        "value": 45.2,
        "timestamp": shared_timestamp,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:

        first = await client.post("/readings", json=payload)

        assert first.status_code == 200

        second = await client.post("/readings", json=payload)

        assert second.status_code == 200
        assert second.json()["status"] == "ignored"