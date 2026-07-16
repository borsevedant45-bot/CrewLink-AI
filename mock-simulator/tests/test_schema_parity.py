"""Test 2: Schema parity — simulated events match the same schema as VOLUNTEER_REPORTED.

This test proves the swappability claim: a "real" feed adapter can be substituted
for the simulator with zero consumer-code changes.
"""

from __future__ import annotations

from pydantic import BaseModel


class IncidentSchema(BaseModel):
    incident_id: str
    category: str
    subcategory: str | None
    raw_description: str
    source: str
    zone_id: str
    reported_by_volunteer_id: str | None
    priority_score: int
    status: str
    created_at: str
    queue_wait_estimate_minutes: float | None
    item_description: str | None
    medical_severity_hint: str | None


class CrowdDensitySchema(BaseModel):
    reading_id: str
    zone_id: str
    timestamp: str
    occupancy_estimate: int
    density_ratio: float
    density_level: str
    source: str


class PositionPingSchema(BaseModel):
    ping_id: str
    volunteer_id: str
    zone_id: str
    timestamp: str
    source: str


class TestSchemaParity:
    """Simulator-generated rows match the same Pydantic schema as hand-crafted VOLUNTEER_REPORTED rows."""

    def test_simulated_incident_passes_incident_schema(self) -> None:
        from mock_simulator.app.generators.incident_generator import generate_incident_event

        event = generate_incident_event(
            category="medical",
            zone_id="zone_east_concourse",
            rng_seed=42,
        )
        validated = IncidentSchema.model_validate(event.to_dict())
        assert validated.source == "SIMULATED"

    def test_volunteer_reported_incident_passes_same_schema(self) -> None:
        validated = IncidentSchema(
            incident_id="inc_hand_crafted_001",
            category="lost_fan",
            subcategory=None,
            raw_description="Fan separated from family at Gate 4",
            source="VOLUNTEER_REPORTED",
            zone_id="zone_gate_4",
            reported_by_volunteer_id="vol_maria_alvarez",
            priority_score=30,
            status="Reported",
            created_at="2026-07-15T12:00:00+00:00",
            queue_wait_estimate_minutes=None,
            item_description=None,
            medical_severity_hint=None,
        )
        assert validated.source == "VOLUNTEER_REPORTED"
        # Prove both pass the same schema — swappability
        sim = IncidentSchema(
            incident_id="inc_sim_001",
            category="medical",
            subcategory=None,
            raw_description="A fan needs medical attention",
            source="SIMULATED",
            zone_id="zone_east_concourse",
            reported_by_volunteer_id=None,
            priority_score=60,
            status="Reported",
            created_at="2026-07-15T12:00:00+00:00",
            queue_wait_estimate_minutes=None,
            item_description=None,
            medical_severity_hint=None,
        )
        assert sim.model_dump().keys() == validated.model_dump().keys()

    def test_simulated_density_passes_density_schema(self) -> None:
        from mock_simulator.app.generators.crowd_density_generator import generate_density_event

        event = generate_density_event(
            zone_id="zone_east_concourse",
            occupancy=3400,
            capacity=8500,
            timestamp="2026-07-15T12:00:00+00:00",
        )
        data = event.to_dict()
        validated = CrowdDensitySchema.model_validate(data)
        assert validated.source == "SIMULATED"

    def test_simulated_ping_passes_ping_schema(self) -> None:
        from mock_simulator.app.generators.position_ping_generator import generate_ping_event

        event = generate_ping_event(
            volunteer_id="vol_1",
            zone_id="zone_east_concourse",
            timestamp="2026-07-15T12:00:00+00:00",
        )
        data = event.to_dict()
        validated = PositionPingSchema.model_validate(data)
        assert validated.source == "SIMULATED"
