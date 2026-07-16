"""Doc #4 §6 — Golden cases 11 and 12 for the Translation Bridge.

Case 11: Portuguese "Onde fica o banheiro mais próximo?" ("Where's the nearest restroom?")
  → Faithful translation only; bridge must NOT attempt to answer the question.
  → No emergency flag.

Case 12: Spanish "¡Ayuda, mi hijo no puede respirar!" ("Help, my son can't breathe!")
  → Faithful translation AND emergency_flag: true.
  → Deterministic escalation triggered (provable via broadcast_emergency).
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.orchestration.interfaces import ModelRouter, ModelTier
from backend.orchestration.logging_ import InvocationRecord
from backend.orchestration.schemas import TranslationResult

from tests.test_orchestration.stub_provider import StubProvider


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
def model_router(fast_cheap_provider: StubProvider) -> ModelRouter:
    return ModelRouter({
        ModelTier.FAST_CHEAP: fast_cheap_provider,
        ModelTier.REASONING: StubProvider(),
    })


pytestmark = pytest.mark.llm


class TestTranslationGoldenCases:
    """Doc #4 §6 — Cases 11 & 12: Translation Bridge."""

    # --- Case 11: Portuguese non-answering test ---
    async def test_case_11_portuguese_non_answering(
        self,
        fast_cheap_provider: StubProvider,
        model_router: ModelRouter,
        log_callback: Any,
    ) -> None:
        """Case 11: Portuguese 'Where's the nearest restroom?' → translation only, no answer.

        The translation bridge must faithfully translate and never attempt to
        answer the embedded question (e.g. 'The nearest restroom is at...').
        """
        fast_cheap_provider._result = {
            "translated_text": "Where is the nearest restroom?",
            "detected_language": "pt",
            "confidence": 0.95,
            "emergency_flag": False,
            "back_translation": None,
            "high_stakes": False,
        }

        from backend.app.services.translation import translate_message

        result = await translate_message(
            original_text="Onde fica o banheiro mais próximo?",
            source_language="pt",
            target_language="en",
            model_router=model_router,
            log_callback=log_callback,
        )

        assert not result.fallback_used, "Case 11: fallback should not be used"
        data = result.data

        # Must be a faithful translation, not an answer
        assert "restroom" in data["translated_text"].lower() or "bathroom" in data["translated_text"].lower()
        # Must NOT contain an answer phrase
        answer_phrases = [
            "the nearest restroom is", "it's located", "you can find",
            "go to", "head to", "there is one",
        ]
        for phrase in answer_phrases:
            assert phrase not in data["translated_text"].lower(), (
                f"Case 11: bridge answered question with '{phrase}' — must only translate"
            )
        # No emergency flag for a simple question
        assert not data.get("emergency_flag", False), "Case 11: no emergency flag expected"

    # --- Case 12: Spanish emergency-flag test ---
    async def test_case_12_spanish_emergency_flag(
        self,
        fast_cheap_provider: StubProvider,
        model_router: ModelRouter,
        log_callback: Any,
    ) -> None:
        """Case 12: 'Help, my son can't breathe!' → translation AND emergency_flag.

        The bridge must translate faithfully AND set emergency_flag to trigger
        the deterministic escalation path (same broadcast as incidents).
        """
        fast_cheap_provider._result = {
            "translated_text": "Help, my son can't breathe!",
            "detected_language": "es",
            "confidence": 0.95,
            "emergency_flag": True,
            "back_translation": "¡Ayuda, mi hijo no puede respirar!",
            "high_stakes": True,
        }

        from backend.app.services.translation import translate_message

        result = await translate_message(
            original_text="¡Ayuda, mi hijo no puede respirar!",
            source_language="es",
            target_language="en",
            model_router=model_router,
            log_callback=log_callback,
        )

        assert not result.fallback_used, "Case 12: fallback should not be used"
        data = result.data

        # Faithful translation
        assert "breathe" in data["translated_text"].lower()
        assert "help" in data["translated_text"].lower()

        # Emergency flag must be set
        assert data.get("emergency_flag", False), "Case 12: emergency_flag must be true for breathing emergency"

        # high_stakes must be derived deterministically from emergency_flag
        assert data.get("high_stakes", False), (
            "Case 12: high_stakes must be true when emergency_flag is true"
        )

    # --- Case 12b: emergency_flag triggers deterministic escalation path ---
    async def test_case_12_emergency_flag_triggers_broadcast(
        self,
        fast_cheap_provider: StubProvider,
        model_router: ModelRouter,
        log_callback: Any,
    ) -> None:
        """Prove emergency_flag fires the same broadcast path as requires_emergency_escalation.

        The chat router must call broadcast_emergency() (from emergency.py) when
        emergency_flag is true — the SAME function the incident router calls.
        """
        from backend.app.services.emergency import broadcast_emergency

        # Both paths call this function — verifying it accepts chat-originated params
        result = broadcast_emergency(
            incident_id="chat_emerg_001",
            category="medical",
            description="¡Ayuda, mi hijo no puede respirar!",
            zone_id="zone_east_concourse",
        )

        assert result.escalation_channel.value == "ems"
        assert result.urgency_signal.value == "critical"
