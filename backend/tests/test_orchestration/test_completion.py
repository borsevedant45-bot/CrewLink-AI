"""Tests for the orchestration completion pipeline.

4 test categories covering all 6 TaskTypes:

1. **Timeout** — provider raises ``asyncio.TimeoutError`` → fallback
2. **Schema-invalid** — provider returns data that fails ``model_validate`` → fallback
3. **Hallucinated ID** — provider returns valid schema with unknown ``volunteer_id``
   or ``chunk_id`` → fallback
4. **Log completeness** — every call (success or failure) produces exactly one row in
   the ``AIInvocationLog`` callback.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from backend.orchestration.completion import complete_with_fallback
from backend.orchestration.interfaces import LLMProvider, TaskType
from backend.orchestration.logging_ import InvocationRecord
from backend.orchestration.schemas import (
    DispatchRecommendation,
    GroundedAnswer,
    IncidentClassification,
    IntentClassification,
    ShiftSummary,
    TranslationResult,
)
from tests.test_orchestration.stub_provider import StubProvider

# ===========================================================================
# Shared helpers
# ===========================================================================

TASK_SCHEMA_MAP: dict[TaskType, type[BaseModel]] = {
    TaskType.INCIDENT_CLASSIFICATION: IncidentClassification,
    TaskType.INTENT_ROUTING: IntentClassification,
    TaskType.TRANSLATION: TranslationResult,
    TaskType.DISPATCH_RECOMMENDATION: DispatchRecommendation,
    TaskType.ASK_CREWLINK_SYNTHESIS: GroundedAnswer,
    TaskType.SHIFT_SUMMARY: ShiftSummary,
}

VALID_RESULTS: dict[TaskType, dict[str, Any]] = {
    TaskType.INCIDENT_CLASSIFICATION: {
        "category": "medical",
        "severity_signal": "medium",
        "requires_emergency_escalation": False,
        "confidence": 0.85,
        "reasoning_summary": "Test classification",
    },
    TaskType.INTENT_ROUTING: {
        "intent": "facility_safety_procedure",
        "confidence": 0.90,
    },
    TaskType.TRANSLATION: {
        "translated_text": "Hola mundo",
        "detected_language": "es",
        "confidence": 0.95,
        "emergency_flag": False,
    },
    TaskType.DISPATCH_RECOMMENDATION: {
        "recommended_volunteers": [
            {
                "volunteer_id": "vol_known",
                "rank": 1,
                "rationale": "Nearest available",
            },
        ],
        "requires_human_supervisor_review": False,
        "confidence": 0.75,
    },
    TaskType.ASK_CREWLINK_SYNTHESIS: {
        "answer": "The south gate is open until 22:00.",
        "grounded": True,
        "sources": ["chunk_gate_hours_001"],
    },
    TaskType.SHIFT_SUMMARY: {
        "summary": "No issues during this shift.",
        "incident_count": 0,
        "notable_events": [],
    },
}

INVALID_RESULTS: dict[TaskType, dict[str, Any]] = {
    TaskType.INCIDENT_CLASSIFICATION: {"severity_signal": "bogus"},
    TaskType.INTENT_ROUTING: {"intent": "not_a_real_intent", "confidence": -1.0},
    TaskType.TRANSLATION: {"translated_text": ""},
    TaskType.DISPATCH_RECOMMENDATION: {"confidence": 99.9},
    TaskType.ASK_CREWLINK_SYNTHESIS: {"answer": "", "sources": {}},
    TaskType.SHIFT_SUMMARY: {},
}

ALL_TASK_TYPES = list(TaskType)


# ===========================================================================
# 1. Timeout tests
# ===========================================================================


class TestTimeout:
    """Provider timeout → deterministic fallback, never an exception."""

    pytestmark = pytest.mark.anyio

    @pytest.mark.parametrize("task_type", ALL_TASK_TYPES)
    async def test_timeout_routes_to_fallback(
        self,
        task_type: TaskType,
        log_callback: Any,
    ) -> None:
        provider: LLMProvider = StubProvider(error=TimeoutError())

        result = await complete_with_fallback(
            provider=provider,
            task_type=task_type,
            system_prompt="test",
            user_text="test",
            schema=TASK_SCHEMA_MAP[task_type],
            log_callback=log_callback,
            timeout_s=1.0,
        )

        assert result.fallback_used, f"{task_type.value}: should have used fallback"
        assert result.fallback_name is not None
        assert result.error_reason == "provider_timeout"



# ===========================================================================
# 2. Schema-invalid tests
# ===========================================================================


class TestSchemaInvalid:
    """Provider returns data that fails model_validate → fallback."""

    pytestmark = pytest.mark.anyio

    @pytest.mark.parametrize("task_type", ALL_TASK_TYPES)
    async def test_invalid_schema_routes_to_fallback(
        self,
        task_type: TaskType,
        log_callback: Any,
    ) -> None:
        provider: LLMProvider = StubProvider(result=INVALID_RESULTS[task_type])

        result = await complete_with_fallback(
            provider=provider,
            task_type=task_type,
            system_prompt="test",
            user_text="test",
            schema=TASK_SCHEMA_MAP[task_type],
            log_callback=log_callback,
            timeout_s=5.0,
        )

        assert result.fallback_used, f"{task_type.value}: invalid data should trigger fallback"
        assert result.error_reason is not None
        assert "validation" in result.error_reason.lower(), (
            f"{task_type.value}: reason should mention validation, got {result.error_reason}"
        )

    @pytest.mark.parametrize("task_type", ALL_TASK_TYPES)
    async def test_fallback_badged_with_fallback_used(
        self,
        task_type: TaskType,
        log_callback: Any,
    ) -> None:
        """Data returned by fallback in validation-failure case must carry the
        fallback indicator in the result envelope."""
        provider: LLMProvider = StubProvider(result=INVALID_RESULTS[task_type])

        result = await complete_with_fallback(
            provider=provider,
            task_type=task_type,
            system_prompt="test",
            user_text="test",
            schema=TASK_SCHEMA_MAP[task_type],
            log_callback=log_callback,
            timeout_s=5.0,
        )

        assert result.fallback_used
        assert isinstance(result.data, dict)


# ===========================================================================
# 3. Hallucinated-ID tests
# ===========================================================================


class TestHallucinatedID:
    """Provider returns valid schema but with ID values not in the allowed set.

    Only TaskTypes that carry ID fields are tested here:
    - DISPATCH_RECOMMENDATION -> volunteer_id in DispatchCandidate
    - ASK_CREWLINK_SYNTHESIS -> sources (chunk IDs)
    """

    pytestmark = pytest.mark.anyio

    async def test_dispatch_hallucinated_volunteer(
        self,
        log_callback: Any,
    ) -> None:
        valid_result = {
            "recommended_volunteers": [
                {
                    "volunteer_id": "vol_nonexistent",
                    "rank": 1,
                    "rationale": "Nearest available",
                },
            ],
            "requires_human_supervisor_review": False,
            "confidence": 0.75,
        }
        provider: LLMProvider = StubProvider(result=valid_result)

        result = await complete_with_fallback(
            provider=provider,
            task_type=TaskType.DISPATCH_RECOMMENDATION,
            system_prompt="test",
            user_text="test",
            schema=DispatchRecommendation,
            log_callback=log_callback,
            timeout_s=5.0,
            validation_context={"volunteer_id": {"vol_known", "vol_other"}},
        )

        assert result.fallback_used, "Hallucinated volunteer_id should trigger fallback"
        assert "hallucinated" in (result.error_reason or "").lower(), (
            f"reason should mention hallucinated vol, got {result.error_reason}"
        )

    async def test_ask_crewlink_hallucinated_chunk(
        self,
        log_callback: Any,
    ) -> None:
        valid_result = {
            "answer": "The gate is open.",
            "grounded": True,
            "sources": ["chunk_nonexistent"],
        }
        provider: LLMProvider = StubProvider(result=valid_result)

        result = await complete_with_fallback(
            provider=provider,
            task_type=TaskType.ASK_CREWLINK_SYNTHESIS,
            system_prompt="test",
            user_text="test",
            schema=GroundedAnswer,
            log_callback=log_callback,
            timeout_s=5.0,
            validation_context={"sources": {"chunk_gate_hours_001"}},
        )

        assert result.fallback_used, "Hallucinated chunk_id should trigger fallback"

    async def test_valid_ids_pass_through(
        self,
        log_callback: Any,
    ) -> None:
        valid_result = {
            "recommended_volunteers": [
                {
                    "volunteer_id": "vol_known",
                    "rank": 1,
                    "rationale": "Nearest available",
                },
            ],
            "requires_human_supervisor_review": False,
            "confidence": 0.75,
        }
        provider: LLMProvider = StubProvider(result=valid_result)

        result = await complete_with_fallback(
            provider=provider,
            task_type=TaskType.DISPATCH_RECOMMENDATION,
            system_prompt="test",
            user_text="test",
            schema=DispatchRecommendation,
            log_callback=log_callback,
            timeout_s=5.0,
            validation_context={"volunteer_id": {"vol_known", "vol_other"}},
        )

        assert not result.fallback_used, "Valid volunteer_id should not trigger fallback"


# ===========================================================================
# 4. Log completeness tests
# ===========================================================================


class TestLogCompleteness:
    """Every call to complete_with_fallback produces exactly one log row.

    Tests cover: success path, timeout path, schema-invalid path,
    and a mixed batch across all TaskTypes.
    """

    pytestmark = pytest.mark.anyio

    async def test_success_produces_one_log_row(
        self,
        log_spy: list[InvocationRecord],
        log_callback: Any,
    ) -> None:
        provider: LLMProvider = StubProvider(result=VALID_RESULTS[TaskType.INCIDENT_CLASSIFICATION])

        await complete_with_fallback(
            provider=provider,
            task_type=TaskType.INCIDENT_CLASSIFICATION,
            system_prompt="test",
            user_text="Classify this incident",
            schema=IncidentClassification,
            log_callback=log_callback,
            timeout_s=5.0,
        )

        assert len(log_spy) == 1, "Success should produce exactly 1 log row"
        record = log_spy[0]
        assert record.fallback_used is False
        assert record.purpose == "incident_classification"
        assert record.tier_used == "fast_cheap"

    async def test_timeout_produces_one_log_row(
        self,
        log_spy: list[InvocationRecord],
        log_callback: Any,
    ) -> None:
        provider: LLMProvider = StubProvider(error=TimeoutError())

        await complete_with_fallback(
            provider=provider,
            task_type=TaskType.INTENT_ROUTING,
            system_prompt="test",
            user_text="Route this query",
            schema=IntentClassification,
            log_callback=log_callback,
            timeout_s=1.0,
        )

        assert len(log_spy) == 1, "Timeout should produce exactly 1 log row"
        record = log_spy[0]
        assert record.fallback_used is True
        assert record.purpose == "intent_routing"

    async def test_schema_invalid_produces_one_log_row(
        self,
        log_spy: list[InvocationRecord],
        log_callback: Any,
    ) -> None:
        provider: LLMProvider = StubProvider(result=INVALID_RESULTS[TaskType.TRANSLATION])

        await complete_with_fallback(
            provider=provider,
            task_type=TaskType.TRANSLATION,
            system_prompt="test",
            user_text="Translate this",
            schema=TranslationResult,
            log_callback=log_callback,
            timeout_s=5.0,
        )

        assert len(log_spy) == 1, "Schema-invalid should produce exactly 1 log row"
        record = log_spy[0]
        assert record.fallback_used is True

    async def test_hallucinated_id_produces_one_log_row(
        self,
        log_spy: list[InvocationRecord],
        log_callback: Any,
    ) -> None:
        valid_result = {
            "recommended_volunteers": [
                {
                    "volunteer_id": "vol_fake",
                    "rank": 1,
                    "rationale": "Nearest",
                },
            ],
            "requires_human_supervisor_review": False,
            "confidence": 0.75,
        }
        provider: LLMProvider = StubProvider(result=valid_result)

        await complete_with_fallback(
            provider=provider,
            task_type=TaskType.DISPATCH_RECOMMENDATION,
            system_prompt="test",
            user_text="Dispatch to incident-1",
            schema=DispatchRecommendation,
            log_callback=log_callback,
            timeout_s=5.0,
            validation_context={"volunteer_id": {"vol_known"}},
        )

        assert len(log_spy) == 1, "Hallucinated ID should produce exactly 1 log row"
        assert log_spy[0].fallback_used is True

    async def test_log_row_count_equals_call_count(
        self,
        log_spy: list[InvocationRecord],
        log_callback: Any,
    ) -> None:
        """Mixed batch: 6 calls across all TaskTypes -> exactly 6 rows."""
        for i, task_type in enumerate(ALL_TASK_TYPES):
            if i % 2 == 0:
                provider: LLMProvider = StubProvider(result=VALID_RESULTS[task_type])
            else:
                provider = StubProvider(error=TimeoutError())

            await complete_with_fallback(
                provider=provider,
                task_type=task_type,
                system_prompt="test",
                user_text=f"Call {i}",
                schema=TASK_SCHEMA_MAP[task_type],
                log_callback=log_callback,
                timeout_s=1.0,
            )

        assert len(log_spy) == 6, f"Expected 6 log rows, got {len(log_spy)}"
        for i, record in enumerate(log_spy):
            if i % 2 == 0:
                assert record.fallback_used is False, f"Row {i} should be success"
            else:
                assert record.fallback_used is True, f"Row {i} should be fallback"


# ===========================================================================
# 5. Fallback data quality (cross-section)
# ===========================================================================


class TestFallbackDataQuality:
    """Spot-check that fallback outputs are sensible for their task type."""

    pytestmark = pytest.mark.anyio

    @pytest.mark.parametrize("task_type", ALL_TASK_TYPES)
    async def test_fallback_returns_dict_with_expected_fields(
        self,
        task_type: TaskType,
        log_callback: Any,
    ) -> None:
        provider: LLMProvider = StubProvider(error=TimeoutError())

        result = await complete_with_fallback(
            provider=provider,
            task_type=task_type,
            system_prompt="test",
            user_text="test",
            schema=TASK_SCHEMA_MAP[task_type],
            log_callback=log_callback,
            timeout_s=1.0,
        )

        assert result.fallback_used
        assert result.fallback_name is not None
        assert isinstance(result.data, dict)
        assert len(result.data) > 0
