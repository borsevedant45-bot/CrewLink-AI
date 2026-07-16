"""Test 3: Source non-nullable — every generated row carries source=SIMULATED.

Phase 1's DB constraint enforces source non-nullable at the schema level.
This test confirms the simulator never bypasses it.
"""

from __future__ import annotations

from mock_simulator.app.generators.crowd_density_generator import generate_density_event
from mock_simulator.app.generators.incident_generator import generate_incident_event
from mock_simulator.app.generators.position_ping_generator import generate_ping_event


class TestSourceNonNullable:
    """Every simulator-generated event carries source=SIMULATED."""

    def test_incident_event_has_simulated_source(self) -> None:
        for cat in ("medical", "lost_fan", "translation", "accessibility", "crowd_queue", "lost_item", "general"):
            event = generate_incident_event(category=cat, zone_id="zone_east_concourse", rng_seed=cat)
            assert event.source == "SIMULATED", f"{cat} incident missing SIMULATED source"

    def test_crowd_density_has_simulated_source(self) -> None:
        event = generate_density_event(
            zone_id="zone_east_concourse",
            occupancy=4000,
            capacity=8500,
            timestamp="2026-07-15T12:00:00+00:00",
        )
        assert event.source == "SIMULATED"

    def test_position_ping_has_simulated_source(self) -> None:
        event = generate_ping_event(
            volunteer_id="vol_1",
            zone_id="zone_east_concourse",
            timestamp="2026-07-15T12:00:00+00:00",
        )
        assert event.source == "SIMULATED"

    def test_source_is_never_optional(self) -> None:
        """source should not accept None — schema-level guarantee."""
        incident = generate_incident_event(category="general", zone_id="zone_test", rng_seed=0)
        assert incident.source is not None and incident.source == "SIMULATED"

        density = generate_density_event("zone_test", 100, 1000, "2026-07-15T12:00:00+00:00")
        assert density.source is not None and density.source == "SIMULATED"

        ping = generate_ping_event("vol_test", "zone_test", "2026-07-15T12:00:00+00:00")
        assert ping.source is not None and ping.source == "SIMULATED"
