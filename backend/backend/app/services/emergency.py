"""ADDENDUM G7/G4/G3 — Emergency Broadcast Service.

Fully deterministic emergency broadcasting with structured CRITICAL logging.
No LLM calls — ever.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from backend.app.services.escalation import EscalationChannel, derive_escalation_channel
from backend.app.services.kb_lookup import is_kb_eligible
from backend.app.services.urgency import UrgencySignal, derive_urgency_signal

logger = logging.getLogger("crewlink.emergency")


@dataclass
class EmergencyBroadcastResult:
    escalation_channel: EscalationChannel
    urgency_signal: UrgencySignal
    kb_eligible: bool
    broadcasted_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def broadcast_emergency(
    *,
    incident_id: str,
    category: str,
    description: str,
    zone_id: str,
    zone_congestion: float = 0.0,
    time_in_queue_seconds: int = 0,
) -> EmergencyBroadcastResult:
    escalation_channel = derive_escalation_channel(category, description)
    urgency_signal = derive_urgency_signal("high", zone_congestion, time_in_queue_seconds, is_emergency=True)
    kb_eligible = is_kb_eligible(category)

    log_payload: dict[str, Any] = {
        "event": "emergency_broadcast",
        "incident_id": incident_id,
        "category": category,
        "zone_id": zone_id,
        "escalation_channel": escalation_channel.value,
        "urgency_signal": urgency_signal.value,
        "kb_eligible": kb_eligible,
        "description_preview": description[:200],
    }

    logger.critical(
        "EMERGENCY BROADCAST: %(event)s — channel=%(escalation_channel)s "
        "incident=%(incident_id)s zone=%(zone_id)s",
        log_payload,
    )

    return EmergencyBroadcastResult(
        escalation_channel=escalation_channel,
        urgency_signal=urgency_signal,
        kb_eligible=kb_eligible,
    )
