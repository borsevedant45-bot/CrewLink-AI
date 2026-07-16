"""Doc #4 §4 — Structured output schemas.

Every model here is the single source of truth for the contract with the LLM.
The JSON Schema sent to the provider is generated from these models via
``model_json_schema()``, not hand-maintained separately.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# ===========================================================================
# 4(a) Incident Classifier
# ===========================================================================


class Category(StrEnum):
    """Doc #3 §2.3 taxonomy — seven fixed categories (ADDENDUM G5: translation)."""

    MEDICAL = "medical"
    LOST_FAN = "lost_fan"
    TRANSLATION = "translation"
    ACCESSIBILITY = "accessibility"
    CROWD_QUEUE = "crowd_queue"
    LOST_ITEM = "lost_item"
    GENERAL = "general"


class Severity(StrEnum):
    """Coarse severity signal (ADDENDUM G4: renamed to urgency_signal at serialization)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IncidentClassification(BaseModel):
    """Doc #4 §4 — Classifier structured output."""

    model_config = ConfigDict(extra="forbid")

    category: Category
    severity_signal: Severity
    requires_emergency_escalation: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_summary: str = Field(max_length=200)
    detected_language: str | None = None


# ===========================================================================
# 4(b) Intent Router
# ===========================================================================


class IntentType(StrEnum):
    """Doc #4 §2 — Ask CrewLink front-door routing."""

    FACILITY_SAFETY_PROCEDURE = "facility_safety_procedure"
    TRANSLATION_REQUEST = "translation_request"
    SMALL_TALK = "small_talk"
    STATUS_OR_LOGISTICS = "status_or_logistics"
    OUT_OF_SCOPE = "out_of_scope"


class IntentClassification(BaseModel):
    """Doc #4 §2 — Intent router structured output."""

    model_config = ConfigDict(extra="forbid")

    intent: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    detected_language: str | None = None


# ===========================================================================
# 4(c) Translation Bridge
# ===========================================================================


class TranslationResult(BaseModel):
    """Doc #4 §3(c) — Translation Bridge structured output."""

    model_config = ConfigDict(extra="forbid")

    translated_text: str
    detected_language: str
    confidence: float = Field(ge=0.0, le=1.0)
    emergency_flag: bool
    back_translation: str | None = None
    high_stakes: bool = False


# ===========================================================================
# 4(d) Dispatch Recommender
# ===========================================================================


class DispatchCandidate(BaseModel):
    """Doc #4 §4 — One recommended volunteer."""

    model_config = ConfigDict(extra="forbid")

    volunteer_id: str
    rank: int = Field(ge=1, le=3)
    rationale: str = Field(max_length=200)


class DispatchRecommendation(BaseModel):
    """Doc #4 §4 — Dispatch Recommender structured output."""

    model_config = ConfigDict(extra="forbid")

    recommended_volunteers: list[DispatchCandidate] = Field(min_length=1, max_length=3)
    requires_human_supervisor_review: bool
    confidence: float = Field(ge=0.0, le=1.0)


# ===========================================================================
# 4(e) Ask CrewLink RAG Assistant
# ===========================================================================


class GroundedAnswer(BaseModel):
    """Doc #4 §3(d) — Ask CrewLink structured output."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    grounded: bool
    sources: list[str] = Field(default_factory=list)


# ===========================================================================
# 4(f) Shift Summary (Reasoning tier)
# ===========================================================================


class ShiftSummary(BaseModel):
    """Doc #4 §4 — Shift Summary structured output (Reasoning tier)."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(max_length=1000)
    incident_count: int = Field(ge=0)
    notable_events: list[str] = Field(default_factory=list)
    crowd_density_peak: str | None = None
    fallback_used: bool = False
