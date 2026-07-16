"""Doc #4 §4 + §5 — ``complete_with_fallback``: the central orchestration function.

Every AI call site in CrewLink flows through this function:
  1. Call ``provider.complete_structured(...)``.
  2. Validate with ``schema.model_validate(...)`` (second layer — Doc #4 §5.2).
  3. If the schema has ``volunteer_id`` or ``chunk_id`` fields, check against
     the caller-supplied *validation_context* (hallucinated-ID guard).
  4. On any failure — time-out, schema mismatch, hallucinated ID — invoke the
     deterministic fallback for that ``TaskType``.
  5. Log exactly one ``InvocationRecord`` per call, whether success or fallback.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from .fallbacks import FALLBACK_MAP
from .interfaces import TASK_TIER_MAP, LLMProvider, TaskType
from .logging_ import InvocationRecord, LogCallback

logger = logging.getLogger("crewlink.orchestration")


# ---------------------------------------------------------------------------
# Result envelope
# ---------------------------------------------------------------------------


@dataclass
class CompletionResult:
    """Wrapper returned by ``complete_with_fallback``."""

    data: dict[str, Any]
    fallback_used: bool
    fallback_name: str | None
    latency_ms: int
    error_reason: str | None = None


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_ids(
    validated: BaseModel,
    validation_context: dict[str, set[str]],
) -> None:
    """Check that ID fields only contain values from the caller's context.

    Doc #4 §5.2 bullet 2: "A volunteer_id the Dispatch Recommender returns
    is checked against the candidate list...a chunk ID...against the chunks
    that were actually retrieved."

    This recursively walks the validated model tree to find any field matching
    a key in *validation_context*, so nested IDs (e.g. ``volunteer_id`` inside
    ``DispatchCandidate`` within ``recommended_volunteers``) are caught.
    """
    for field_name, allowed_values in validation_context.items():
        _check_field(validated, field_name, allowed_values)


def _check_field(
    model: BaseModel,
    field_name: str,
    allowed: set[str],
) -> None:
    """Recursively check all values of *field_name* in *model* and children."""
    fields = type(model).model_fields
    for fname in fields:
        value = getattr(model, fname, None)
        if value is None:
            continue

        # Direct match — validate the value(s)
        if fname == field_name:
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and item not in allowed:
                        msg = f"Hallucinated {field_name}={item!r}: not in allowed set"
                        raise ValueError(msg)
            elif isinstance(value, str) and value not in allowed:
                msg = f"Hallucinated {field_name}={value!r}: not in allowed set"
                raise ValueError(msg)

        # Recurse into nested models
        if isinstance(value, BaseModel):
            _check_field(value, field_name, allowed)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, BaseModel):
                    _check_field(item, field_name, allowed)


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


async def complete_with_fallback(
    *,
    provider: LLMProvider,
    task_type: TaskType,
    system_prompt: str,
    user_text: str,
    schema: type[BaseModel],
    log_callback: LogCallback,
    timeout_s: float,
    validation_context: dict[str, set[str]] | None = None,
    fallback_kwargs: dict[str, Any] | None = None,
) -> CompletionResult:
    """Make an AI call with full enforcement pipeline and fallback.

    Args:
        provider: The ``LLMProvider`` for this task's tier.
        task_type: Which CrewLink task this is (determines tier + fallback).
        system_prompt: The system message (Doc #4 §3 prompts).
        user_text: The user message (untrusted content wrapped in tags).
        schema: The Pydantic model defining the expected output shape.
        log_callback: Async callable that persists an ``InvocationRecord``.
        timeout_s: Hard timeout for the provider call.
        validation_context: Optional ``{field_name: {allowed_value, ...}}``
            for hallucinated-ID checks (Doc #4 §5.2).
        fallback_kwargs: Extra keyword arguments for the fallback handler.

    Returns:
        ``CompletionResult`` — success or fallback, never an exception.
    """
    tier = TASK_TIER_MAP[task_type]
    start = time.monotonic()
    error_reason: str | None = None

    try:
        # Step 1: Call the provider (which does flatten_refs → tool schema
        # → forced tool_choice → extract → model_validate internally).
        raw = await provider.complete_structured(
            system=system_prompt,
            user=user_text,
            schema=schema,
            timeout_s=timeout_s,
        )

        # Step 2: Explicit second validation (Doc #4 §5.2 bullet 1).
        validated = schema.model_validate(raw if isinstance(raw, dict) else raw.model_dump())

        # Step 3: Hallucinated-ID check (Doc #4 §5.2 bullet 2).
        if validation_context:
            _validate_ids(validated, validation_context)

        data = validated.model_dump()
        confidence: float | None = float(data["confidence"]) if "confidence" in data else None
        elapsed = _elapsed_ms(start)

        await log_callback(
            InvocationRecord.from_call(
                tier=tier,
                task_type=task_type,
                latency_ms=elapsed,
                fallback_used=False,
                confidence=confidence,
                input_summary=user_text[:200],
                output_text=str(data)[:500],
            ),
        )
        return CompletionResult(
            data=data,
            fallback_used=False,
            fallback_name=None,
            latency_ms=elapsed,
        )

    except Exception as exc:
        elapsed = _elapsed_ms(start)
        error_reason = _exc_reason(exc)
        logger.warning(
            "AI fallback triggered for %s after %.0fms: %s",
            task_type.value,
            elapsed,
            error_reason,
        )

        # Route to deterministic fallback
        fallback_fn = FALLBACK_MAP.get(task_type)
        if fallback_fn is None:
            msg = f"No fallback registered for {task_type}"
            raise RuntimeError(msg) from exc

        fallback_kwargs = fallback_kwargs or {}
        fallback_result = fallback_fn(**fallback_kwargs)

        fallback_data: dict[str, Any]
        if isinstance(fallback_result, BaseModel):
            fallback_data = fallback_result.model_dump()
        else:
            fallback_data = {"text": str(fallback_result)}

        await log_callback(
            InvocationRecord.from_call(
                tier=tier,
                task_type=task_type,
                latency_ms=elapsed,
                fallback_used=True,
                confidence=fallback_data.get("confidence"),
                input_summary=user_text[:200],
                output_text=str(fallback_data)[:500],
            ),
        )
        return CompletionResult(
            data=fallback_data,
            fallback_used=True,
            fallback_name=task_type.value,
            latency_ms=elapsed,
            error_reason=error_reason,
        )


def _elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


def _exc_reason(exc: Exception) -> str:
    if isinstance(exc, TimeoutError):
        return "provider_timeout"
    if isinstance(exc, ValidationError):
        return f"schema_validation_error: {exc.errors()}"
    return f"{type(exc).__name__}: {exc}"
