from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class VolunteerPositionPing(Base):
    __tablename__ = "volunteer_position_pings"

    ping_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    volunteer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("volunteers.volunteer_id"), nullable=False
    )
    zone_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("zones.zone_id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(UTC),
    )
    source: Mapped[str] = mapped_column(
        Enum(
            "SIMULATED", "VOLUNTEER_REPORTED", "SUPERVISOR_CREATED",
            name="position_source_enum", create_constraint=True,
        ),
        nullable=False,
    )

    volunteer = relationship("Volunteer", back_populates="position_pings")
    zone = relationship("Zone", back_populates="volunteer_position_pings")

    def __repr__(self) -> str:
        return f"<VolunteerPositionPing {self.ping_id} volunteer={self.volunteer_id}>"
