"""Doc #4 §2 + §3(d) — Ask CrewLink service: intent router + 5-branch handler.

Implements the grounding-boundary branching from Doc #4 §2:
  1. Intent routing (Fast/Cheap) — classify query into 5 intents.
  2. Four non-FACILITY branches never touch KB retrieval or Reasoning tier.
  3. FACILITY_SAFETY_PROCEDURE: retrieve → threshold gate → synthesis (Reasoning).
     The synthesis call carries the LIVE EMERGENCY OVERRIDE prompt (Doc #4 §3(d))
     so the model checks for live emergencies before answering from KB.

Doc #8 §3.3 — multilingual wrapper:
  - Query is converted to English before retrieval/synthesis.
  - Final answer is translated back to the volunteer's language.
  Both extra calls use the Fast/Cheap tier, separate from the Reasoning tier.

Every response carries descriptive fields per Doc #5 §2.8.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.config import settings
from backend.app.services.kb_retrieval import retrieve_chunks
from backend.app.services.prompts import (
    ASK_CREWLINK_SYSTEM_PROMPT,
    INTENT_ROUTER_SYSTEM_PROMPT,
)
from backend.orchestration.completion import complete_with_fallback
from backend.orchestration.interfaces import ModelRouter, TaskType
from backend.orchestration.logging_ import LogCallback
from backend.orchestration.schemas import (
    GroundedAnswer,
    IntentClassification,
    IntentType,
)

logger = logging.getLogger("crewlink.ask_crewlink")


# ---------------------------------------------------------------------------
# API response models (Doc #5 §2.8)
# ---------------------------------------------------------------------------


class SourceCitation(BaseModel):
    """A single knowledge-base source cited in an Ask CrewLink answer."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    chunk_id: str
    title: str


class AskCrewLinkResult(BaseModel):
    """Doc #5 §2.8 — Ask CrewLink response."""

    model_config = ConfigDict(extra="forbid")

    answer: str | None = None
    grounded: bool = False
    confidence: float = 0.0
    sources: list[SourceCitation] = Field(default_factory=list)
    fallback_message: str | None = None
    fallback_used: bool = False


# ---------------------------------------------------------------------------
# Templated responses for non-FACILITY branches
# ---------------------------------------------------------------------------

_TEMPLATED_REPLIES: dict[IntentType, AskCrewLinkResult] = {
    IntentType.SMALL_TALK: AskCrewLinkResult(
        answer=(
            "I'm here to help with venue questions about Founders Field! "
            "If you have a question about facilities, safety, "
            "or procedures, feel free to ask."
        ),
        grounded=False,
        confidence=1.0,
    ),
    IntentType.STATUS_OR_LOGISTICS: AskCrewLinkResult(
        answer=(
            "For status updates on your tasks or shift schedule, "
            "please check your task feed or contact your zone supervisor. "
            "I can help with questions about the venue, facilities, "
            "and procedures."
        ),
        grounded=False,
        confidence=1.0,
    ),
    IntentType.OUT_OF_SCOPE: AskCrewLinkResult(
        grounded=False,
        confidence=1.0,
        fallback_message=(
            "I can only answer questions about Founders Field's facilities, "
            "safety procedures, accessibility resources, and venue operations. "
            "Please ask your zone supervisor for help with other questions."
        ),
    ),
    IntentType.TRANSLATION_REQUEST: AskCrewLinkResult(
        grounded=False,
        confidence=1.0,
        fallback_message=(
            "This sounds like a translation request. "
            "Please use the Chat Bridge for translation assistance "
            "between languages."
        ),
    ),
}


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------


