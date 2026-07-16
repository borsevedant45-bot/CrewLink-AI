"""Doc #4 §3(b) — Dispatch Recommender Service.

Wires ``complete_with_fallback`` with the Dispatch Recommender system prompt,
Reasoning tier, and ``DispatchRecommendation`` schema.

CRITICAL: If ``requires_emergency_escalation`` is true, this service
NEVER calls the provider — it goes directly to the emergency fallback path.
This is the provable emergency bypass (Doc #4 §3(b) / ADDENDUM G4).
"""

from __future__ import annotations

from typing import Any

from backend.app.services.prompts import DISPATCH_RECOMMENDER_SYSTEM_PROMPT
from backend.orchestration.completion import CompletionResult, complete_with_fallback
from backend.orchestration.interfaces import ModelRouter, TaskType
from backend.orchestration.logging_ import LogCallback
from backend.orchestration.schemas import DispatchRecommendation


async def recommend_dispatch(
    *,
    incident_data: dict[str, Any],
    candidates: list[dict[str, Any]],
    model_router: ModelRouter,
    log_callback: LogCallback,
    timeout_s: float = 30.0,
) -> CompletionResult:
    requires_emergency = incident_data.get("requires_emergency_escalation", False)

    if requires_emergency:
        from backend.orchestration.fallbacks import _dispatch_fallback
        fallback_result = _dispatch_fallback()
        return CompletionResult(
            data=fallback_result.model_dump(),
            fallback_used=True,
            fallback_name="dispatch_recommendation",
            latency_ms=0,
            error_reason="emergency_bypass",
        )

    provider = model_router.for_task(TaskType.DISPATCH_RECOMMENDATION)

    candidate_ids = {c["volunteer_id"] for c in candidates}
    candidates_text = "\n".join(
        f"- {c['volunteer_id']} (zone={c.get('zone_id', '?')}, "
        f"role={c.get('role', '?')}, certs={c.get('certifications', [])})"
        for c in candidates
    )

    user_text = (
        f"<incident>\n"
        f"  id: {incident_data.get('incident_id', '?')}\n"
        f"  category: {incident_data.get('category', '?')}\n"
        f"  severity: {incident_data.get('severity_signal', '?')}\n"
        f"  zone: {incident_data.get('zone_id', '?')}\n"
        f"  summary: {incident_data.get('description', '?')}\n"
        f"</incident>\n\n"
        f"<candidates>\n{candidates_text}\n</candidates>"
    )

    result = await complete_with_fallback(
        provider=provider,
        task_type=TaskType.DISPATCH_RECOMMENDATION,
        system_prompt=DISPATCH_RECOMMENDER_SYSTEM_PROMPT,
        user_text=user_text,
        schema=DispatchRecommendation,
        log_callback=log_callback,
        timeout_s=timeout_s,
        validation_context={"volunteer_id": candidate_ids},
    )

    return result
