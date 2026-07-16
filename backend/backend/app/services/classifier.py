"""Doc #4 §3(a)/§4 — Incident Classification Service.

Wires ``complete_with_fallback`` with the Incident Classifier system prompt,
Fast/Cheap tier, and ``IncidentClassification`` schema.
"""

from __future__ import annotations

from typing import Any

from backend.app.services.prompts import INCIDENT_CLASSIFIER_SYSTEM_PROMPT
from backend.orchestration.completion import complete_with_fallback
from backend.orchestration.interfaces import ModelRouter, TaskType
from backend.orchestration.logging_ import LogCallback
from backend.orchestration.schemas import IncidentClassification


async def classify_incident(
    *,
    description: str,
    zone_id: str,
    source: str,
    model_router: ModelRouter,
    log_callback: LogCallback,
    timeout_s: float = 15.0,
) -> Any:
    provider = model_router.for_task(TaskType.INCIDENT_CLASSIFICATION)

    user_text = (
        f"<incident_report>\n"
        f"  <description>{description}</description>\n"
        f"  <zone>{zone_id}</zone>\n"
        f"  <source>{source}</source>\n"
        f"</incident_report>"
    )

    result = await complete_with_fallback(
        provider=provider,
        task_type=TaskType.INCIDENT_CLASSIFICATION,
        system_prompt=INCIDENT_CLASSIFIER_SYSTEM_PROMPT,
        user_text=user_text,
        schema=IncidentClassification,
        log_callback=log_callback,
        timeout_s=timeout_s,
        fallback_kwargs={"description": description},
    )

    return result
