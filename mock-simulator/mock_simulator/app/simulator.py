"""Main simulator loop — orchestrates all three generators.

Runs a tick loop at config.tick_interval, calling each generator's pure function
and posting resulting events to the backend via IngestClient.
"""

from __future__ import annotations

import random
import time as _time
from typing import Any

from mock_simulator.app.config import SimulatorConfig
from mock_simulator.app.generators.crowd_density_generator import (
    CrowdDensityState,
    tick_crowd_density,
)
from mock_simulator.app.generators.incident_generator import (
    IncidentState,
    tick_incidents,
)
from mock_simulator.app.generators.position_ping_generator import (
    PositionPingState,
    tick_position_pings,
)
from mock_simulator.app.ingest_client import IngestClient


def _sync_state(
    zones: list[dict[str, Any]],
    volunteers: list[dict[str, Any]],
    config: SimulatorConfig,
) -> tuple[IncidentState, CrowdDensityState, PositionPingState, random.Random]:
    rng = random.Random(config.random_seed)
    config._zones_cache = zones  # type: ignore[attr-defined]
    inc_state = IncidentState.initial(zones, config)
    den_state = CrowdDensityState.initial(zones, config)
    ping_state = PositionPingState.initial(volunteers, config)
    return inc_state, den_state, ping_state, rng


class Simulator:
    """Main simulation orchestrator."""

    def __init__(
        self,
        config: SimulatorConfig,
        zones: list[dict[str, Any]],
        volunteers: list[dict[str, Any]],
        client: IngestClient | None = None,
    ) -> None:
        self._config = config
        self._client = client
        self._inc_state, self._den_state, self._ping_state, self._rng = _sync_state(
            zones, volunteers, config,
        )
        self._tick_count: int = 0

    @property
    def tick_count(self) -> int:
        return self._tick_count

    def step(self) -> list[dict[str, Any]]:
        """Execute one simulation tick. Returns list of event dicts produced."""
        now = self._tick_count * self._config.tick_interval
        events: list[dict[str, Any]] = []

        self._inc_state, inc_event = tick_incidents(
            self._inc_state, self._rng, self._config, now,
        )
        if inc_event:
            events.append(inc_event.to_dict())

        self._den_state, den_event = tick_crowd_density(
            self._den_state, self._rng, self._config, now,
        )
        if den_event:
            events.append(den_event.to_dict())

        self._ping_state, ping_event = tick_position_pings(
            self._ping_state, self._rng, self._config, now,
        )
        if ping_event:
            events.append(ping_event.to_dict())

        self._tick_count += 1
        return events

    def run(self, max_ticks: int | None = None, live: bool = False) -> None:
        """Run the simulation loop.

        Args:
            max_ticks: If set, stop after this many ticks.
            live: If True, post to backend via IngestClient and sleep between ticks.
        """
        while max_ticks is None or self._tick_count < max_ticks:
            events = self.step()
            if live and self._client:
                for ev in events:
                    if "reading_id" in ev:
                        self._client.post_crowd_density(ev)
                    elif "ping_id" in ev:
                        self._client.post_position_ping(ev)
                    else:
                        self._client.post_incident(ev)
            if live:
                _time.sleep(self._config.tick_interval)
