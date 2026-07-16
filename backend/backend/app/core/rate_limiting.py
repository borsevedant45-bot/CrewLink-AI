"""In-process rate limiter keyed on (user_id, tier).

ADDENDUM G2 tier limits:
  AUTH=5         — POST /auth/*
  STANDARD=120   — CRUD on zones, volunteers, shifts, sessions
  REALTIME_POLL=30 — GET /incidents, /incidents/feed, /zones/{id}/crowd-density
  AI_FAST=30     — POST /incidents, POST chatbot messages
  AI_REASONING=6 — dispatch-recommendation, kb-ask, shift-summary
"""

from __future__ import annotations

import time

RateLimitTier = str

_TIER_LIMITS: dict[RateLimitTier, int] = {
    "AUTH": 5,
    "STANDARD": 120,
    "REALTIME_POLL": 30,
    "AI_FAST": 30,
    "AI_REASONING": 6,
}

DEFAULT_WINDOW = 60  # seconds


class RateLimiter:
    """Simple in-memory sliding-window counter per (user_id, tier) key."""

    def __init__(self, window_seconds: int = DEFAULT_WINDOW) -> None:
        self._window = window_seconds
        self._counters: dict[tuple[str, RateLimitTier], list[float]] = {}
        self._windows: dict[tuple[str, RateLimitTier], float] = {}

    @staticmethod
    def get_limit(tier: RateLimitTier) -> int:
        return _TIER_LIMITS.get(tier, 0)

    def check(self, key: tuple[str, RateLimitTier]) -> bool:
        limit = self.get_limit(key[1])
        if limit == 0:
            return False  # unknown tier
        now = time.monotonic()
        window_start = now - self._window
        timestamps = self._counters.setdefault(key, [])
        # Prune old entries
        timestamps[:] = [t for t in timestamps if t > window_start]
        if len(timestamps) >= limit:
            return False
        timestamps.append(now)
        self._windows[key] = now
        return True

    def reset_key(self, key: tuple[str, RateLimitTier]) -> None:
        self._counters.pop(key, None)
        self._windows.pop(key, None)

    def remaining(self, key: tuple[str, RateLimitTier]) -> int:
        limit = self.get_limit(key[1])
        timestamps = self._counters.get(key, [])
        now = time.monotonic()
        window_start = now - self._window
        active = sum(1 for t in timestamps if t > window_start)
        return max(0, limit - active)
