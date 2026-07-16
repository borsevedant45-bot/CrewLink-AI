"""Structural test: Prove the Reasoning tier is called exactly zero times
across the four non-FACILITY_SAFETY_PROCEDURE branches.

Uses a CallCountingStub for the Reasoning tier — if it's ever called,
the test fails.  The Fast/Cheap provider (intent router) returns each of
the four non-facility intents, and the service must handle them without
touching the Reasoning tier.

Doc #4 §2 code-level guarantee (paraphrased):
  "the retrieval call is syntactically unreachable from any branch
   except FACILITY_SAFETY_PROCEDURE, and even there the Reasoning-tier
   call sits behind an 'if not grounded: return'."

Additionally tests that FACILITY_SAFETY_PROCEDURE with BELOW-threshold
retrieval also makes zero Reasoning-tier calls.
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.orchestration.interfaces import ModelRouter, ModelTier
from backend.orchestration.logging_ import InvocationRecord
from tests.test_orchestration.stub_provider import StubProvider

# ======================================================================
# Call-counting stub — raises if called
# ======================================================================


class CallCountingStub(StubProvider):
    """Stub that counts calls and raises on any attempt."""

    def __init__(self) -> None:
        super().__init__()
        self.call_count = 0

    async def complete_structured(
        self,
        *,
        system: str,  # noqa: ARG002
        user: str,  # noqa: ARG002
        schema: type[Any],  # noqa: ARG002
        timeout_s: float,  # noqa: ARG002
    ) -> Any:
        self.call_count += 1
        msg = "Reasoning tier should NOT be called for non-FACILITY branches"
        raise RuntimeError(msg)

    async def complete_text(
        self,
        *,
        system: str,  # noqa: ARG002
        user: str,  # noqa: ARG002
        timeout_s: float,  # noqa: ARG002
    ) -> str:
        self.call_count += 1
        msg = "Reasoning tier should NOT be called for non-FACILITY branches"
        raise RuntimeError(msg)


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
def reasoning_counter() -> CallCountingStub:
    return CallCountingStub()


@pytest.fixture
def model_router(
    fast_cheap_provider: StubProvider,
    reasoning_counter: CallCountingStub,
) -> ModelRouter:
    return ModelRouter({
        ModelTier.FAST_CHEAP: fast_cheap_provider,
        ModelTier.REASONING: reasoning_counter,
    })


# ======================================================================
# Tests
# ======================================================================


class TestNoReasoningOnNonFacility:
    """Prove Reasoning tier is never invoked for non-FACILITY branches."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("intent,query", [
        (
            "translation_request",
            "Can you translate this for me: donde esta el bano?",
        ),
        (
            "small_talk",
            "Hello! How are you today?",
        ),
        (
            "status_or_logistics",
            "What is my current assignment?",
        ),
        (
            "out_of_scope",
            "Who won the 2022 World Cup?",
        ),
    ])
    async def test_reasoning_not_called_for_non_facility(
        self,
        intent: str,
        query: str,
        fast_cheap_provider: StubProvider,
        reasoning_counter: CallCountingStub,
        model_router: ModelRouter,
        log_callback: Any,
    ) -> None:
        """Each non-FACILITY branch must NOT call the Reasoning tier."""
        fast_cheap_provider._result = {
            "intent": intent,
            "confidence": 0.90,
            "detected_language": "en",
        }

        from backend.app.services.ask_crewlink import handle_ask_crewlink

        result = await handle_ask_crewlink(
            question=query,
            volunteer_id="vol_maria_alvarez",
            volunteer_language="en",
            model_router=model_router,
            log_callback=log_callback,
        )

        assert reasoning_counter.call_count == 0, (
            f"Reasoning tier was called {reasoning_counter.call_count} times "
            f"for intent={intent}"
        )
        # For these branches, the result should never be grounded
        assert not result.grounded, (
            f"Result should not be grounded for intent={intent}"
        )

    @pytest.mark.asyncio
    async def test_facility_below_threshold_no_reasoning(
        self,
        fast_cheap_provider: StubProvider,
        reasoning_counter: CallCountingStub,
        model_router: ModelRouter,
        log_callback: Any,
    ) -> None:
        """FACILITY_SAFETY_PROCEDURE with retrieval below threshold must NOT call Reasoning.

        Even though this is the FACILITY branch, the 'if not grounded: return' gate
        must fire before the synthesis call is reached.
        """
        fast_cheap_provider._result = {
            "intent": "facility_safety_procedure",
            "confidence": 0.95,
            "detected_language": "en",
        }

        # Patch retrieval to return chunks BELOW the threshold
        from unittest.mock import AsyncMock, patch

        below_threshold_chunks = [
            {
                "chunk_id": "low_sim_chunk",
                "text": "Some marginally relevant text.",
                "metadata": {
                    "doc_title": "Test Doc",
                    "doc_type": "VENUE_MAP",
                    "section_heading": "Test",
                    "token_count": "5",
                },
                "similarity": 0.30,  # well below 0.75
            },
        ]

        with patch(
            "backend.app.services.ask_crewlink.retrieve_chunks",
            AsyncMock(return_value=below_threshold_chunks),
        ):
            from backend.app.services.ask_crewlink import handle_ask_crewlink

            result = await handle_ask_crewlink(
                question="Where is Gate 4?",
                volunteer_id="vol_maria_alvarez",
                volunteer_language="en",
                model_router=model_router,
                log_callback=log_callback,
            )

        assert reasoning_counter.call_count == 0, (
            f"Reasoning tier called {reasoning_counter.call_count} times — "
            "should be 0 when retrieval is below threshold"
        )
        assert not result.grounded, "Below-threshold result must not be grounded"
        assert result.answer is None, (
            "Below-threshold result must not have an answer"
        )
        assert result.fallback_message is not None, (
            "Below-threshold result should have fallback_message"
        )
