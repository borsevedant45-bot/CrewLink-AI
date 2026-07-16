"""All mock-simulator config values in one module.

Doc #3 §4 config defaults, with Doc #3 §4's illustrative values as defaults.
Where the doc gives a range, the specific value is my own choice, flagged below.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SimulatorConfig:
    # --- §4.1: Incident Generator ---
    # Mean inter-arrival time (seconds). Doc #3 §4.1 range: 45-90s.
    # MY CHOICE: 60s — midpoint of the documented range.
    incident_mean_interval_seconds: float = 60.0

    # Category weights (7 categories, must sum to 100). Doc #3 §4.1 table.
    category_weights: dict[str, float] = field(default_factory=lambda: {
        "general": 0.25,
        "crowd_queue": 0.20,
        "lost_fan": 0.15,
        "lost_item": 0.15,
        "translation": 0.10,
        "accessibility": 0.10,
        "medical": 0.05,
    })

    # Burst mode toggle — when enabled, a post-goal surge of CROWD_QUEUE and
    # LOST_FAN incidents for ~20s starting 10s into simulation.
    burst_mode_enabled: bool = True
    burst_start_offset: float = 10.0
    burst_duration: float = 20.0
    burst_multiplier: float = 5.0

    # --- §4.2: Crowd Density Generator ---
    # Sampling interval per zone (seconds). Doc #3 §4.2 range: 15-30s.
    # MY CHOICE: 20s — midpoint of the documented range.
    density_sample_interval: float = 20.0

    # Mean-reversion strength per tick (0-1). MY CHOICE: 0.05 for gentle drift.
    density_mean_reversion: float = 0.05

    # Random walk volatility (max delta as fraction of capacity).
    # MY CHOICE: 0.03 — 3% of capacity per tick.
    density_volatility: float = 0.03

    # Density level thresholds (as fraction of capacity). Doc #3 §4.2 exact table.
    density_low_threshold: float = 0.40
    density_moderate_threshold: float = 0.70
    density_high_threshold: float = 0.90

    # Baseline occupancy by time-of-day (fraction of capacity).
    # Authored shape: low pre-match, peak at kickoff/halftime, spike at final whistle.
    # Doc #3 §4.2 calls this "an illustrative authored shape, not derived from real data."
    # MY CHOICE: 6 time points over a 180-minute match window.
    baseline_times: list[float] = field(default_factory=lambda: [
        0.0,    # pre-match
        30.0,   # early match
        60.0,   # ~kickoff
        90.0,   # halftime
        120.0,  # post-halftime
        150.0,  # final whistle
    ])
    baseline_occupancy: list[float] = field(default_factory=lambda: [
        0.10,  # pre-match: 10%
        0.30,  # early: 30%
        0.70,  # kickoff: 70%
        0.50,  # halftime: 50% (concourse surge)
        0.65,  # post-halftime: 65%
        0.85,  # final whistle: 85% spike
    ])

    # --- §4.3: Position Ping Generator ---
    # Ping interval per active volunteer (seconds). Doc #3 §4.3 range: 20-40s.
    # MY CHOICE: 30s — midpoint.
    ping_interval: float = 30.0

    # Per-tick probability of transitioning to a different zone.
    # Doc #3 §4.3 range: 10-15%. MY CHOICE: 12% — midpoint.
    position_transition_probability: float = 0.12

    # --- General ---
    # Backend internal API base URL.
    backend_url: str = "http://backend:8000"

    # Internal auth token (must match backend's settings.simulator_auth_token).
    internal_auth_token: str = "sim-service-token-change-in-prod"

    # Master random seed for reproducibility.
    random_seed: int = 42

    # Simulation tick interval (seconds). Tick rate of the main loop.
    # MY CHOICE: 1.0s — fine enough for 20-30s sampling intervals.
    tick_interval: float = 1.0


def make_default_config() -> SimulatorConfig:
    return SimulatorConfig()
