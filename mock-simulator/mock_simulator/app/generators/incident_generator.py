"""Incident generator — Poisson-process, templated raw_description, zone-weighted.

Doc #3 §4.1: Pure function (state, rng, config) → (new_state, event | None).
All randomness comes from the seeded `rng` argument — no uuid.uuid4() calls,
ensuring deterministic reproducibility.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


def _make_id(rng: Any, prefix: str = "inc") -> str:
    """Deterministic ID from seeded RNG, replacing uuid.uuid4()."""
    return f"{prefix}_{rng.getrandbits(64):016x}"


@dataclass
class IncidentEvent:
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "category": self.category,
            "subcategory": self.subcategory,
            "raw_description": self.raw_description,
            "source": self.source,
            "zone_id": self.zone_id,
            "reported_by_volunteer_id": self.reported_by_volunteer_id,
            "priority_score": self.priority_score,
            "status": self.status,
            "created_at": self.created_at,
            "queue_wait_estimate_minutes": self.queue_wait_estimate_minutes,
            "item_description": self.item_description,
            "medical_severity_hint": self.medical_severity_hint,
        }


@dataclass
class IncidentState:
    next_arrival_time: float
    burst_mode_active: bool
    burst_end_time: float
    _rng_state: tuple[Any, ...] | None = None  # for determinism

    @classmethod
    def initial(
        cls,
        zones: list[dict[str, Any]],  # noqa: ARG003
        config: Any,
    ) -> IncidentState:
        import random as _random
        rng = _random.Random(config.random_seed + 3000)
        # Draw first arrival in (0, mean_interval)
        uniform = rng.random()
        first_arrival = -math.log(max(uniform, 1e-10)) * config.incident_mean_interval_seconds
        return cls(
            next_arrival_time=first_arrival,
            burst_mode_active=False,
            burst_end_time=0.0,
        )


# --- Templates per category (templated, not LLM-generated) ---

_TEMPLATES: dict[str, list[str]] = {
    "medical": [
        "Fan reports {symptom} at {location}",
        "Guest experiencing {symptom} near {location}",
        "Medical assistance needed: {symptom} at {location}",
    ],
    "crowd_queue": [
        "Long queue forming at {location}",
        "Crowd bottleneck reported at {location}",
        "Queue backed up significantly at {location}",
    ],
    "lost_fan": [
        "Fan separated from group at {location}",
        "Lost guest reported at {location}",
        "Individual looking for party at {location}",
    ],
    "lost_item": [
        "Found {item} at {location}",
        "Guest reports lost {item} near {location}",
        "{item} handed in at {location}",
    ],
    "translation": [
        "Fan needs {language} help at {location}",
        "Translation requested for {language} speaker at {location}",
        "Guest requires {language} assistance at {location}",
    ],
    "accessibility": [
        "Wheelchair assistance needed at {location}",
        "Accessibility request at {location}",
        "Guest needs mobility aid at {location}",
    ],
    "general": [
        "Guest inquiry at {location}",
        "Information request at {location}",
        "General assistance needed at {location}",
    ],
}

_SYMPTOMS: list[str] = [
    "dizziness", "headache", "nausea", "shortness of breath",
    "chest discomfort", "bleeding from minor cut", "fainting",
    "dehydration", "heat exhaustion symptoms",
]

_ITEMS: list[str] = [
    "phone", "wallet", "keys", "bag", "jacket",
    "camera", "hat", "scarf", "water bottle", "ticket",
]

_LOCATIONS_QUALIFIER: list[str] = [
    "the main concourse", "Gate 4", "Gate 7",
    "Section 110", "Section 205", "the guest services desk",
    "the east restrooms", "the west concession stand",
    "the north stairwell", "the south exit",
]

_LANGUAGES: list[str] = [
    "Spanish", "Portuguese", "French", "Arabic", "Japanese", "Korean", "German",
]


def _format_iso_timestamp(now: float) -> str:
    hours = int(now // 3600)
    minutes = int((now % 3600) // 60)
    seconds = int(now % 60)
    return f"2026-07-15T{hours:02d}:{minutes:02d}:{seconds:02d}+00:00"


def _draw_category(rng: Any, config: Any) -> str:
    """Weighted random draw from category distribution."""
    cats: list[str] = list(config.category_weights.keys())
    weights: list[float] = list(config.category_weights.values())
    result: str = rng.choices(cats, weights=weights, k=1)[0]
    return result


def _draw_zone(zones: list[dict[str, Any]], rng: Any) -> str:
    """Weighted zone selection by capacity_estimate."""
    if not zones:
        return "zone_unknown"
    weights: list[int] = [int(z["capacity_estimate"]) for z in zones]
    result: dict[str, Any] = rng.choices(zones, weights=weights, k=1)[0]
    return str(result["zone_id"])


def _build_raw_description(category: str, rng: Any) -> str:
    templates: list[str] = _TEMPLATES.get(category, _TEMPLATES["general"])
    template: str = rng.choice(templates)
    location: str = rng.choice(_LOCATIONS_QUALIFIER)
    subs: dict[str, str] = {"location": location}
    if category == "medical":
        subs["symptom"] = str(rng.choice(_SYMPTOMS))
    elif category == "lost_item":
        subs["item"] = str(rng.choice(_ITEMS))
    elif category == "translation":
        subs["language"] = str(rng.choice(_LANGUAGES))
    return str(template.format(**subs))


def _priority_base(category: str) -> int:
    scores: dict[str, int] = {
        "medical": 60, "crowd_queue": 45, "accessibility": 35,
        "lost_fan": 30, "translation": 20, "lost_item": 15, "general": 10,
    }
    return scores.get(category, 10)


def generate_incident_event(
    category: str,
    zone_id: str,
    rng_seed: int | str | None = None,
) -> IncidentEvent:
    """Generate a single incident event deterministically for testing."""
    import random
    rng = random.Random(rng_seed) if rng_seed is not None else random.Random()
    raw = _build_raw_description(category, rng)
    now = 100.0
    return IncidentEvent(
        incident_id=_make_id(rng),
        category=category,
        subcategory=None,
        raw_description=raw,
        source="SIMULATED",
        zone_id=zone_id,
        reported_by_volunteer_id=None,
        priority_score=_priority_base(category),
        status="Reported",
        created_at=_format_iso_timestamp(now),
        queue_wait_estimate_minutes=15.0 if category == "crowd_queue" else None,
        item_description=rng.choice(_ITEMS) if category == "lost_item" else None,
        medical_severity_hint=rng.choice(["low", "medium", "high"]) if category == "medical" else None,
    )


def tick_incidents(
    state: IncidentState,
    rng: Any,
    config: Any,
    now: float,
) -> tuple[IncidentState, IncidentEvent | None]:
    """Pure function: given current state, produce next incident or None.

    All event IDs are derived from the seeded `rng` for deterministic reproducibility.
    Zone assignments use `config._zones_cache` (set by Simulator) or empty list.

    Returns (new_state, event).
    """
    zones = getattr(config, "_zones_cache", [])
    next_arrival = state.next_arrival_time
    burst_active = state.burst_mode_active
    burst_end = state.burst_end_time

    if config.burst_mode_enabled and not burst_active and now >= config.burst_start_offset:
        burst_active = True
        burst_end = now + config.burst_duration

    if burst_active and now >= burst_end:
        burst_active = False

    effective_interval = config.incident_mean_interval_seconds
    if burst_active:
        effective_interval /= config.burst_multiplier

    if now < next_arrival:
        return state, None

    # Generate incident
    category = _draw_category(rng, config)
    zone_id = _draw_zone(zones, rng) if zones else "zone_unknown"
    raw_description = _build_raw_description(category, rng)

    event = IncidentEvent(
        incident_id=_make_id(rng),
        category=category,
        subcategory=None,
        raw_description=raw_description,
        source="SIMULATED",
        zone_id=zone_id,
        reported_by_volunteer_id=None,
        priority_score=_priority_base(category),
        status="Reported",
        created_at=_format_iso_timestamp(now),
        queue_wait_estimate_minutes=15.0 if category == "crowd_queue" else None,
        item_description=rng.choice(_ITEMS) if category == "lost_item" else None,
        medical_severity_hint=rng.choice(["low", "medium", "high"]) if category == "medical" else None,
    )

    # Schedule next arrival (Poisson: inter-arrival = -ln(U) * mean)
    uniform = rng.random()
    inter_arrival = -math.log(max(uniform, 1e-10)) * effective_interval
    next_arrival = now + inter_arrival

    new_state = IncidentState(
        next_arrival_time=next_arrival,
        burst_mode_active=burst_active,
        burst_end_time=burst_end,
    )
    return new_state, event
