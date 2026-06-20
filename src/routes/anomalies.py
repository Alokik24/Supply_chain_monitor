# src/routes/anomalies.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from src.database import get_db
from src.models import AnomalyCase
from src.schema.anomaly import (
    AnomalyResponse,
    AnomalyStatusUpdate,
)
from src.workers.scoring_worker import (
    redis_client,
    WATERMARK_KEY,
)


VALID_STATUSES = {
    "FLAGGED",
    "INVESTIGATING",
    "RESOLVED",
    "FALSE_POSITIVE"
}

router = APIRouter(
    prefix="/anomalies",
    tags=["Anomalies"]
)

@router.get(
    "",
    response_model=list[AnomalyResponse]
)
async def get_anomalies(
    line_id: str | None = None,
    status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = Query(
        default=50,
        ge=1,
        le=100
    ),
    cursor: int | None = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AnomalyCase)
    if line_id:
        stmt = stmt.where(
            AnomalyCase.line_id == line_id
        )
    if status:

        if status not in VALID_STATUSES:
            raise HTTPException(
                status_code=400,
                detail="Invalid status filter"
            )

        stmt = stmt.where(
            AnomalyCase.status == status
        )
    if start_date:
        stmt = stmt.where(
            AnomalyCase.timestamp >= start_date
        )

    if end_date:
        stmt = stmt.where(
            AnomalyCase.timestamp <= end_date
        )
    stmt = stmt.order_by(
        AnomalyCase.score.desc(),
        AnomalyCase.id.desc()
    )
    if cursor:
        stmt = stmt.where(
            AnomalyCase.id < cursor
        )
    stmt = stmt.limit(limit)

    result = await db.execute(stmt)

    return result.scalars().all()

@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db)
):
    total_cases = await db.scalar(
        select(func.count()).select_from(AnomalyCase)
    )

    flagged = await db.scalar(
        select(func.count())
        .select_from(AnomalyCase)
        .where(AnomalyCase.status == "FLAGGED")
    )

    investigating = await db.scalar(
        select(func.count())
        .select_from(AnomalyCase)
        .where(AnomalyCase.status == "INVESTIGATING")
    )

    resolved = await db.scalar(
        select(func.count())
        .select_from(AnomalyCase)
        .where(AnomalyCase.status == "RESOLVED")
    )

    avg_score = await db.scalar(
        select(func.avg(AnomalyCase.score))
    )

    return {
        "total_cases": total_cases or 0,
        "flagged": flagged or 0,
        "investigating": investigating or 0,
        "resolved": resolved or 0,
        "average_score": round(float(avg_score or 0), 3)
    }


@router.get("/worker-status")
async def get_worker_status():

    watermark = redis_client.get(WATERMARK_KEY)

    return {
        "worker_running": True,
        "watermark": int(watermark or 0)
    }



@router.get(
    "/{case_id}",
    response_model=AnomalyResponse
)
async def get_anomaly(
    case_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AnomalyCase)
        .where(AnomalyCase.id == case_id)
    )

    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=404,
            detail="Anomaly not found"
        )

    return case

@router.patch(
    "/{case_id}",
    response_model=AnomalyResponse
)
async def update_status(
    case_id: int,
    payload: AnomalyStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Invalid status"
        )

    result = await db.execute(
        select(AnomalyCase)
        .where(AnomalyCase.id == case_id)
    )

    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=404,
            detail="Anomaly not found"
        )

    case.status = payload.status

    await db.commit()
    await db.refresh(case)

    return case