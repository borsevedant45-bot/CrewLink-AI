from datetime import datetime
from uuid import uuid4

from backend.app.db.base import Base
from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Shift(Base):
    __tablename__ = "shifts"

    shift_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    volunteer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("volunteers.volunteer_id"), nullable=False
    )
    zone_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("zones.zone_id"), nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "SCHEDULED", "ACTIVE", "COMPLETED", "NO_SHOW", "CANCELLED",
            name="shift_status_enum", create_constraint=True,
        ),
        nullable=False,
        default="SCHEDULED",
    )
    check_in_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    volunteer = relationship("Volunteer", back_populates="shifts")
    zone = relationship("Zone", back_populates="shifts")

    def __repr__(self) -> str:
        return f"<Shift {self.shift_id} volunteer={self.volunteer_id}>"
