"""Pure incident state machine — zero FastAPI/SQLAlchemy imports.

Doc #2 §5 transition table (13 normal + 1 emergency-bypass).
Terminal states: Resolved, Cancelled — fully immutable.
"""

from __future__ import annotations

from typing import Literal

IncidentStatus = Literal[
    "Reported", "Triaged", "Dispatched", "Acknowledged",
    "InProgress", "Resolved", "Escalated", "Cancelled",
]

_TERMINAL: frozenset[IncidentStatus] = frozenset({"Resolved", "Cancelled"})

_TRANSITIONS: dict[IncidentStatus, frozenset[IncidentStatus]] = {
    "Reported": frozenset({"Triaged", "Cancelled"}),
    "Triaged": frozenset({"Dispatched", "Escalated", "Cancelled"}),
    "Dispatched": frozenset({"Acknowledged", "Escalated", "Cancelled"}),
    "Acknowledged": frozenset({"InProgress", "Escalated", "Cancelled"}),
    "InProgress": frozenset({"Resolved", "Escalated", "Cancelled"}),
    "Escalated": frozenset({"Triaged", "Dispatched", "Cancelled"}),
    "Resolved": frozenset(),
    "Cancelled": frozenset(),
}


def is_terminal(status: IncidentStatus) -> bool:
    return status in _TERMINAL


def valid_transitions_from(status: IncidentStatus) -> frozenset[IncidentStatus]:
    return _TRANSITIONS.get(status, frozenset())


def apply_transition(
    from_status: IncidentStatus,
    to_status: IncidentStatus,
    *,
    emergency_bypass: bool = False,
) -> IncidentStatus:
    """Apply a state transition.

    Args:
        from_status: Current incident status.
        to_status: Desired next status.
        emergency_bypass: If True, allows Reported -> Escalated directly
                          (emergency escalation path, Doc #2 §5).

    Returns:
        The new status on success.

    Raises:
        ValueError: If the transition is not permitted by the state machine.
    """
    if from_status not in _TRANSITIONS:
        raise ValueError(f"Unknown status: {from_status}")

    if is_terminal(from_status):
        raise ValueError(
            f"Cannot transition from terminal state '{from_status}'"
        )

    if emergency_bypass and from_status == "Reported" and to_status == "Escalated":
        return to_status

    valid = _TRANSITIONS[from_status]
    if to_status not in valid:
        raise ValueError(
            f"Invalid transition: '{from_status}' -> '{to_status}'. "
            f"Valid targets from '{from_status}': {sorted(valid)}"
        )
    return to_status