async def handle_ask_crewlink(
    *,
    question: str,
    volunteer_id: str,
    volunteer_language: str,
    model_router: ModelRouter,
    log_callback: LogCallback,
) -> AskCrewLinkResult:
    """Main Ask CrewLink handler — Doc #4 §2 branching + Doc #8 §3.3 wrapper.

    Args:
        question: The volunteer's free-text question.
        volunteer_id: The volunteer's UUID (for logging).
        volunteer_language: ISO 639-1 code (e.g. 'en', 'es', 'fr').
        model_router: The system's ModelRouter.
        log_callback: Async callback for invocation logging.

    Returns:
        ``AskCrewLinkResult`` — structured response, never an exception.
    """
    _ = volunteer_id  # kept for future logging use

    # ------------------------------------------------------------------
    # Doc #8 §3.3 step 1–2: Detect source language, translate to English
    # for retrieval if needed.
    # ------------------------------------------------------------------
    query_for_processing = question
    is_multilingual = volunteer_language and volunteer_language != "en"

    if is_multilingual:
        query_for_processing = await _translate_for_retrieval(
            question, volunteer_language, model_router, log_callback,
        )

    # ------------------------------------------------------------------
    # Step 1 of Doc #4 §2: Intent routing (Fast/Cheap)
    # ------------------------------------------------------------------
    router_provider = model_router.for_task(TaskType.INTENT_ROUTING)

    intent_result = await complete_with_fallback(
        provider=router_provider,
        task_type=TaskType.INTENT_ROUTING,
        system_prompt=INTENT_ROUTER_SYSTEM_PROMPT,
        user_text=f"<query>{query_for_processing}</query>",
        schema=IntentClassification,
        log_callback=log_callback,
        timeout_s=2.0,
    )

    # If intent routing fell back, default to FACILITY_SAFETY_PROCEDURE
    # (ambiguity resolves toward caution — Doc #4 governing principle 2).
    if intent_result.fallback_used:
        intent = IntentType.FACILITY_SAFETY_PROCEDURE
    else:
        intent_str = intent_result.data.get("intent", "facility_safety_procedure")
        try:
            intent = IntentType(intent_str)
        except ValueError:
            intent = IntentType.FACILITY_SAFETY_PROCEDURE

    # ------------------------------------------------------------------
    # Steps 2–5 of Doc #4 §2: Branch on intent
    # ------------------------------------------------------------------

    # Four branches that NEVER touch KB retrieval or Reasoning tier:
    if intent == IntentType.TRANSLATION_REQUEST:
        return _TEMPLATED_REPLIES[IntentType.TRANSLATION_REQUEST]

    if intent == IntentType.SMALL_TALK:
        return _TEMPLATED_REPLIES[IntentType.SMALL_TALK]

    if intent == IntentType.STATUS_OR_LOGISTICS:
        return _TEMPLATED_REPLIES[IntentType.STATUS_OR_LOGISTICS]

    if intent == IntentType.OUT_OF_SCOPE:
        return _TEMPLATED_REPLIES[IntentType.OUT_OF_SCOPE]

    # ------------------------------------------------------------------
    # FACILITY_SAFETY_PROCEDURE — the ONLY branch that touches KB
    # or the Reasoning tier.  (Doc #4 §2 code-level guarantee.)
    # ------------------------------------------------------------------
    assert intent == IntentType.FACILITY_SAFETY_PROCEDURE

    # Retrieve from Chroma
    chunks = await retrieve_chunks(query_for_processing, top_k=5)

    # Apply similarity threshold gate (ADDENDUM G8: MIN_GROUNDING_SIMILARITY = 0.75)
    threshold = settings.min_grounding_similarity
    groundable = [c for c in chunks if c["similarity"] >= threshold]

    if not groundable:
        logger.warning(
            "KB empty/below threshold: query=%s  retrieved=%d  threshold=%.2f",
            query_for_processing, len(chunks), threshold,
        )
        no_kb_msg = (
            "I couldn't find an answer in the venue guide. "
            "Please ask your zone supervisor or "
            "check at the information desk."
        )
        return AskCrewLinkResult(
            grounded=False,
            confidence=0.0,
            fallback_message=no_kb_msg,
        )

    # Build context for synthesis
    context_parts = []
    for c in groundable:
        context_parts.append(
            f"[Chunk {c['chunk_id']}] (similarity: {c['similarity']:.2f})\n{c['text']}"
        )
    context_text = "\n\n".join(context_parts)

    # Retrieve chunk IDs for whitelist validation
    retrieved_chunk_ids = {c["chunk_id"] for c in groundable}

    user_text = (
        f"<query>{query_for_processing}</query>\n\n"
        f"<context_chunks>\n{context_text}\n</context_chunks>"
    )

    # Synthesis call (Reasoning tier) — the only Reasoning-tier call in
    # this function, gated behind the ``if not groundable: return`` above.
    synth_provider = model_router.for_task(TaskType.ASK_CREWLINK_SYNTHESIS)
    synth_result = await complete_with_fallback(
        provider=synth_provider,
        task_type=TaskType.ASK_CREWLINK_SYNTHESIS,
        system_prompt=ASK_CREWLINK_SYSTEM_PROMPT,
        user_text=user_text,
        schema=GroundedAnswer,
        log_callback=log_callback,
        timeout_s=8.0,
        validation_context={"sources": retrieved_chunk_ids},
    )

    # ------------------------------------------------------------------
    # Build the response
    # ------------------------------------------------------------------
    answer: str | None = None
    grounded = False
    confidence = 0.0
    fallback_msg: str | None = None
    fallback_used = synth_result.fallback_used
    sources: list[SourceCitation] = []

    if synth_result.fallback_used:
        # Doc #4 §5.3 fallback: raw chunks shown with explanation note.
        fallback_msg = synth_result.data.get(
            "answer",
            "AI summary unavailable — showing matching excerpts.",
        )
        answer = None
        grounded = False
        confidence = 0.0
    else:
        answer = synth_result.data.get("answer")
        grounded = synth_result.data.get("grounded", False)
        confidence = synth_result.data.get("confidence", 0.85)
        if not isinstance(confidence, (int, float)):
            confidence = 0.85

        if grounded:
            cited_ids = set(synth_result.data.get("sources", []))
            sources = [
                SourceCitation(
                    document_id=c["metadata"].get("doc_title", "unknown"),
                    chunk_id=c["chunk_id"],
                    title=c["metadata"].get("section_heading", "unknown"),
                )
                for c in groundable
                if c["chunk_id"] in cited_ids
            ]

    # ------------------------------------------------------------------
    # Doc #8 §3.3 step 6: Translate answer back to volunteer's language
    # ------------------------------------------------------------------
    if is_multilingual and answer:
        answer = await _translate_answer(
            answer, volunteer_language, model_router, log_callback,
        )

    return AskCrewLinkResult(
        answer=answer,
        grounded=grounded,
        confidence=confidence,
        sources=sources,
        fallback_message=fallback_msg,
        fallback_used=fallback_used,
    )


