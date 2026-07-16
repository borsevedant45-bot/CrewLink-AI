"""Priority-score calculator for incident triage.

Doc #3 §2.1: priority_score is deliberately not a raw model output.
It combines category severity, zone crowd density, and queue-wait estimate.

Weights documented below are the author's own calibration, not sourced from
CrewLink AI design docs. They are a placeholder for future ML-based scoring.
"""

from __future__ import annotations

from typing import Literal

Category = Literal[
    "medical", "lost_fan", "translation", "accessibility",
    "crowd_queue", "lost_item", "general",
]

DensityLevel = Literal["LOW", "MODERATE", "HIGH", "CRITICAL"] | None

# Base severity per category (author's calibration, not from docs)
_BASE_SEVERITY: dict[str, int] = {
    "medical": 60,
    "crowd_queue": 45,
    "accessibility": 35,
    "lost_fan": 30,
    "translation": 20,
    "lost_item": 15,
    "general": 10,
}

# Crowd-density multiplier (author's calibration)
_DENSITY_MULTIPLIER: dict[str, float] = {
    "LOW": 1.0,
    "MODERATE": 1.2,
    "HIGH": 1.5,
    "CRITICAL": 2.0,
}

# Queue-wait contribution: +0.5 per minute, capped at +20
_QUEUE_WAIT_PER_MINUTE = 0.5
_QUEUE_WAIT_MAX_BONUS = 20


def compute_priority_score(
    category: str,
    crowd_density_level: DensityLevel = None,
    queue_wait_minutes: float | None = None,
) -> int:
    """Compute a deterministic priority score in [0, 100].

    Weights (author's calibration, not from CrewLink AI design docs):
      - category_base : fixed per category (see _BASE_SEVERITY)
      - density_mult  : 1.0–2.0x based on zone crowd density
      - queue_bonus   : +0.5/min for CROWD_QUEUE incidents only, cap +20

    Doc #3 §2.1: priority_score combines category, crowd density, and queue wait.
    """
    base = _BASE_SEVERITY.get(category, 10)

    density_mult = _DENSITY_MULTIPLIER.get(crowd_density_level or "LOW", 1.0)

    score = float(base) * density_mult

    if category == "crowd_queue" and queue_wait_minutes is not None:
        bonus = min(queue_wait_minutes * _QUEUE_WAIT_PER_MINUTE, _QUEUE_WAIT_MAX_BONUS)
        score += bonus

    return max(0, min(100, round(score)))
