"""Mapping between Doc #2 §5 (PascalCase) and Doc #5 wire format (snake_case).

This is an explicit enum-to-string mapping, not string-matching or heuristics.
"""

from __future__ import annotations

_INCIDENT_STATUS_MAP: dict[str, str] = {
    "Reported": "reported",
    "Triaged": "triaged",
    "Dispatched": "dispatched",
    "Acknowledged": "acknowledged",
    "InProgress": "in_progress",
    "Resolved": "resolved",
    "Escalated": "escalated",
    "Cancelled": "cancelled",
}

_INCIDENT_STATUS_REVERSE: dict[str, str] = {v: k for k, v in _INCIDENT_STATUS_MAP.items()}


def status_to_wire(pascal: str) -> str:
    """Convert Doc #2 status (PascalCase) to Doc #5 wire format (snake_case)."""
    result = _INCIDENT_STATUS_MAP.get(pascal)
    if result is None:
        raise ValueError(f"Unknown status: {pascal!r}")
    return result


def status_from_wire(snake: str) -> str:
    """Convert Doc #5 wire format (snake_case) to Doc #2 status (PascalCase)."""
    result = _INCIDENT_STATUS_REVERSE.get(snake)
    if result is None:
        raise ValueError(f"Unknown wire status: {snake!r}")
    return result
