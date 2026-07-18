"""Doc #4 §1 — Model tiering, task types, provider protocol, and router.

This file is the single source of truth for the tier-to-task mapping.
Nothing else in the codebase names a tier or a model.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------


class ModelTier(StrEnum):
    """Doc #4 §1 — Exactly two tiers for the entire system."""

    FAST_CHEAP = "fast_cheap"
    REASONING = "reasoning"


# ---------------------------------------------------------------------------
# Task types  (Doc #4 §1 table)
# ---------------------------------------------------------------------------


class TaskType(StrEnum):
    """Every AI task in the system.

    Each maps to exactly one ModelTier via TASK_TIER_MAP below.
    """

    INCIDENT_CLASSIFICATION = "incident_classification"
    INTENT_ROUTING = "intent_routing"
    TRANSLATION = "translation"
    DISPATCH_RECOMMENDATION = "dispatch_recommendation"
    ASK_CREWLINK_SYNTHESIS = "ask_crewlink_synthesis"
    SHIFT_SUMMARY = "shift_summary"


# ---------------------------------------------------------------------------
# Task → tier mapping  (single source of truth — Doc #4 §1 table)
# ---------------------------------------------------------------------------

TASK_TIER_MAP: dict[TaskType, ModelTier] = {
    TaskType.INCIDENT_CLASSIFICATION: ModelTier.FAST_CHEAP,
    TaskType.INTENT_ROUTING: ModelTier.FAST_CHEAP,
    TaskType.TRANSLATION: ModelTier.FAST_CHEAP,
    TaskType.DISPATCH_RECOMMENDATION: ModelTier.REASONING,
    TaskType.ASK_CREWLINK_SYNTHESIS: ModelTier.REASONING,
    TaskType.SHIFT_SUMMARY: ModelTier.REASONING,
}

# ---------------------------------------------------------------------------
# Provider protocol  (Doc #4 §1)
# ---------------------------------------------------------------------------


@runtime_checkable
class LLMProvider(Protocol):
    """Every vendor adapter implements this and nothing but this.

    Business logic only ever talks to this Protocol — no vendor SDK import,
    no model name string literal outside this package.
    """

    async def complete_structured(
        self,
        *,
        system: str,
        user: str,
        schema: type[BaseModel],
        timeout_s: float,
    ) -> BaseModel:
        """Call the model with a forced tool-constrained output.

        Steps (Doc #4 §4 enforcement mechanism):
          1. Build tool definition from ``schema.model_json_schema()``
             with ``flatten_refs()`` to resolve ``$ref`` / ``$defs``.
          2. Send with ``tool_choice`` forced to that one tool (never "auto").
          3. Extract tool-call arguments from the response.
          4. Validate with ``schema.model_validate(...)``.
          5. Raise on any failure — the caller's fallback layer handles it.
        """

    async def complete_text(
        self,
        *,
        system: str,
        user: str,
        timeout_s: float,
    ) -> str:
        """Call the model for free-text output (no tool constraint).

        Used only for TaskTypes whose output is not a structured schema
        (e.g. certain translation or summary variants).
        """


# ---------------------------------------------------------------------------
# Sentinel: returned when no real provider is registered so the caller's
# fallback layer (complete_with_fallback §5) can handle the failure.
# ---------------------------------------------------------------------------


class _MissingProvider:
    """Duck-typed LLMProvider that raises on any call.

    ``complete_with_fallback`` wraps its provider call in ``try/except`` and
    routes to deterministic fallbacks (Doc #4 §5).  Raising here instead of in
    ``ModelRouter.for_task`` ensures the fallback chain is reached.
    """

    async def complete_structured(
        self,
        *,
        system: str,
        user: str,
        schema: type[BaseModel],
        timeout_s: float,
    ) -> BaseModel:
        msg = "No provider registered for this tier — check ModelRouter init"
        raise RuntimeError(msg)

    async def complete_text(
        self,
        *,
        system: str,
        user: str,
        timeout_s: float,
    ) -> str:
        msg = "No provider registered for this tier — check ModelRouter init"
        raise RuntimeError(msg)


# ---------------------------------------------------------------------------
# Router  (Doc #4 §1)
# ---------------------------------------------------------------------------


class ModelRouter:
    """Holds one provider per tier and routes callers by TaskType.

    Usage::

        provider = model_router.for_task(TaskType.INCIDENT_CLASSIFICATION)
        result = await provider.complete_structured(...)
    """

    def __init__(self, providers: dict[ModelTier, LLMProvider]) -> None:
        self._providers = providers

    def for_task(self, task: TaskType) -> LLMProvider:
        """Return the provider configured for *task*'s tier.

        Returns ``_MissingProvider`` instead of raising when no real provider
        is registered, so the caller's ``try/except`` (e.g. in
        ``complete_with_fallback``) can catch the failure and route to the
        deterministic fallback per Doc #4 §5.
        """
        tier = TASK_TIER_MAP[task]
        provider = self._providers.get(tier)
        if provider is None:
            return _MissingProvider()
        return provider
