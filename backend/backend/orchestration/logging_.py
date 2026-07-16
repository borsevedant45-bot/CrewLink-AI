"""Doc #3 — AIInvocationLog: logging callback for every AI call and override.

Every call to the AI orchestration layer (success or fallback) produces
exactly one log row.  Manual overrides (FR-9) produce a row with
``override_type`` set to distinguish human choice from model output.

This module defines the record shape and a callback Protocol so the
persistence strategy can be injected (SQLAlchemy session, test spy, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from .interfaces import ModelTier, TaskType


@dataclass
class InvocationRecord:
    """One row for ``AIInvocationLog`` (Doc #3 entity).

    All fields match ``backend/app/models/ai_invocation_log.py``.

    ``override_type`` (G15):
      - ``None`` — AI model output (the normal case)
      - ``"HUMAN_RECLASSIFICATION"`` — supervisor/volunteer manually changed status
      - ``"HUMAN_REASSIGNMENT"`` — supervisor manually reassigned an incident
    """

    invocation_id: str = field(default_factory=lambda: str(uuid4()))
    related_entity_type: str = "NONE"
    related_entity_id: str | None = None
    tier_used: str = ""
    purpose: str = ""
    input_summary: str = ""
    output_text: str = ""
    confidence: float | None = None
    latency_ms: int = 0
    model_provider: str = "stub"
    model_name: str = "stub"
    fallback_used: bool = False
    golden_eval_expected_label: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    override_type: str | None = None

    @classmethod
    def from_call(
        cls,
        *,
        tier: ModelTier,
        task_type: TaskType,
        latency_ms: int,
        fallback_used: bool,
        confidence: float | None = None,
        input_summary: str = "",
        output_text: str = "",
        related_entity_type: str = "NONE",
        related_entity_id: str | None = None,
    ) -> InvocationRecord:
        """Build a record from the common call-site parameters."""
        return cls(
            tier_used=tier.value,
            purpose=task_type.value,
            latency_ms=latency_ms,
            fallback_used=fallback_used,
            confidence=confidence,
            input_summary=input_summary[:500],
            output_text=output_text[:2000],
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
        )

    @classmethod
    def for_manual_override(
        cls,
        *,
        override_type: str,
        related_entity_type: str,
        related_entity_id: str,
        input_summary: str,
        output_text: str,
    ) -> InvocationRecord:
        """Build a record for a human override (no AI call involved)."""
        return cls(
            tier_used="NONE",
            purpose="CLASSIFICATION" if "RECLASSIFICATION" in override_type else "DISPATCH_RECOMMENDATION",
            latency_ms=0,
            fallback_used=False,
            confidence=None,
            input_summary=input_summary[:500],
            output_text=output_text[:2000],
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            override_type=override_type,
        )


class LogCallback(Protocol):
    """Signature for the callback that persists an InvocationRecord."""

    async def __call__(self, record: InvocationRecord) -> None: ...
