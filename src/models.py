# src/models.py

from sqlalchemy import BigInteger, String, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base
from datetime import datetime


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    # SQLAlchemy automatically infers auto-increment behavior here
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)

    line_id: Mapped[str] = mapped_column(String(50))
    sensor_type: Mapped[str] = mapped_column(String(50))
    value: Mapped[float] = mapped_column()
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "line_id", "sensor_type", "timestamp", name="uq_line_sensor_timestamp"
        ),
    )
