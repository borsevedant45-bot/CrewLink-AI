"""Doc #4 §6 — Golden cases 13, 14, 15 for Ask CrewLink.

Case 13: "Where is the nearest accessible restroom to the East Concourse?"
  → FACILITY_SAFETY_PROCEDURE → retrieval above threshold → synthesis
  → grounded: true, answer cites Accessibility Guide chunk(s)

Case 14: "What's the score of the match happening right now?"
  → OUT_OF_SCOPE → polite deflection
  → grounded: false, fallback_message populated

Case 15: "Someone near section 114 just collapsed, what do I do?"
  → FACILITY_SAFETY_PROCEDURE → retrieval above threshold → synthesis
  → LIVE EMERGENCY OVERRIDE: response leads with Report Incident / EMS,
    does NOT answer from the KB in that turn
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.orchestration.interfaces import ModelRouter, ModelTier
from backend.orchestration.logging_ import InvocationRecord
from tests.test_orchestration.stub_provider import StubProvider

pytestmark = [pytest.mark.usefixtures("mock_retrieval_patch"), pytest.mark.llm]

# ======================================================================
# Shared fixtures
# ======================================================================


@pytest.fixture
def log_spy() -> list[InvocationRecord]:
    return []


@pytest.fixture
def log_callback(log_spy: list[InvocationRecord]) -> Any:
    async def _cb(record: InvocationRecord) -> None:
        log_spy.append(record)
    return _cb


@pytest.fixture
def fast_cheap_provider() -> StubProvider:
    return StubProvider()


@pytest.fixture
def reasoning_provider() -> StubProvider:
    return StubProvider()


@pytest.fixture
def model_router(
    fast_cheap_provider: StubProvider,
    reasoning_provider: StubProvider,
) -> ModelRouter:
    return ModelRouter({
        ModelTier.FAST_CHEAP: fast_cheap_provider,
        ModelTier.REASONING: reasoning_provider,
    })


# ======================================================================
# Golden cases
# ======================================================================


class TestAskCrewLinkGoldenCases:
    """Doc #4 §6 — Cases 13-15: Ask CrewLink."""

    @pytest.mark.asyncio
    async def test_case_13_in_kb_grounded(
        self,
        fast_cheap_provider: StubProvider,
        reasoning_provider: StubProvider,
        model_router: ModelRouter,
        log_callback: Any,
    ) -> None:
        """Case 13: 'Where is the nearest accessible restroom to the East Concourse?'

        FACILITY_SAFETY_PROCEDURE → retrieval above threshold → synthesis.
        Expect grounded=true with source citations.
        """
        # Arrange: intent router returns facility_safety_procedure
        fast_cheap_provider._result = {
            "intent": "facility_safety_procedure",
            "confidence": 0.95,
            "detected_language": "en",
        }

        # Arrange: synthesis returns a grounded answer citing a chunk
        reasoning_provider._result = {
            "answer": (
                "The nearest accessible restroom to the East Concourse is "
                "located adjacent to the standard restrooms on the East Concourse, "
                "near Guest Services Desk East. Wheelchair-accessible restrooms are "
                "available on every concourse."
            ),
            "grounded": True,
            "sources": ["def456_accessibility_restrooms"],
        }

        from backend.app.services.ask_crewlink import handle_ask_crewlink

        # Act
        result = await handle_ask_crewlink(
            question="Where is the nearest accessible restroom to the East Concourse?",
            volunteer_id="vol_maria_alvarez",
            volunteer_language="en",
            model_router=model_router,
            log_callback=log_callback,
        )

        # Assert: grounded with answer and sources
        assert result.grounded, "Case 13: should be grounded"
        assert result.answer is not None, "Case 13: answer should not be None"
        assert "restroom" in result.answer.lower(), (
            "Case 13: answer should mention restroom"
        )
        assert len(result.sources) > 0, "Case 13: should have at least one source"
        # Assert source has expected structure (document_id, chunk_id, title)
        first_source = result.sources[0]
        assert "chunk_id" in first_source.model_dump(), (
            "Case 13: source should have chunk_id"
        )
        assert "document_id" in first_source.model_dump(), (
            "Case 13: source should have document_id"
        )
        assert not result.fallback_used, "Case 13: fallback should not be used"

    @pytest.mark.asyncio
    async def test_case_14_out_of_kb_refusal(
        self,
        fast_cheap_provider: StubProvider,
        model_router: ModelRouter,
        log_callback: Any,
    ) -> None:
        """Case 14: 'What's the score of the match happening right now?'

        OUT_OF_SCOPE → polite deflection with grounded=false and fallback_message.
        """
        # Arrange: intent router returns out_of_scope
        fast_cheap_provider._result = {
            "intent": "out_of_scope",
            "confidence": 0.85,
            "detected_language": "en",
        }

        from backend.app.services.ask_crewlink import handle_ask_crewlink

        # Act
        result = await handle_ask_crewlink(
            question="What's the score of the match happening right now?",
            volunteer_id="vol_maria_alvarez",
            volunteer_language="en",
            model_router=model_router,
            log_callback=log_callback,
        )

        # Assert: not grounded, no fabricated score
        assert not result.grounded, "Case 14: should not be grounded"
        assert result.answer is None, "Case 14: answer should be null for out-of-scope"
        assert result.fallback_message is not None, (
            "Case 14: fallback_message should be populated"
        )
        # Must NOT contain a fabricated score
        assert "score" not in (result.fallback_message or "").lower(), (
            "Case 14: must not fabricate a score"
        )
        assert not result.fallback_used, "Case 14: no AI call was made, so no fallback"

    @pytest.mark.asyncio
    async def test_case_15_live_emergency_override(
        self,
        fast_cheap_provider: StubProvider,
        reasoning_provider: StubProvider,
        model_router: ModelRouter,
        log_callback: Any,
    ) -> None:
        """Case 15: 'Someone near section 114 just collapsed, what do I do?'

        FACILITY_SAFETY_PROCEDURE → retrieval above threshold → synthesis.
        LIVE EMERGENCY OVERRIDE in the prompt must cause the model to lead with
        'Report this incident' / EMS instruction, NOT answer from KB.
        """
        # Arrange: intent router returns facility_safety_procedure
        fast_cheap_provider._result = {
            "intent": "facility_safety_procedure",
            "confidence": 0.95,
            "detected_language": "en",
        }

        # The stub simulates the model correctly following the LIVE EMERGENCY
        # OVERRIDE: the answer leads with "Report this incident" / EMS instruction
        # instead of answering from the KB.
        reasoning_provider._result = {
            "answer": (
                "REPORT THIS INCIDENT IMMEDIATELY: Someone near Section 114 has collapsed. "
                "Use CrewLink's Report Incident feature right now to alert medical personnel. "
                "If you see a staff phone, dial *MED and give your location (Section 114). "
                "Do not move the person unless they are in immediate danger."
            ),
            "grounded": True,
            "sources": [],
        }

        from backend.app.services.ask_crewlink import handle_ask_crewlink

        # Act
        result = await handle_ask_crewlink(
            question="Someone near section 114 just collapsed, what do I do?",
            volunteer_id="vol_maria_alvarez",
            volunteer_language="en",
            model_router=model_router,
            log_callback=log_callback,
        )

        # Assert: answer leads with emergency instruction
        assert result.grounded, "Case 15: grounded should be true (model says it is)"
        assert result.answer is not None, "Case 15: answer should not be None"
        answer_lower = result.answer.lower()
        # Must contain emergency-related language
        assert any(
            word in answer_lower
            for word in ["report", "ems", "medical", "dial", "incident"]
        ), (
            "Case 15: answer must lead with emergency instruction, "
            f"got: {result.answer[:200]}"
        )
        assert not result.fallback_used, (
            "Case 15: fallback should not be used"
        )

    # ------------------------------------------------------------------
    # Structural: verify the LIVE EMERGENCY OVERRIDE exists in the prompt
    # ------------------------------------------------------------------

    def test_live_emergency_override_in_prompt(self) -> None:
        """Assert that the Ask CrewLink system prompt contains LIVE EMERGENCY OVERRIDE.

        This is a structural guarantee — the prompt text must contain the override
        section (Doc #4 §3(d)) so the Reasoning-tier model checks for live emergencies
        before answering from the KB.
        """
        from backend.app.services.prompts import ASK_CREWLINK_SYSTEM_PROMPT

        assert "LIVE EMERGENCY OVERRIDE" in ASK_CREWLINK_SYSTEM_PROMPT, (
            "ASK_CREWLINK_SYSTEM_PROMPT must contain LIVE EMERGENCY OVERRIDE section"
        )
        assert "Before answering anything from the knowledge base" in ASK_CREWLINK_SYSTEM_PROMPT, (
            "LIVE EMERGENCY OVERRIDE must instruct model to check before answering from KB"
        )
        assert "Report Incident" in ASK_CREWLINK_SYSTEM_PROMPT, (
            "LIVE EMERGENCY OVERRIDE must reference the Report Incident feature"
        )
