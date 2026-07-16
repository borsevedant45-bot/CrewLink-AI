"""Test 4: Rate-limit-tier assignment — every planned endpoint maps to exactly one tier.

ADDENDUM G2: AUTH=5, STANDARD=120, REALTIME_POLL=30, AI_FAST=30, AI_REASONING=6
"""

from __future__ import annotations

from backend.app.core.rate_limiting import RateLimiter, RateLimitTier

RATE_LIMIT_MANIFEST: dict[str, RateLimitTier] = {
    # Auth endpoints
    "POST /auth/login": "AUTH",
    "POST /auth/refresh": "AUTH",
    "POST /auth/ws-ticket": "STANDARD",
    # Volunteers
    "GET /volunteers": "STANDARD",
    "GET /volunteers/me": "STANDARD",
    "GET /volunteers/{volunteer_id}": "STANDARD",
    "PATCH /volunteers/{volunteer_id}/status": "STANDARD",
    "PATCH /volunteers/{volunteer_id}": "STANDARD",
    "POST /volunteers/{volunteer_id}/position-ping": "STANDARD",
    # Zones
    "GET /zones": "STANDARD",
    "GET /zones/{zone_id}": "STANDARD",
    "GET /zones/{zone_id}/volunteers": "STANDARD",
    "GET /zones/{zone_id}/crowd-density": "REALTIME_POLL",
    # Incidents
    "GET /incidents/feed": "REALTIME_POLL",
    "GET /incidents": "REALTIME_POLL",
    "GET /incidents/{incident_id}": "STANDARD",
    "POST /incidents": "AI_FAST",
    "POST /incidents/{incident_id}/dispatch-recommendation": "AI_REASONING",
    "PATCH /incidents/{incident_id}/assign": "STANDARD",
    "PATCH /incidents/{incident_id}/status": "STANDARD",
    # Shifts
    "GET /shifts": "STANDARD",
    "GET /shifts/{shift_id}": "STANDARD",
    "POST /shifts": "STANDARD",
    "PATCH /shifts/{shift_id}": "STANDARD",
    "POST /shifts/{shift_id}/checkin": "STANDARD",
    "POST /shifts/{shift_id}/checkout": "STANDARD",
    "GET /shifts/{shift_id}/summary": "AI_REASONING",
    # Chat sessions
    "POST /chat-sessions": "STANDARD",
    "GET /chat-sessions": "STANDARD",
    "GET /chat-sessions/{session_id}": "REALTIME_POLL",
    "GET /chat-sessions/{session_id}/messages": "REALTIME_POLL",
    "POST /chat-sessions/{session_id}/messages": "AI_FAST",
    "PATCH /chat-sessions/{session_id}/close": "STANDARD",
    # Knowledge base
    "GET /knowledge-base/documents": "STANDARD",
    "GET /knowledge-base/documents/{doc_id}": "STANDARD",
    "POST /knowledge-base/ask": "AI_REASONING",
}


class TestRateLimitTierManifest:
    """Every endpoint maps to exactly one rate-limit tier."""

    def test_all_endpoints_have_tier(self) -> None:
        missing = [ep for ep, tier in RATE_LIMIT_MANIFEST.items() if not tier]
        assert not missing, f"Endpoints without tier: {missing}"

    def test_tiers_are_valid(self) -> None:
        valid = {"AUTH", "STANDARD", "REALTIME_POLL", "AI_FAST", "AI_REASONING"}
        for ep, tier in RATE_LIMIT_MANIFEST.items():
            assert tier in valid, f"{ep} → invalid tier {tier}"

    def test_limit_values_match_addendum_g2(self) -> None:
        assert RateLimiter.get_limit("AUTH") == 5, "AUTH=5 per ADDENDUM G2"
        assert RateLimiter.get_limit("STANDARD") == 120, "STANDARD=120 per ADDENDUM G2"
        assert RateLimiter.get_limit("REALTIME_POLL") == 30
        assert RateLimiter.get_limit("AI_FAST") == 30
        assert RateLimiter.get_limit("AI_REASONING") == 6, "AI_REASONING=6 per ADDENDUM G2"


class TestRateLimiterBehavior:
    """In-process rate limiter keyed on (user_id, tier)."""

    def test_allows_within_limit(self) -> None:
        limiter = RateLimiter()
        key = ("test_user", "STANDARD")
        assert limiter.check(key)
        assert limiter.remaining(key) == 119

    def test_blocks_after_limit(self) -> None:
        limiter = RateLimiter()
        key = ("block_user", "AUTH")
        for _ in range(5):
            limiter.check(key)
        assert not limiter.check(key), "6th request should be blocked for AUTH tier"

    def test_reset_after_window(self) -> None:
        limiter = RateLimiter(window_seconds=0.01)
        key = ("reset_user", "STANDARD")
        # Exhaust
        for _ in range(120):
            limiter.check(key)
        assert not limiter.check(key), "Should be blocked after exhaust"
        # Reset the key
        limiter.reset_key(key)
        assert limiter.check(key), "Should allow after window reset"

    def test_different_tiers_independent(self) -> None:
        limiter = RateLimiter()
        user = "multi_tier_user"
        # Exhaust STANDARD
        for _ in range(120):
            limiter.check((user, "STANDARD"))
        assert not limiter.check((user, "STANDARD"))
        # REALTIME_POLL should still work
        assert limiter.check((user, "REALTIME_POLL"))
