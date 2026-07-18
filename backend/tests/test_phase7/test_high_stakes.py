"""Doc #8 §4.1 — Deterministic high_stakes derivation test.

Proves that ``high_stakes`` is ALWAYS computed from the deterministic rule:
  ``emergency_flag OR category in {medical, accessibility}``

And is NEVER read from a model output field, even if the model tries to set one.
This mirrors how ``priority_score`` and ``requires_emergency_escalation`` are
deterministic elsewhere in the system (Doc #3, ADDENDUM G4).
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.orchestration.interfaces import ModelRouter, ModelTier
from backend.orchestration.logging_ import InvocationRecord
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


# Import after fixture definitions
from backend.app.services.translation import _derive_high_stakes  # noqa: E402


class TestHighStakesDerivation:
    """Doc #8 §4.1 — high_stakes is deterministic, never from model output."""

    # --- Rule: emergency_flag OR category in {medical, accessibility} ---

    @pytest.mark.parametrize("emergency_flag,category,expected", [
        (True, "general", True),       # emergency_flag alone triggers high_stakes
        (True, "medical", True),       # both true
        (True, "accessibility", True), # both true
        (True, "lost_fan", True),      # emergency_flag alone
        (False, "medical", True),      # medical category alone
        (False, "accessibility", True), # accessibility category alone
        (False, "general", False),     # neither
        (False, "lost_fan", False),    # neither
        (False, "lost_item", False),   # neither
        (False, "translation", False), # neither
        (False, "crowd_queue", False), # neither
    ])
    def test_high_stakes_deterministic_rule(
        self,
        emergency_flag: bool,
        category: str,
        expected: bool,
    ) -> None:
        """high_stakes follows the deterministic rule, period."""
        result = _derive_high_stakes(emergency_flag=emergency_flag, category=category)
        assert result == expected, (
            f"high_stakes({emergency_flag=}, {category=}) should be {expected}"
        )

    async def test_model_cannot_override_high_stakes(
        self,
        fast_cheap_provider: StubProvider,
        model_router: ModelRouter,
        log_callback: Any,
    ) -> None:
        """Even if the model sets high_stakes=false for emergency, code overrides.

        This proves high_stakes is NEVER read from the model output — it's
        always derived deterministically AFTER the model call.
        """
        # Model returns high_stakes=false despite emergency content
        fast_cheap_provider._result = {
            "translated_text": "Help, my son can't breathe!",
            "detected_language": "es",
            "confidence": 0.95,
            "emergency_flag": True,
            "back_translation": None,
            "high_stakes": False,  # model says false — but code must override
        }

        from backend.app.services.translation import translate_message

        result = await translate_message(
            original_text="¡Ayuda, mi hijo no puede respirar!",
            source_language="es",
            target_language="en",
            model_router=model_router,
            log_callback=log_callback,
        )

        data = result.data

        # Code must override the model's high_stakes=false
        assert data["high_stakes"] is True, (
            "high_stakes must be True when emergency_flag is True, "
            "regardless of what the model outputs"
        )

    async def test_model_cannot_set_high_stakes_when_not_warranted(
        self,
        fast_cheap_provider: StubProvider,
        model_router: ModelRouter,
        log_callback: Any,
    ) -> None:
        """Even if the model sets high_stakes=true for non-emergency + non-medical/accessibility, code overrides."""
        fast_cheap_provider._result = {
            "translated_text": "Where is the bathroom?",
            "detected_language": "pt",
            "confidence": 0.95,
            "emergency_flag": False,
            "back_translation": None,
            "high_stakes": True,  # model says true — but code must override
        }

        from backend.app.services.translation import translate_message

        result = await translate_message(
            original_text="Onde fica o banheiro?",
            source_language="pt",
            target_language="en",
            model_router=model_router,
            log_callback=log_callback,
        )

        data = result.data

        # high_stakes should be false (no emergency, category is 'general' for stand-alone translation)
        assert data["high_stakes"] is False, (
            "high_stakes must be False when emergency_flag is False and "
            "category is not medical/accessibility, regardless of model output"
        )
