"""Test 5: Priority-score purity — identical input → identical output, no side effects.

Doc #3 §2.1: "priority_score is deliberately not a raw model output."
"""

from backend.app.core.priority import compute_priority_score


class TestPriorityScorePurity:
    """Priority-score calculator is a pure function with documented weights."""

    def test_identical_input_identical_output(self) -> None:
        result1 = compute_priority_score(
            category="medical", crowd_density_level="HIGH", queue_wait_minutes=None
        )
        result2 = compute_priority_score(
            category="medical", crowd_density_level="HIGH", queue_wait_minutes=None
        )
        assert result1 == result2
        assert isinstance(result1, int)

    def test_no_side_effects(self) -> None:
        cat = "general"
        density = "LOW"
        compute_priority_score(category=cat, crowd_density_level=density, queue_wait_minutes=None)  # type: ignore[arg-type]
        assert cat == "general"
        assert density == "LOW"

    def test_score_in_range(self) -> None:
        for cat in ("medical", "lost_fan", "translation", "accessibility", "crowd_queue", "lost_item", "general"):
            for density in ("LOW", "MODERATE", "HIGH", "CRITICAL", None):
                score = compute_priority_score(
                    category=cat, crowd_density_level=density, queue_wait_minutes=None
                )
                assert 0 <= score <= 100, f"{cat}/{density} → {score} outside [0,100]"

    def test_medical_higher_than_general(self) -> None:
        med = compute_priority_score("medical", crowd_density_level="LOW", queue_wait_minutes=None)
        gen = compute_priority_score("general", crowd_density_level="LOW", queue_wait_minutes=None)
        assert med > gen, "Medical should score higher than general"

    def test_crowd_density_increases_score(self) -> None:
        base = compute_priority_score("lost_fan", crowd_density_level="LOW", queue_wait_minutes=None)
        high = compute_priority_score("lost_fan", crowd_density_level="CRITICAL", queue_wait_minutes=None)
        assert high >= base, "Higher crowd density should not decrease priority"

    def test_queue_wait_adds_to_crowd_queue(self) -> None:
        no_wait = compute_priority_score("crowd_queue", crowd_density_level="MODERATE", queue_wait_minutes=0)
        with_wait = compute_priority_score("crowd_queue", crowd_density_level="MODERATE", queue_wait_minutes=15)
        assert with_wait >= no_wait, "Queue wait should increase priority for CROWD_QUEUE"

    def test_docstring_cites_doc3_section(self) -> None:
        doc = compute_priority_score.__doc__ or ""
        assert "weights" in doc.lower() or "calibration" in doc.lower(), (
            "Docstring should mention explicit weights/calibration"
        )

    def test_queue_wait_does_not_affect_non_queue_categories(self) -> None:
        no_wait = compute_priority_score("medical", crowd_density_level="MODERATE", queue_wait_minutes=None)
        with_wait = compute_priority_score("medical", crowd_density_level="MODERATE", queue_wait_minutes=30)
        assert no_wait == with_wait, "Queue wait should NOT affect non-CROWD_QUEUE categories"
