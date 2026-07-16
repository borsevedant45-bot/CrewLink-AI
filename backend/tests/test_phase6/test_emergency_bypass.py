"""Emergency bypass call-count test.

Proves that when ``requires_emergency_escalation`` is true, the dispatch
service NEVER calls the Reasoning-tier LLM provider — not even once.
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.orchestration.interfaces import ModelRouter, ModelTier
from backend.orchestration.logging_ import InvocationRecord

from tests.test_orchestration.stub_provider import StubProvider

from backend.app.services.dispatch_recommender import recommend_dispatch


@pytest.fixture
def log_spy() -> list[InvocationRecord]:
    return []


@pytest.fixture
def log_callback(log_spy: list[InvocationRecord]) -> Any:
    async def _cb(record: InvocationRecord) -> None:
        log_spy.append(record)
    return _cb


class TestEmergencyBypass:
    """Provable: Reasoning tier = 0 calls for emergency incidents."""

    async def test_reasoning_tier_not_called_for_emergency(
        self,
        log_callback: Any,
        log_spy: list[InvocationRecord],
    ) -> None:
        """Set provider to raise — if called, test fails.

        The dispatch service MUST check requires_emergency_escalation BEFORE
        calling the provider.
        """
        call_counter = {"count": 0}

        class CallCountingStub(StubProvider):
            async def complete_structured(
                self,
                *,
                system: str,
                user: str,
                schema: type[Any],
                timeout_s: float,
            ) -> Any:
                call_counter["count"] += 1
                msg = f"Provider was called (count={call_counter['count']}) despite emergency bypass"
                raise RuntimeError(msg)

        router = ModelRouter({
            ModelTier.FAST_CHEAP: StubProvider(),
            ModelTier.REASONING: CallCountingStub(),
        })

        result = await recommend_dispatch(
            incident_data={
                "incident_id": "inc_emerg_001",
                "category": "medical",
                "severity_signal": "high",
                "zone_id": "zone_east_concourse",
                "description": "Fan collapsed, not breathing — emergency at Gate 4",
                "requires_emergency_escalation": True,
            },
            candidates=[
                {"volunteer_id": "vol_001", "zone_id": "zone_east_concourse", "role": "volunteer", "certifications": ["First Aid"]},
            ],
            model_router=router,
            log_callback=log_callback,
        )

        # Proving the provider was never called
        assert call_counter["count"] == 0, "Reasoning-tier provider was called — EMERGENCY BYPASS FAILED"
        # Result should indicate bypass
        assert result.fallback_used
        assert result.fallback_name is not None
        assert result.error_reason == "emergency_bypass"

    async def test_non_emergency_calls_provider_normally(
        self,
        log_callback: Any,
    ) -> None:
        """Non-emergency incident → provider IS called."""
        call_counter = {"count": 0}

        class TrackingStub(StubProvider):
            async def complete_structured(
                self,
                *,
                system: str,
                user: str,
                schema: type[Any],
                timeout_s: float,
            ) -> Any:
                call_counter["count"] += 1
                return schema(
                    recommended_volunteers=[{"volunteer_id": "vol_001", "rank": 1, "rationale": "Nearest available"}],
                    requires_human_supervisor_review=False,
                    confidence=0.85,
                )

        router = ModelRouter({
            ModelTier.FAST_CHEAP: StubProvider(),
            ModelTier.REASONING: TrackingStub(),
        })

        result = await recommend_dispatch(
            incident_data={
                "incident_id": "inc_non_emerg_001",
                "category": "lost_fan",
                "severity_signal": "high",
                "zone_id": "zone_east_concourse",
                "description": "Lost child near Gate 2",
                "requires_emergency_escalation": False,
            },
            candidates=[
                {"volunteer_id": "vol_001", "zone_id": "zone_east_concourse", "role": "volunteer", "certifications": []},
            ],
            model_router=router,
            log_callback=log_callback,
        )

        assert call_counter["count"] == 1, "Non-emergency: provider should be called exactly once"
        assert not result.fallback_used
        assert len(result.data["recommended_volunteers"]) == 1
