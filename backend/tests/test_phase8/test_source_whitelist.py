"""Source-citation whitelist test for Ask CrewLink.

Doc #4 §5.2 bullet 2: "a chunk ID Ask CrewLink cites is checked against
the chunks that were actually retrieved for that request."

This test forces the model (via the stub provider) to cite a chunk ID
that was NEVER retrieved for that request, and asserts it is rejected
and routed to fallback — not surfaced to the UI.

Additionally proves that a chunk ID that *was* retrieved is accepted.
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.orchestration.interfaces import ModelRouter, ModelTier
from backend.orchestration.logging_ import InvocationRecord
from tests.test_orchestration.stub_provider import StubProvider

pytestmark = pytest.mark.usefixtures("mock_retrieval_patch")

# ======================================================================
# Fixtures
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
# Tests
# ======================================================================


class TestSourceWhitelist:
    """Doc #4 §5.2 — chunk ID whitelist enforcement."""

    @pytest.mark.asyncio
    async def test_hallucinated_chunk_id_rejected(
        self,
        fast_cheap_provider: StubProvider,
        reasoning_provider: StubProvider,
        model_router: ModelRouter,
        log_callback: Any,
    ) -> None:
        """Model cites a chunk ID NOT in the retrieved set → must be rejected.

        The test configures retrieval to return chunks with IDs
        ['abc123_chunk_east_concourse', 'def456_accessibility_restrooms'].
        The stub provider returns a GroundedAnswer citing 'hallucinated_chunk_999'
        which is NOT in the retrieved set.
        → complete_with_fallback's validation_context must reject it
        → fallback is used.
        """
        # Arrange: intent router returns facility_safety_procedure
        fast_cheap_provider._result = {
            "intent": "facility_safety_procedure",
            "confidence": 0.95,
            "detected_language": "en",
        }

        # The model cites a chunk ID that was never retrieved
        reasoning_provider._result = {
            "answer": (
                "The nearest accessible restroom is at the East Concourse "
                "near Guest Services Desk East."
            ),
            "grounded": True,
            "sources": ["hallucinated_chunk_999"],  # NOT in retrieved set
        }

        from backend.app.services.ask_crewlink import handle_ask_crewlink

        # Act
        result = await handle_ask_crewlink(
            question="Where is the nearest accessible restroom?",
            volunteer_id="vol_maria_alvarez",
            volunteer_language="en",
            model_router=model_router,
            log_callback=log_callback,
        )

        # Assert: hallucinated ID forced fallback
        assert result.fallback_used, (
            "Hallucinated chunk ID should force fallback"
        )
        # The fallback sets grounded=false
        assert not result.grounded, (
            "Result must not be grounded after whitelist rejection"
        )

    @pytest.mark.asyncio
    async def test_legitimate_chunk_id_accepted(
        self,
        fast_cheap_provider: StubProvider,
        reasoning_provider: StubProvider,
        model_router: ModelRouter,
        log_callback: Any,
    ) -> None:
        """Model cites only chunk IDs from the retrieved set → accepted normally."""
        # Arrange: intent router returns facility_safety_procedure
        fast_cheap_provider._result = {
            "intent": "facility_safety_procedure",
            "confidence": 0.95,
            "detected_language": "en",
        }

        # The model cites a chunk that IS in the retrieved set
        reasoning_provider._result = {
            "answer": (
                "The East Concourse has accessible restrooms near "
                "Guest Services Desk East."
            ),
            "grounded": True,
            "sources": ["def456_accessibility_restrooms"],  # in retrieved set
        }

        from backend.app.services.ask_crewlink import handle_ask_crewlink

        # Act
        result = await handle_ask_crewlink(
            question="Where is the nearest accessible restroom?",
            volunteer_id="vol_maria_alvarez",
            volunteer_language="en",
            model_router=model_router,
            log_callback=log_callback,
        )

        # Assert: legitimate chunk accepted without fallback
        assert not result.fallback_used, (
            "Legitimate chunk IDs should not trigger fallback"
        )
        assert result.grounded, "Result should be grounded"
        assert result.answer is not None, "Answer should be provided"
        assert len(result.sources) > 0, "Should have source citations"
        # Verify the cited chunk_id appears in sources
        source_ids = {s.chunk_id for s in result.sources}
        assert "def456_accessibility_restrooms" in source_ids, (
            "The cited chunk should appear in sources"
        )