# ---------------------------------------------------------------------------
# Multilingual helpers (Doc #8 §3.3)
# ---------------------------------------------------------------------------


async def _translate_for_retrieval(
    text: str,
    source_language: str,
    model_router: ModelRouter,
    _log_callback: LogCallback,
) -> str:
    """Translate query from *source_language* to English for retrieval.

    Uses a Fast/Cheap call.  Returns original text on failure (translation
    failure should never block the query path).
    """
    if source_language == "en":
        return text

    provider = model_router.for_task(TaskType.TRANSLATION)
    prompt = (
        "Translate the following text to English. "
        "Output ONLY the translated text, nothing else."
    )
    try:
        translated = await provider.complete_text(
            system=prompt,
            user=f"<text>{text}</text>",
            timeout_s=2.0,
        )
        return translated.strip()
    except Exception:
        logger.warning(
            "Translation-to-English failed for lang=%s — using original query",
            source_language,
        )
        return text


async def _translate_answer(
    text: str,
    target_language: str,
    model_router: ModelRouter,
    _log_callback: LogCallback,
) -> str:
    """Translate English answer into *target_language*.

    Uses a Fast/Cheap call.  Returns original English text on failure.
    """
    provider = model_router.for_task(TaskType.TRANSLATION)
    prompt = (
        f"Translate the following text to {target_language}. "
        "Output ONLY the translated text, nothing else."
    )
    try:
        translated = await provider.complete_text(
            system=prompt,
            user=f"<text>{text}</text>",
            timeout_s=2.0,
        )
        return translated.strip()
    except Exception:
        logger.warning(
            "Translation-from-English failed for lang=%s — using original answer",
            target_language,
        )
        return text
