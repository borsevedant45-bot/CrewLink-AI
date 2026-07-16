"""ADDENDUM G4 — urgency_signal derivation.

Convert the classifier severity_signal + external factors
(congestion, time_in_queue) into a deterministic urgency_signal.
"""

import enum


class UrgencySignal(enum.StrEnum):
    low = 'low'
    medium = 'medium'
    high = 'high'
    critical = 'critical'


def derive_urgency_signal(
    severity_signal: str,
    zone_congestion: float = 0.0,
    time_in_queue_seconds: int = 0,
    is_emergency: bool = False,
) -> UrgencySignal:
    """Derive urgency_signal from severity + context (ADDENDUM G4).

    ``critical`` is returned when an emergency escalation is active AND
    severity is ``high`` — representing the life-threatening threshold
    that triggers the deterministic broadcast path.
    """
    severity = severity_signal.strip().lower()
    if severity == 'high':
        if is_emergency:
            return UrgencySignal.critical
        return UrgencySignal.high
    if severity == 'medium':
        if zone_congestion >= 0.8:
            return UrgencySignal.high
        if time_in_queue_seconds > 600:
            return UrgencySignal.high
        return UrgencySignal.medium
    if severity == 'low':
        if zone_congestion >= 0.8:
            return UrgencySignal.medium
        return UrgencySignal.low
    return UrgencySignal.low
