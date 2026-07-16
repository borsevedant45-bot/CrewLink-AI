"""Volunteer position ping generator — sticky Markov-chain zone model.

Doc #3 §4.3: Pure function (state, rng, config) → (new_state, event | None).
Fixed interval per volunteer, zone-level only (no lat/long).
All randomness from seeded `rng` — deterministic IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _make_id(rng: Any, prefix: str = "ping") -> str:
    return f"{prefix}_{rng.getrandbits(64):016x}"


@dataclass
class PositionPing:
    ping_id: str
    volunteer_id: str
    zone_id: str
    timestamp: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ping_id": self.ping_id,
            "volunteer_id": self.volunteer_id,
            "zone_id": self.zone_id,
            "timestamp": self.timestamp,
            "source": self.source,
        }


@dataclass
class PositionPingState:
    current_zone: dict[str, str]
    next_ping_time: dict[str, float]

    @classmethod
    def initial(
        cls,
        volunteers: list[dict[str, Any]],
        config: Any,
    ) -> PositionPingState:
        cur_zone: dict[str, str] = {}
        next_ping: dict[str, float] = {}
        import random as _random
        rng = _random.Random(config.random_seed + 2000)
        for v in volunteers:
            vid = v["volunteer_id"]
            cur_zone[vid] = v["assigned_zone_id"]
            next_ping[vid] = rng.uniform(0, config.ping_interval)
        return cls(current_zone=cur_zone, next_ping_time=next_ping)


def _format_iso_timestamp(now: float) -> str:
    hours = int(now // 3600)
    minutes = int((now % 3600) // 60)
    seconds = int(now % 60)
    return f"2026-07-15T{hours:02d}:{minutes:02d}:{seconds:02d}+00:00"


def generate_ping_event(
    volunteer_id: str,
    zone_id: str,
    timestamp: str,
) -> PositionPing:
    """Generate a single ping event deterministically for testing."""
    import random
    rng = random.Random(8888)
    return PositionPing(
        ping_id=_make_id(rng),
        volunteer_id=volunteer_id,
        zone_id=zone_id,
        timestamp=timestamp,
        source="SIMULATED",
    )


def tick_position_pings(
    state: PositionPingState,
    rng: Any,
    config: Any,
    now: float,
) -> tuple[PositionPingState, PositionPing | None]:
    """Pure function: tick position pings for all volunteers.

    Sticky Markov-chain: each volunteer stays in their current zone with
    probability (1 - transition_probability), otherwise moves to a weighted-random zone.
    All IDs from seeded `rng`.

    Returns (new_state, event | None).
    """
    new_zones = dict(state.current_zone)
    new_times = dict(state.next_ping_time)
    event: PositionPing | None = None
    zone_ids = list(set(state.current_zone.values()))

    for vid in list(new_zones.keys()):
        if now < state.next_ping_time.get(vid, float("inf")):
            continue

        current = new_zones[vid]

        if rng.random() < config.position_transition_probability:
            other_zones = [z for z in zone_ids if z != current]
            if other_zones:
                new_zone = rng.choice(other_zones)
                new_zones[vid] = new_zone
            else:
                new_zone = current
        else:
            new_zone = current

        event = PositionPing(
            ping_id=_make_id(rng),
            volunteer_id=vid,
            zone_id=new_zone,
            timestamp=_format_iso_timestamp(now),
            source="SIMULATED",
        )

        jitter = rng.uniform(-config.ping_interval * 0.2, config.ping_interval * 0.2)
        new_times[vid] = now + config.ping_interval + jitter

    new_state = PositionPingState(current_zone=new_zones, next_ping_time=new_times)
    return new_state, event
