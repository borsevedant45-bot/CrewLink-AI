from datetime import UTC, datetime
from uuid import uuid4

from backend.app.db.base import Base
from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    volunteer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("volunteers.volunteer_id"), nullable=False
    )
    fan_display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    volunteer_language: Mapped[str] = mapped_column(String(50), nullable=False)
    fan_detected_language: Mapped[str] = mapped_column(String(50), nullable=False)
    zone_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("zones.zone_id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum("ACTIVE", "ENDED", name="chat_session_status_enum", create_constraint=True),
        nullable=False,
        default="ACTIVE",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(UTC),
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    linked_incident_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("incidents.incident_id"), nullable=True, unique=True
    )

    volunteer = relationship("Volunteer", back_populates="chat_sessions")
    zone = relationship("Zone", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    linked_incident = relationship("Incident", back_populates="linked_chat_session", uselist=False)

    __table_args__ = (
        UniqueConstraint("linked_incident_id", name="uq_chat_session_linked_incident"),
    )

    def __repr__(self) -> str:
        return f"<ChatSession {self.session_id} volunteer={self.volunteer_id}>"
