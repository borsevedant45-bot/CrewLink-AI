"""Test 1: Determinism — fixed seed produces identical event sequence.

Doc #7 §2: "Mock-generator determinism" bullet.
"""

from __future__ import annotations

import pickle
import random
from typing import Any

from mock_simulator.app.config import SimulatorConfig, make_default_config
from mock_simulator.app.generators.crowd_density_generator import CrowdDensityState, tick_crowd_density
from mock_simulator.app.generators.incident_generator import IncidentState, tick_incidents
from mock_simulator.app.generators.position_ping_generator import PositionPingState, tick_position_pings


def _run_simulation(
    seed: int,
    ticks: int,
    dt: float,
    config: SimulatorConfig,
    zones: list[dict[str, Any]],
    volunteers: list[dict[str, Any]],
) -> list[bytes]:
    rng = random.Random(seed)
    config._zones_cache = zones  # type: ignore[attr-defined]
    # Use a copy of config with the given seed for initial states
    seed_config = make_default_config()
    seed_config.random_seed = seed
    inc_state = IncidentState.initial(zones, seed_config)
    den_state = CrowdDensityState.initial(zones, seed_config)
    ping_state = PositionPingState.initial(volunteers, seed_config)
    events: list[bytes] = []

    for tick in range(ticks):
        now = tick * dt
        inc_state, inc_event = tick_incidents(inc_state, rng, config, now)
        den_state, den_event = tick_crowd_density(den_state, rng, config, now)
        ping_state, ping_event = tick_position_pings(ping_state, rng, config, now)
        for ev in (inc_event, den_event, ping_event):
            if ev is not None:
                events.append(pickle.dumps(ev, protocol=pickle.HIGHEST_PROTOCOL))

    return events


class TestDeterminism:
    """Fixed random seed → byte-for-byte identical event sequence across two runs."""

    def test_identical_across_two_runs(self) -> None:
        config = make_default_config()
        zones = [
            {"zone_id": "zone_east_concourse", "capacity_estimate": 8500},
            {"zone_id": "zone_west_concourse", "capacity_estimate": 8500},
            {"zone_id": "zone_north_concourse", "capacity_estimate": 6000},
            {"zone_id": "zone_south_concourse", "capacity_estimate": 6000},
        ]
        volunteers = [
            {"volunteer_id": "vol_1", "assigned_zone_id": "zone_east_concourse"},
            {"volunteer_id": "vol_2", "assigned_zone_id": "zone_west_concourse"},
        ]

        run1 = _run_simulation(seed=42, ticks=100, dt=1.0, config=config, zones=zones, volunteers=volunteers)
        run2 = _run_simulation(seed=42, ticks=100, dt=1.0, config=config, zones=zones, volunteers=volunteers)

        assert len(run1) == len(run2), f"Event count differs: {len(run1)} vs {len(run2)}"
        for i, (a, b) in enumerate(zip(run1, run2, strict=True)):
            assert a == b, f"Event {i} differs between runs"

    def test_different_seed_produces_different_sequence(self) -> None:
        config = make_default_config()
        zones = [{"zone_id": "zone_test", "capacity_estimate": 1000}]
        volunteers = [{"volunteer_id": "vol_test", "assigned_zone_id": "zone_test"}]

        run1 = _run_simulation(seed=1, ticks=50, dt=1.0, config=config, zones=zones, volunteers=volunteers)
        run2 = _run_simulation(seed=2, ticks=50, dt=1.0, config=config, zones=zones, volunteers=volunteers)

        if len(run1) > 0 and len(run2) > 0:
            assert run1 != run2, "Different seeds should produce different event sequences"
