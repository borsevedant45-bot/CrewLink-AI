from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class CrowdDensityReading(Base):
    __tablename__ = "crowd_density_readings"

    reading_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    zone_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("zones.zone_id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(UTC),
    )
    occupancy_estimate: Mapped[int] = mapped_column(Integer, nullable=False)
    density_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    density_level: Mapped[str] = mapped_column(
        Enum(
            "LOW", "MODERATE", "HIGH", "CRITICAL",
            name="density_level_enum", create_constraint=True,
        ),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        Enum(
            "SIMULATED", "VOLUNTEER_REPORTED", "SUPERVISOR_CREATED",
            name="reading_source_enum", create_constraint=True,
        ),
        nullable=False,
    )

    zone = relationship("Zone", back_populates="crowd_density_readings")

    def __repr__(self) -> str:
        return f"<CrowdDensityReading {self.reading_id} zone={self.zone_id}>"
