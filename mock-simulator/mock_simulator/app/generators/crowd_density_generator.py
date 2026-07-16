"""Crowd density generator — bounded mean-reverting random walk per zone.

Doc #3 §4.2: Pure function (state, rng, config) → (new_state, event | None).
Fixed-interval sampling, baseline curve, density_level classification.
All randomness from seeded `rng` — deterministic IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _make_id(rng: Any, prefix: str = "den") -> str:
    return f"{prefix}_{rng.getrandbits(64):016x}"


@dataclass
class CrowdDensityEvent:
    reading_id: str
    zone_id: str
    timestamp: str
    occupancy_estimate: int
    density_ratio: float
    density_level: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "reading_id": self.reading_id,
            "zone_id": self.zone_id,
            "timestamp": self.timestamp,
            "occupancy_estimate": self.occupancy_estimate,
            "density_ratio": self.density_ratio,
            "density_level": self.density_level,
            "source": self.source,
        }


@dataclass
class CrowdDensityState:
    current_density: dict[str, float]
    next_sample_time: dict[str, float]
    zone_capacities: dict[str, int]

    @classmethod
    def initial(
        cls,
        zones: list[dict[str, Any]],
        config: Any,
    ) -> CrowdDensityState:
        import random as _random
        rng = _random.Random(config.random_seed + 1000)
        cur: dict[str, float] = {}
        caps: dict[str, int] = {}
        next_times: dict[str, float] = {}
        for z in zones:
            zid = z["zone_id"]
            cap = z["capacity_estimate"]
            caps[zid] = cap
            baseline = _baseline_at_time(config, 0.0)
            cur[zid] = rng.uniform(
                baseline * cap * 0.5,
                baseline * cap * 1.5,
            )
            next_times[zid] = rng.uniform(0, config.density_sample_interval)
        return cls(
            current_density=cur,
            next_sample_time=next_times,
            zone_capacities=caps,
        )


def _format_iso_timestamp(now: float) -> str:
    hours = int(now // 3600)
    minutes = int((now % 3600) // 60)
    seconds = int(now % 60)
    return f"2026-07-15T{hours:02d}:{minutes:02d}:{seconds:02d}+00:00"


def _baseline_at_time(config: Any, now: float) -> float:
    """Interpolate the authored baseline curve at time *now* (seconds)."""
    times: list[float] = list(config.baseline_times)
    values: list[float] = list(config.baseline_occupancy)
    if now <= times[0]:
        return values[0]
    if now >= times[-1]:
        return values[-1]
    for i in range(len(times) - 1):
        if times[i] <= now <= times[i + 1]:
            frac = (now - times[i]) / (times[i + 1] - times[i])
            return values[i] + frac * (values[i + 1] - values[i])
    return values[-1]


def _classify_density_level(ratio: float, config: Any | None = None) -> str:
    """Classify density ratio into LOW/MODERATE/HIGH/CRITICAL.

    Doc #3 §4.2 threshold table: <40% LOW, 40-70% MODERATE, 70-90% HIGH, >90% CRITICAL.
    """
    if config:
        if ratio >= config.density_high_threshold:
            return "CRITICAL"
        if ratio >= config.density_moderate_threshold:
            return "HIGH"
        if ratio >= config.density_low_threshold:
            return "MODERATE"
        return "LOW"
    if ratio >= 0.90:
        return "CRITICAL"
    if ratio >= 0.70:
        return "HIGH"
    if ratio >= 0.40:
        return "MODERATE"
    return "LOW"


def generate_density_event(
    zone_id: str,
    occupancy: int,
    capacity: int,
    timestamp: str,
) -> CrowdDensityEvent:
    """Generate a single density event deterministically for testing."""
    import random
    rng = random.Random(9999)
    ratio = occupancy / max(capacity, 1)
    return CrowdDensityEvent(
        reading_id=_make_id(rng),
        zone_id=zone_id,
        timestamp=timestamp,
        occupancy_estimate=occupancy,
        density_ratio=round(ratio, 4),
        density_level=_classify_density_level(ratio),
        source="SIMULATED",
    )


def tick_crowd_density(
    state: CrowdDensityState,
    rng: Any,
    config: Any,
    now: float,
) -> tuple[CrowdDensityState, CrowdDensityEvent | None]:
    """Pure function: bounded mean-reverting random walk per zone.

    All event IDs derived from seeded `rng` for deterministic reproducibility.
    Returns (new_state, event | None).
    """
    new_density = dict(state.current_density)
    new_times = dict(state.next_sample_time)
    event: CrowdDensityEvent | None = None
    dt = config.density_sample_interval
    mean_revert = config.density_mean_reversion
    volatility = config.density_volatility

    for zid in list(new_density.keys()):
        if now < state.next_sample_time.get(zid, float("inf")):
            continue

        cap = state.zone_capacities.get(zid, 1000)
        baseline = _baseline_at_time(config, now)
        target = baseline * cap
        prev = new_density[zid]

        drift = (target - prev) * mean_revert
        noise = rng.gauss(0, volatility * cap)
        new_val = prev + drift + noise

        new_val = max(0.0, min(new_val, float(cap)))
        new_density[zid] = new_val

        ratio = new_val / max(cap, 1)
        level = _classify_density_level(ratio, config)

        event = CrowdDensityEvent(
            reading_id=_make_id(rng),
            zone_id=zid,
            timestamp=_format_iso_timestamp(now),
            occupancy_estimate=round(new_val),
            density_ratio=round(ratio, 4),
            density_level=level,
            source="SIMULATED",
        )

        jitter = rng.uniform(-dt * 0.2, dt * 0.2)
        new_times[zid] = now + dt + jitter

    new_state = CrowdDensityState(
        current_density=new_density,
        next_sample_time=new_times,
        zone_capacities=state.zone_capacities,
    )
    return new_state, event
