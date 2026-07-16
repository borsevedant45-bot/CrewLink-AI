from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class ChatMessage(Base):
    """Doc #5 §2.7 — ChatMessage entity, extended with Doc #8 §4 fields."""

    __tablename__ = "chat_messages"

    message_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_sessions.session_id"), nullable=False
    )
    sender: Mapped[str] = mapped_column(
        Enum("VOLUNTEER", "FAN", name="chat_sender_enum", create_constraint=True),
        nullable=False,
    )
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    original_language: Mapped[str] = mapped_column(String(50), nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_language: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    emergency_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    back_translation: Mapped[str | None] = mapped_column(Text, nullable=True)
    high_stakes: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(UTC),
    )
    model_tier_used: Mapped[str] = mapped_column(String(20), nullable=False)

    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<ChatMessage {self.message_id} session={self.session_id}>"
