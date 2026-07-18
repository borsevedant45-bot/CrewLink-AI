"""Test 1: Incident state machine — every valid transition + every plausible illegal transition.

Doc #2 §5's "Valid transitions" table as parametrized cases.
Terminal-state immutability: Resolved/Cancelled reject any further transition.
"""

from __future__ import annotations

import pytest

from backend.app.core.state_machine import (
    IncidentStatus,
    apply_transition,
    is_terminal,
    valid_transitions_from,
)

# Every valid transition from Doc #2 §5's table
VALID_TRANSITIONS: list[tuple[IncidentStatus, IncidentStatus]] = [
    ("Reported", "Triaged"),
    ("Reported", "Cancelled"),
    ("Triaged", "Dispatched"),
    ("Triaged", "Escalated"),
    ("Triaged", "Cancelled"),
    ("Dispatched", "Acknowledged"),
    ("Dispatched", "Escalated"),
    ("Dispatched", "Cancelled"),
    ("Acknowledged", "InProgress"),
    ("Acknowledged", "Escalated"),
    ("Acknowledged", "Cancelled"),
    ("InProgress", "Resolved"),
    ("InProgress", "Escalated"),
    ("InProgress", "Cancelled"),
    ("Escalated", "Triaged"),
    ("Escalated", "Dispatched"),
    ("Escalated", "Cancelled"),
]


# Plausible but illegal transitions from every state
ILLEGAL_TRANSITIONS: list[tuple[IncidentStatus, IncidentStatus]] = [
    # Terminal states — fully immutable
    ("Resolved", "Reported"),
    ("Resolved", "Triaged"),
    ("Resolved", "Dispatched"),
    ("Resolved", "Acknowledged"),
    ("Resolved", "InProgress"),
    ("Resolved", "Escalated"),
    ("Resolved", "Cancelled"),
    ("Cancelled", "Reported"),
    ("Cancelled", "Triaged"),
    ("Cancelled", "Dispatched"),
    ("Cancelled", "Acknowledged"),
    ("Cancelled", "InProgress"),
    ("Cancelled", "Resolved"),
    ("Cancelled", "Escalated"),
    # Non-terminal states, illegal moves
    ("Reported", "Dispatched"),  # skip triage
    ("Reported", "InProgress"),  # skip dispatch
    ("Reported", "Resolved"),  # skip everything
    ("Triaged", "Acknowledged"),  # skip dispatch
    ("Triaged", "InProgress"),  # skip dispatch
    ("Triaged", "Resolved"),  # skip dispatch + work
    ("Dispatched", "Triaged"),  # cannot go back
    ("Dispatched", "InProgress"),  # skip acknowledge
    ("Dispatched", "Resolved"),  # skip acknowledge + work
    ("Acknowledged", "Triaged"),  # cannot go back
    ("Acknowledged", "Reported"),  # cannot go back
    ("Acknowledged", "Dispatched"),  # already past
    ("Acknowledged", "Resolved"),  # skip work
    ("InProgress", "Triaged"),  # cannot go back
    ("InProgress", "Dispatched"),  # cannot go back
    ("InProgress", "Acknowledged"),  # cannot go back
    ("InProgress", "Reported"),  # cannot go back
    ("Escalated", "Reported"),
    ("Escalated", "Acknowledged"),
    ("Escalated", "InProgress"),
    ("Escalated", "Resolved"),
]


class TestStateMachineTransitions:
    """Every row of Doc #2 §5's transition table, plus rejection cases."""

    @pytest.mark.parametrize("from_status,to_status", VALID_TRANSITIONS)
    def test_valid_transition(self, from_status: IncidentStatus, to_status: IncidentStatus) -> None:
        result = apply_transition(from_status, to_status)
        assert result == to_status, (
            f"Expected {from_status} -> {to_status} to succeed, got {result}"
        )

    @pytest.mark.parametrize("from_status,to_status", ILLEGAL_TRANSITIONS)
    def test_illegal_transition_raises(self, from_status: IncidentStatus, to_status: IncidentStatus) -> None:
        with pytest.raises(ValueError):
            apply_transition(from_status, to_status)

    def test_terminal_states_are_terminal(self) -> None:
        for status in ("Resolved", "Cancelled"):
            assert is_terminal(status), f"{status} should be terminal"

    def test_non_terminal_states_are_not_terminal(self) -> None:
        for status in ("Reported", "Triaged", "Dispatched", "Acknowledged", "InProgress", "Escalated"):
            assert not is_terminal(status), f"{status} should not be terminal"

    def test_valid_transitions_from_each_state(self) -> None:
        for from_status, to_status in VALID_TRANSITIONS:
            valid = valid_transitions_from(from_status)
            assert to_status in valid, (
                f"{to_status} should be a valid transition from {from_status}"
            )

    def test_cancelled_is_valid_from_any_non_terminal(self) -> None:
        for status in ("Reported", "Triaged", "Dispatched", "Acknowledged", "InProgress", "Escalated"):
            valid = valid_transitions_from(status)
            assert "Cancelled" in valid, (
                f"Cancelled should be reachable from {status} (§5: 'any non-terminal state')"
            )

    def test_emergency_bypass_skips_triage_and_dispatch(self) -> None:
        """Emergency escalation bypass goes directly to Escalated from Reported."""
        result = apply_transition("Reported", "Escalated", emergency_bypass=True)
        assert result == "Escalated"
