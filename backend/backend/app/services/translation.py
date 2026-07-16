"""Doc #4 §3(c)/§4(c) / Doc #8 §4 — Translation Bridge Service.

Wires ``complete_with_fallback`` with the Translation Bridge system prompt,
Fast/Cheap tier, and ``TranslationResult`` schema.

Structural constraints (enforced by ``test_translation_imports.py``):
  - Fast/Cheap tier ONLY — never reaches the Reasoning tier.
  - Never touches the RAG/vector store.
  - ``high_stakes`` is derived deterministically per Doc #8 §4.1,
    NEVER from the model output.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.services.prompts import TRANSLATION_BRIDGE_SYSTEM_PROMPT
from backend.orchestration.completion import CompletionResult, complete_with_fallback
from backend.orchestration.interfaces import ModelRouter, TaskType
from backend.orchestration.logging_ import LogCallback
from backend.orchestration.schemas import TranslationResult

logger = logging.getLogger("crewlink.translation")


# ---------------------------------------------------------------------------
# Deterministic high_stakes derivation  (Doc #8 §4.1)
# ---------------------------------------------------------------------------

# Categories that always make translation high-stakes, even without emergency flag
HIGH_STAKES_CATEGORIES: frozenset[str] = frozenset({"medical", "accessibility"})


def _derive_high_stakes(*, emergency_flag: bool, category: str = "general") -> bool:
    """Doc #8 §4.1: high_stakes is ALWAYS computed deterministically.

    Rule: ``emergency_flag OR category in {medical, accessibility}``

    This is NEVER left to the model's judgment, matching how ``priority_score``
    and ``requires_emergency_escalation`` are deterministic elsewhere.
    """
    return emergency_flag or (category.lower() in HIGH_STAKES_CATEGORIES)


# ---------------------------------------------------------------------------
# Translation service
# ---------------------------------------------------------------------------


async def translate_message(
    *,
    original_text: str,
    source_language: str,
    target_language: str,
    model_router: ModelRouter,
    log_callback: LogCallback,
    timeout_s: float = 15.0,
) -> CompletionResult:
    """Translate *original_text* from *source_language* to *target_language*.

    Uses the Fast/Cheap tier (``TaskType.TRANSLATION``) via ``complete_with_fallback``.
    After the call, ``high_stakes`` is ALWAYS overridden with the deterministic value
    — never trusted from the model output.

    Returns:
        ``CompletionResult`` with ``data`` matching ``TranslationResult`` schema.
    """
    provider = model_router.for_task(TaskType.TRANSLATION)

    user_text = (
        f"<message>\n"
        f"  <text>{original_text}</text>\n"
        f"  <source_language>{source_language}</source_language>\n"
        f"  <target_language>{target_language}</target_language>\n"
        f"</message>"
    )

    result = await complete_with_fallback(
        provider=provider,
        task_type=TaskType.TRANSLATION,
        system_prompt=TRANSLATION_BRIDGE_SYSTEM_PROMPT,
        user_text=user_text,
        schema=TranslationResult,
        log_callback=log_callback,
        timeout_s=timeout_s,
        fallback_kwargs={"original_text": original_text},
    )

    # ── Post-call deterministic override (Doc #8 §4.1) ──────────────
    data: dict[str, Any] = result.data
    emergency_flag = bool(data.get("emergency_flag", False))
    category = str(data.get("category", "general"))

    high_stakes = _derive_high_stakes(emergency_flag=emergency_flag, category=category)
    data["high_stakes"] = high_stakes

    # ── Structured logging: WARNING for low-confidence high-stakes ──
    confidence = float(data.get("confidence", 0.0))
    if high_stakes and confidence < 0.7:
        logger.warning(
            "Low-confidence high-stakes translation — confidence=%.2f "
            "emergency_flag=%s source=%s target=%s preview=%.100s",
            confidence,
            emergency_flag,
            source_language,
            target_language,
            original_text,
        )

    return CompletionResult(
        data=data,
        fallback_used=result.fallback_used,
        fallback_name=result.fallback_name,
        latency_ms=result.latency_ms,
        error_reason=result.error_reason,
    )
