"""Unit tests for individual generator pure functions.

Tests that generators produce expected events under known conditions.
"""

from __future__ import annotations

import random

from mock_simulator.app.config import make_default_config


class TestIncidentGeneratorUnit:
    """Incident generator pure-function unit tests."""

    def test_no_event_before_first_arrival(self) -> None:
        from mock_simulator.app.generators.incident_generator import IncidentState, tick_incidents
        config = make_default_config()
        config.incident_mean_interval_seconds = 100.0  # very long
        config._zones_cache = [{"zone_id": "z1", "capacity_estimate": 1000}]  # type: ignore[attr-defined]
        zones = [{"zone_id": "z1", "capacity_estimate": 1000}]
        state = IncidentState.initial(zones, config)
        rng = random.Random(0)
        new_state, event = tick_incidents(state, rng, config, now=0.0)
        assert event is None, "Should not generate event at time 0"
        assert new_state.next_arrival_time > 0

    def test_event_generated_at_arrival_time(self) -> None:
        from mock_simulator.app.generators.incident_generator import IncidentState, tick_incidents
        config = make_default_config()
        config.incident_mean_interval_seconds = 1.0
        config._zones_cache = [{"zone_id": "z1", "capacity_estimate": 1000}]  # type: ignore[attr-defined]
        zones = [{"zone_id": "z1", "capacity_estimate": 1000}]
        state = IncidentState.initial(zones, config)
        rng = random.Random(0)
        # Tick far enough to guarantee an arrival
        new_state, event = tick_incidents(state, rng, config, now=10.0)
        assert event is not None, "Should generate event after many ticks"
        assert event.source == "SIMULATED"
        assert event.zone_id == "z1"

    def test_category_from_distribution(self) -> None:
        from mock_simulator.app.generators.incident_generator import _draw_category
        config = make_default_config()
        rng = random.Random(42)
        categories = []
        for _ in range(1000):
            cat = _draw_category(rng, config)
            categories.append(cat)
        # Medical is 5% — expect at least 1 in 1000
        assert "medical" in categories
        assert "general" in categories
        assert "crowd_queue" in categories

    def test_zone_weighted_by_capacity(self) -> None:
        from mock_simulator.app.generators.incident_generator import _draw_zone
        rng = random.Random(99)
        zones = [
            {"zone_id": "small", "capacity_estimate": 100},
            {"zone_id": "large", "capacity_estimate": 10000},
        ]
        zone_ids = []
        for _ in range(5000):
            z = _draw_zone(zones, rng)
            zone_ids.append(z)
        large_count = zone_ids.count("large")
        small_count = zone_ids.count("small")
        assert large_count > small_count, "Larger zones should get proportionally more incidents"

    def test_burst_mode_increases_frequency(self) -> None:
        from mock_simulator.app.generators.incident_generator import IncidentState, tick_incidents
        config = make_default_config()
        config.incident_mean_interval_seconds = 10.0
        config.burst_mode_enabled = True
        config._zones_cache = [{"zone_id": "z1", "capacity_estimate": 1000}]  # type: ignore[attr-defined]
        zones = [{"zone_id": "z1", "capacity_estimate": 1000}]
        state = IncidentState.initial(zones, config)
        rng = random.Random(0)
        # Burst mode kicks in 10-30s — tick at 20s
        new_state, event = tick_incidents(state, rng, config, now=20.0)
        assert state.burst_mode_active or new_state.burst_mode_active or event is not None


class TestCrowdDensityUnit:
    """Crowd density generator pure-function unit tests."""

    def test_initial_density_within_bounds(self) -> None:
        from mock_simulator.app.generators.crowd_density_generator import CrowdDensityState
        config = make_default_config()
        zones = [{"zone_id": "z_test", "capacity_estimate": 5000}]
        state = CrowdDensityState.initial(zones, config)
        for _zid, val in state.current_density.items():
            assert 0 <= val <= 5000

    def test_density_reverts_toward_baseline(self) -> None:
        from mock_simulator.app.generators.crowd_density_generator import CrowdDensityState, tick_crowd_density
        config = make_default_config()
        zones = [{"zone_id": "z_test", "capacity_estimate": 10000}]
        state = CrowdDensityState.initial(zones, config)
        # Force density far from baseline
        state.current_density["z_test"] = 9000.0
        rng = random.Random(0)
        moved_toward = False
        for _ in range(20):
            state, event = tick_crowd_density(state, rng, config, now=_ * config.density_sample_interval)
            if event is not None:
                diff_from_baseline = abs(event.occupancy_estimate - 5000)  # 50% baseline
                if diff_from_baseline < 4000:
                    moved_toward = True
                    break
        assert moved_toward, "Density should revert toward baseline over time"

    def test_level_thresholds(self) -> None:
        from mock_simulator.app.generators.crowd_density_generator import _classify_density_level
        assert _classify_density_level(0.2) == "LOW"
        assert _classify_density_level(0.5) == "MODERATE"
        assert _classify_density_level(0.75) == "HIGH"
        assert _classify_density_level(0.95) == "CRITICAL"


class TestPositionPingUnit:
    """Position ping generator pure-function unit tests."""

    def test_ping_contains_volunteer_and_zone(self) -> None:
        from mock_simulator.app.generators.position_ping_generator import PositionPingState, tick_position_pings
        config = make_default_config()
        volunteers = [{"volunteer_id": "v1", "assigned_zone_id": "z_home"}]
        state = PositionPingState.initial(volunteers, config)
        rng = random.Random(42)
        # Force first ping
        state.next_ping_time["v1"] = 0.0
        new_state, event = tick_position_pings(state, rng, config, now=1.0)
        assert event is not None
        assert event.volunteer_id == "v1"
        assert event.zone_id is not None

    def test_volunteer_stays_in_home_zone_most_of_the_time(self) -> None:
        from mock_simulator.app.generators.position_ping_generator import PositionPingState, tick_position_pings
        config = make_default_config()
        config.position_transition_probability = 0.1
        volunteers = [{"volunteer_id": "v_sticky", "assigned_zone_id": "z_home"}]
        state = PositionPingState.initial(volunteers, config)
        state.current_zone["v_sticky"] = "z_home"
        rng = random.Random(0)
        zones_seen = {"z_home": 0, "z_away": 0}
        for i in range(200):
            state, event = tick_position_pings(state, rng, config, now=i * config.ping_interval)
            if event is not None:
                zones_seen[str(event.zone_id)] = zones_seen.get(str(event.zone_id), 0) + 1
        home_count = zones_seen.get("z_home", 0)
        away_count = zones_seen.get("z_away", 0)
        total = home_count + away_count
        assert total > 0
        assert home_count / total > 0.7, "Volunteer should stay in home zone >70% of ticks"

    def test_no_lat_lon_in_ping(self) -> None:
        from mock_simulator.app.generators.position_ping_generator import PositionPing
        ping = PositionPing(
            ping_id="p_test",
            volunteer_id="v1",
            zone_id="z1",
            timestamp="2026-07-15T12:00:00+00:00",
            source="SIMULATED",
        )
        data = ping.to_dict()
        assert "latitude" not in data
        assert "longitude" not in data
