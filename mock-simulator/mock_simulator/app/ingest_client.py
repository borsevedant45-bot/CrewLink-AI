"""HTTP client for posting simulated events to the backend's /internal/ingest/* routes.

ADDENDUM G13: Static service credential in Authorization header.
"""

from __future__ import annotations

from typing import Any

import httpx


class IngestClient:
    """Posts events to the backend internal ingestion API."""

    def __init__(self, base_url: str, auth_token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }

    def post_incident(self, event: dict[str, Any]) -> httpx.Response:
        return httpx.post(
            f"{self._base_url}/internal/ingest/incidents",
            json=event,
            headers=self._headers,
        )

    def post_crowd_density(self, event: dict[str, Any]) -> httpx.Response:
        return httpx.post(
            f"{self._base_url}/internal/ingest/crowd-density",
            json=event,
            headers=self._headers,
        )

    def post_position_ping(self, event: dict[str, Any]) -> httpx.Response:
        return httpx.post(
            f"{self._base_url}/internal/ingest/position-pings",
            json=event,
            headers=self._headers,
        )
