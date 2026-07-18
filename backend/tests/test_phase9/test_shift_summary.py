"""Doc #7 §3.4 — Shift-summary golden-set test.

Tests:
- Schema conformance (hard 100% gate): the returned ShiftSummary must
  match the Pydantic schema exactly.
- Content-sanity threshold: summary must be non-empty, incident_count
  should be plausible, fallback_used must be boolean.

Per G18: fallback returns schema-conformant ShiftSummary with
``fallback_used=True``.
"""

from __future__ import annotations

from backend.orchestration.fallbacks import _shift_summary_fallback
from backend.orchestration.schemas import ShiftSummary


class TestShiftSummaryGoldenSet:
    """Shift-summary golden-set: schema conformance + content sanity."""

    def test_schema_conformance(self) -> None:
        """ShiftSummary must validate through Pydantic without error."""
        payload = ShiftSummary(
            summary="Quiet shift. 3 minor incidents handled, peak crowd density moderate.",
            incident_count=3,
            notable_events=["Lost child reunited with parents", "Queue management at Gate 6"],
            crowd_density_peak="moderate",
            fallback_used=False,
        )
        dumped = payload.model_dump()
        validated = ShiftSummary.model_validate(dumped)
        assert validated.summary == payload.summary
        assert validated.incident_count == 3
        assert len(validated.notable_events) == 2
        assert validated.crowd_density_peak == "moderate"
        assert validated.fallback_used is False

    def test_fallback_schema_conformant(self) -> None:
        """G18: fallback must produce schema-conformant ShiftSummary."""
        fallback = _shift_summary_fallback()
        dumped = fallback.model_dump()
        validated = ShiftSummary.model_validate(dumped)
        assert validated.fallback_used is True
        assert validated.summary == "Shift summary unavailable — AI orchestration degraded."
        assert validated.incident_count == 0

    def test_content_sanity_threshold(self) -> None:
        """Content-sanity: summary non-empty, incident_count non-negative."""
        payload = ShiftSummary(
            summary="Test shift with several incidents.",
            incident_count=5,
            notable_events=["Event A", "Event B"],
            crowd_density_peak="low",
            fallback_used=False,
        )
        assert len(payload.summary) > 0, "Summary must not be empty"
        assert payload.incident_count >= 0, "incident_count must be non-negative"
        assert isinstance(payload.fallback_used, bool), "fallback_used must be boolean"

    def test_empty_notable_events_default(self) -> None:
        """ShiftSummary with no notable events should default to empty list."""
        payload = ShiftSummary(
            summary="Short shift.",
            incident_count=0,
            fallback_used=False,
        )
        assert payload.notable_events == [], "Should default to empty list"
        assert payload.crowd_density_peak is None, "Should default to None"
