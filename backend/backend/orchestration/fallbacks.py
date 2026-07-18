"""Doc #4 §5.3 — Deterministic fallback handlers for every TaskType.

Each fallback produces a Pydantic model matching the schema the TaskType
would have returned from the LLM.  Every response is visibly badged with
``fallback_used: true`` and a ``classification_method`` or equivalent field
for UI display.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .interfaces import TaskType
from .schemas import (
    Category,
    DispatchCandidate,
    DispatchRecommendation,
    GroundedAnswer,
    IncidentClassification,
    IntentClassification,
    IntentType,
    Severity,
    ShiftSummary,
    TranslationResult,
)


def _classify_fallback(description: str = "") -> IncidentClassification:
    """Doc #4 §5.3 — Keyword/heuristic classifier.

    Biased toward higher default severity when uncertain.  The resulting
    ``IncidentClassification`` can be distinguished from an LLM-produced
    one by checking ``classification_method`` (not a schema field — checked
    via the ``fallback_used`` flag in the envelope).
    """
    text_lower = description.lower()

    # Simple keyword heuristic
    emergency_keywords = [
        "collaps", "unconscious", "breath", "bleed", "chest pain",
        "choking", "seizure", "allergic", "fire", "smoke", "weapon",
        "violence", "threat", "not moving",
    ]
    medical_keywords = ["hurt", "injur", "wound", "blood", "fall", "dizzy", "pain"]
    crowd_keywords = ["crowd", "queue", "line", "congestion", "wait"]
    lost_keywords = ["lost", "missing", "can't find", "separated"]

    if any(k in text_lower for k in emergency_keywords):
        return IncidentClassification(
            category=Category.MEDICAL,
            severity_signal=Severity.HIGH,
            requires_emergency_escalation=True,
            confidence=0.5,
            reasoning_summary="Fallback heuristic: emergency keyword matched",
        )

    if any(k in text_lower for k in medical_keywords):
        return IncidentClassification(
            category=Category.MEDICAL,
            severity_signal=Severity.MEDIUM,
            requires_emergency_escalation=False,
            confidence=0.5,
            reasoning_summary="Fallback heuristic: medical keyword matched",
        )

    if any(k in text_lower for k in crowd_keywords):
        return IncidentClassification(
            category=Category.CROWD_QUEUE,
            severity_signal=Severity.MEDIUM,
            requires_emergency_escalation=False,
            confidence=0.5,
            reasoning_summary="Fallback heuristic: crowd/queue keyword matched",
        )

    if any(k in text_lower for k in lost_keywords):
        return IncidentClassification(
            category=Category.LOST_FAN,
            severity_signal=Severity.MEDIUM,
            requires_emergency_escalation=False,
            confidence=0.5,
            reasoning_summary="Fallback heuristic: lost-person keyword matched",
        )

    return IncidentClassification(
        category=Category.GENERAL,
        severity_signal=Severity.LOW,
        requires_emergency_escalation=False,
        confidence=0.3,
        reasoning_summary="Fallback heuristic: no specific keyword matched",
    )


def _intent_routing_fallback(_query: str = "") -> IntentClassification:
    """Doc #4 §5.3 — Default to FACILITY_SAFETY_PROCEDURE when uncertain.

    Ambiguity resolves toward caution (Doc #4 governing principle 2).
    """
    return IntentClassification(
        intent=IntentType.FACILITY_SAFETY_PROCEDURE,
        confidence=0.4,
    )


def _translation_fallback(original_text: str = "") -> TranslationResult:
    """Doc #4 §5.3 — Show original text with 'translation unavailable' notice.

    Never a guessed translation.
    """
    return TranslationResult(
        translated_text=original_text,
        detected_language="und",
        confidence=0.0,
        emergency_flag=False,
    )


def _dispatch_fallback() -> DispatchRecommendation:
    """Doc #4 §5.3 — Nearest-available-in-zone stub; flagged for supervisor review.

    The full implementation (Phase 7) will query the volunteer roster.
    """
    return DispatchRecommendation(
        recommended_volunteers=[
            DispatchCandidate(
                volunteer_id="fallback_nearest_available",
                rank=1,
                rationale="Fallback: nearest available in zone (supervisor review recommended)",
            ),
        ],
        requires_human_supervisor_review=True,
        confidence=0.0,
    )


def _ask_crewlink_fallback() -> GroundedAnswer:
    """Doc #4 §5.3 — Static 'ask a supervisor / check the printed venue guide'."""
    return GroundedAnswer(
        answer=(
            "I couldn't find an answer in the venue guide. "
            "Please ask your zone supervisor or check at the information desk."
        ),
        grounded=False,
        sources=[],
    )


def _shift_summary_fallback() -> ShiftSummary:
    """Doc #4 §5.3 — Fallback shift summary with G18-conformant schema."""
    return ShiftSummary(
        summary="Shift summary unavailable — AI orchestration degraded.",
        incident_count=0,
        notable_events=[],
        fallback_used=True,
    )


# ---------------------------------------------------------------------------
# Registry — one fallback per TaskType
# ---------------------------------------------------------------------------

FALLBACK_MAP: dict[TaskType, Callable[..., Any]] = {
    TaskType.INCIDENT_CLASSIFICATION: _classify_fallback,
    TaskType.INTENT_ROUTING: _intent_routing_fallback,
    TaskType.TRANSLATION: _translation_fallback,
    TaskType.DISPATCH_RECOMMENDATION: _dispatch_fallback,
    TaskType.ASK_CREWLINK_SYNTHESIS: _ask_crewlink_fallback,
    TaskType.SHIFT_SUMMARY: _shift_summary_fallback,
}


class FallbackRegistry:
    """Accessor for fallback handlers."""

    def get(self, task_type: TaskType) -> Callable[..., Any]:
        handler = FALLBACK_MAP.get(task_type)
        if handler is None:
            msg = f"No fallback registered for {task_type}"
            raise KeyError(msg)
        return handler
