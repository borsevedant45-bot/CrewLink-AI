from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class Volunteer(Base):
    __tablename__ = "volunteers"

    volunteer_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("VOLUNTEER", "SUPERVISOR", name="volunteer_role_enum", create_constraint=True),
        nullable=False,
    )
    primary_language: Mapped[str] = mapped_column(String(50), nullable=False)
    secondary_languages: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    assigned_zone_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("zones.zone_id"), nullable=False
    )
    skills_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(
        Enum(
            "OFF_SHIFT", "AVAILABLE", "BUSY", "ON_BREAK",
            name="volunteer_status_enum", create_constraint=True,
        ),
        nullable=False,
        default="OFF_SHIFT",
    )
    auth_subject_id: Mapped[str] = mapped_column(String(200), nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(50), nullable=True)

    shifts = relationship("Shift", back_populates="volunteer")
    reported_incidents = relationship(
        "Incident", back_populates="reporter", foreign_keys="Incident.reported_by_volunteer_id"
    )
    assigned_incidents = relationship(
        "Incident", back_populates="assignee", foreign_keys="Incident.assigned_volunteer_id"
    )
    chat_sessions = relationship("ChatSession", back_populates="volunteer")
    position_pings = relationship("VolunteerPositionPing", back_populates="volunteer")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<Volunteer {self.volunteer_id} {self.display_name}>"
