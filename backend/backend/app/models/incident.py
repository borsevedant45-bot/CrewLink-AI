from datetime import UTC, datetime
from uuid import uuid4

from backend.app.db.base import Base
from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

INCIDENT_CATEGORIES = (
    "medical", "lost_fan", "translation", "accessibility",
    "crowd_queue", "lost_item", "general",
)
INCIDENT_SOURCES = ("SIMULATED", "VOLUNTEER_REPORTED", "SUPERVISOR_CREATED")
INCIDENT_STATUSES = (
    "Reported", "Triaged", "Dispatched", "Acknowledged",
    "InProgress", "Resolved", "Escalated", "Cancelled",
)


class Incident(Base):
    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    category: Mapped[str] = mapped_column(
        Enum(*INCIDENT_CATEGORIES, name="incident_category_enum", create_constraint=True),
        nullable=False,
    )
    subcategory: Mapped[str | None] = mapped_column(String(200), nullable=True)
    raw_description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(
        Enum(*INCIDENT_SOURCES, name="incident_source_enum", create_constraint=True),
        nullable=False,
    )
    zone_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("zones.zone_id"), nullable=False
    )
    reported_by_volunteer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("volunteers.volunteer_id"), nullable=True
    )
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority_score: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(*INCIDENT_STATUSES, name="incident_status_enum", create_constraint=True),
        nullable=False,
        default="Reported",
    )
    assigned_volunteer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("volunteers.volunteer_id"), nullable=True
    )
    dispatch_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    dispatch_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    kb_lookup_performed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    kb_reference_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    detected_language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language_context: Mapped[str | None] = mapped_column(String(50), nullable=True)
    accessibility_flags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    queue_wait_estimate_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    item_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    medical_severity_hint: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(UTC),
    )
    triaged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    zone = relationship("Zone", back_populates="incidents", foreign_keys=[zone_id])
    reporter = relationship(
        "Volunteer", back_populates="reported_incidents", foreign_keys=[reported_by_volunteer_id]
    )
    assignee = relationship(
        "Volunteer", back_populates="assigned_incidents", foreign_keys=[assigned_volunteer_id]
    )
    linked_chat_session = relationship("ChatSession", back_populates="linked_incident", uselist=False)

    def __repr__(self) -> str:
        return f"<Incident {self.incident_id} {self.category}/{self.status}>"
