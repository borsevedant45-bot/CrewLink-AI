"""Doc #3 — AIInvocationLog: one row per AI call or manual override.

FR-9 (G15): ``override_type`` distinguishes model output (NONE) from human
overrides (HUMAN_RECLASSIFICATION / HUMAN_REASSIGNMENT).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from backend.app.db.base import Base
from sqlalchemy import DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class AIInvocationLog(Base):
    __tablename__ = "ai_invocation_logs"

    invocation_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    related_entity_type: Mapped[str] = mapped_column(
        Enum(
            "INCIDENT", "CHAT_MESSAGE", "NONE",
            name="related_entity_type_enum", create_constraint=True,
        ),
        nullable=False,
    )
    related_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    tier_used: Mapped[str] = mapped_column(
        Enum(
            "fast_cheap", "reasoning", "NONE",
            name="tier_enum", create_constraint=True,
        ),
        nullable=False,
    )
    purpose: Mapped[str] = mapped_column(
        Enum(
            "incident_classification", "intent_routing", "translation",
            "dispatch_recommendation", "ask_crewlink_synthesis", "shift_summary",
            "CLASSIFICATION", "DISPATCH_RECOMMENDATION",
            name="invocation_purpose_enum", create_constraint=True,
        ),
        nullable=False,
    )
    input_summary: Mapped[str] = mapped_column(Text, nullable=False)
    output_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    model_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    golden_eval_expected_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(UTC),
    )
    override_type: Mapped[str | None] = mapped_column(
        Enum(
            "NONE", "HUMAN_RECLASSIFICATION", "HUMAN_REASSIGNMENT",
            name="override_type_enum", create_constraint=True,
        ),
        nullable=True, default="NONE",
    )

    def __repr__(self) -> str:
        return f"<AIInvocationLog {self.invocation_id} {self.purpose}>"
