# src/models.py

from sqlalchemy import BigInteger, String, DateTime, UniqueConstraint, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base
from datetime import datetime, timezone
from typing import List, Optional


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    line_id: Mapped[str] = mapped_column(String(50))
    sensor_type: Mapped[str] = mapped_column(String(50))
    value: Mapped[float] = mapped_column()
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint(
            "line_id", "sensor_type", "timestamp", name="uq_line_sensor_timestamp"
        ),
    )


class AnomalyCase(Base):
    __tablename__ = "anomaly_cases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    
    # Option A: Machine-state coordinates replacing point reading IDs
    line_id: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    status: Mapped[str] = mapped_column(String(30), default="FLAGGED")
    score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # FIX: Corrected typo from delete-orphan to delete_orphan
    evidence_logs: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="case", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "line_id", "timestamp", name="uq_line_timestamp_case"
        ),
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    case_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("anomaly_cases.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    case: Mapped["AnomalyCase"] = relationship("AnomalyCase", back_populates="evidence_logs")