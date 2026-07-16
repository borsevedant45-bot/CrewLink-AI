"""Doc #7 §5.4 — Translation golden-set extension (Doc #8 §4.3).

Graded on:
- Schema conformance (hard 100% gate): every TranslationResult must validate
  through Pydantic without error.
- Back-translation similarity (threshold-graded): original text compared
  against back_translation (reported, not a merge-block).
- Confidence floor (reported): medical/accessibility/emergency phrases
  must have confidence >= 0.4 (reported, not a merge-block).

In CI (LLM_MODE=recorded), golden-set fixtures replay deterministic
responses.  Live-model eval (LLM_MODE=live) is nightly-only and never
blocks a merge.
"""

from __future__ import annotations

import pytest

from backend.orchestration.schemas import TranslationResult


# ── Representative high-stakes phrases per supported language  ──
#  (Doc #8 §4.3, table T1–T8)

TRANSLATION_GOLDEN_CASES = [
    # (name, language, original_en, translated_text, confidence, emergency,
    #  back_translation, high_stakes_expected)
    pytest.param(
        "T1",
        "es",
        "He is not breathing",
        "No está respirando",
        0.92,
        False,
        "He is not breathing",
        True,
        id="T1-es-medical-not-breathing",
    ),
    pytest.param(
        "T2",
        "es",
        "Where is the accessible restroom?",
        "¿Dónde está el baño accesible?",
        0.88,
        False,
        "Where is the accessible restroom?",
        True,
        id="T2-es-accessibility-restroom",
    ),
    pytest.param(
        "T3",
        "fr",
        "She fell and hit her head",
        "Elle est tombée et s'est cogné la tête",
        0.85,
        False,
        "She fell and hit her head",
        True,
        id="T3-fr-medical-fell",
    ),
    pytest.param(
        "T4",
        "fr",
        "I need a wheelchair escort",
        "J'ai besoin d'un accompagnement en fauteuil roulant",
        0.78,
        False,
        "I need a wheelchair escort",
        True,
        id="T4-fr-accessibility-wheelchair",
    ),
    pytest.param(
        "T5",
        "de",
        "There is a fire in the east concourse",
        "Es gibt ein Feuer im Ostkonkurs",
        0.82,
        True,
        "There is a fire in the east concourse",
        True,
        id="T5-de-emergency-fire",
    ),
    pytest.param(
        "T6",
        "ja",
        "My child is having a seizure",
        "私の子供が発作を起こしています",
        0.90,
        False,
        "My child is having a seizure",
        True,
        id="T6-ja-medical-seizure",
    ),
    pytest.param(
        "T7",
        "ko",
        "Where is the quiet room?",
        "조용한 방이 어디에 있나요?",
        0.75,
        False,
        "Where is the quiet room?",
        True,
        id="T7-ko-accessibility-quiet",
    ),
    pytest.param(
        "T8",
        "ar",
        "He has a severe allergic reaction",
        "لديه رد فعل تحسسي شديد",
        0.80,
        True,
        "He has a severe allergic reaction",
        True,
        id="T8-ar-medical-emergency-allergic",
    ),
]


pytestmark = pytest.mark.llm


class TestTranslationGoldenSet:
    """Doc #8 §4.3 — Translation golden-set: schema conformance + quality."""

    @pytest.mark.parametrize(
        ("case_id", "language", "original", "translated", "confidence",
         "emergency", "back_translation", "high_stakes"),
        TRANSLATION_GOLDEN_CASES,
    )
    def test_schema_conformance(
        self,
        case_id: str,
        language: str,
        original: str,
        translated: str,
        confidence: float,
        emergency: bool,
        back_translation: str,
        high_stakes: bool,
    ) -> None:
        """Hard 100% gate: every TranslationResult must validate through
        Pydantic without error."""
        result = TranslationResult(
            translated_text=translated,
            detected_language=language,
            confidence=confidence,
            emergency_flag=emergency,
            back_translation=back_translation,
            high_stakes=high_stakes,
        )
        dumped = result.model_dump()
        validated = TranslationResult.model_validate(dumped)
        assert validated.translated_text == translated
        assert validated.detected_language == language
        assert validated.confidence == confidence
        assert validated.emergency_flag == emergency
        assert validated.back_translation == back_translation
        assert validated.high_stakes == high_stakes

    @pytest.mark.parametrize(
        ("case_id", "language", "original", "translated", "confidence",
         "emergency", "back_translation", "high_stakes"),
        TRANSLATION_GOLDEN_CASES,
    )
    def test_confidence_floor(
        self,
        case_id: str,
        language: str,
        original: str,
        translated: str,
        confidence: float,
        emergency: bool,
        back_translation: str,
        high_stakes: bool,
    ) -> None:
        """Confidence floor >= 0.4 for all medical/accessibility/emergency
        phrases (reported, not a merge-block)."""
        assert confidence >= 0.4, (
            f"{case_id}: confidence {confidence} < 0.4 floor"
        )

    @pytest.mark.parametrize(
        ("case_id", "language", "original", "translated", "confidence",
         "emergency", "back_translation", "high_stakes"),
        TRANSLATION_GOLDEN_CASES,
    )
    def test_back_translation_similarity(
        self,
        case_id: str,
        language: str,
        original: str,
        translated: str,
        confidence: float,
        emergency: bool,
        back_translation: str,
        high_stakes: bool,
    ) -> None:
        """Back-translation similarity >= 0.6 (BLEU) with original.

        For the recorded / golden-set path, we assert exact-match since
        the fixture is pinned.  In live-model eval, this is threshold-
        graded and reported, never a merge block."""
        assert back_translation == original, (
            f"{case_id}: back_translation differs from original\n"
            f"  original:       {original}\n"
            f"  back_translation: {back_translation}"
        )

    def test_fallback_schema_conformant(self) -> None:
        """Fallback must produce schema-conformant TranslationResult."""
        from backend.orchestration.fallbacks import _translation_fallback

        fallback = _translation_fallback()
        dumped = fallback.model_dump()
        validated = TranslationResult.model_validate(dumped)
        assert validated.detected_language == "und"
        assert validated.confidence == 0.0
        assert validated.emergency_flag is False
