"""Doc #7 §4 — Integration flow #5: FR-4 status propagation to supervisor rollup.

Tests FR-4: "Let a volunteer change a task's status (Acknowledged / En Route /
Resolved) in one tap; propagate the change to the supervisor rollup within 5
seconds." (Doc #1 §5.1 FR-4)

Per G14: "En Route" button → status ``in_progress``.
"""

from __future__ import annotations

import json
import time
from typing import Any

from fastapi.testclient import TestClient

from tests.test_orchestration.stub_provider import StubProvider


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _walk_to(
    client: TestClient,
    incident_id: str,
    token: str,
    *statuses: str,
) -> None:
    """Walk the incident through a chain of status transitions."""
    for s in statuses:
        resp = client.patch(
            f"/api/v1/incidents/{incident_id}/status",
            json={"status": s},
            headers=_auth_header(token),
        )
        assert resp.status_code == 200, (
            f"Transition to {s} failed: {resp.status_code} {resp.text}"
        )


class TestFR4StatusPropagation:
    """FR-4: one-tap status change → supervisor rollup within 5s."""

    def test_acknowledged_propagates_to_supervisor_within_5s(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
        supervisor_token: str,
        fast_cheap_provider: StubProvider,
    ) -> None:
        """Volunteer taps 'Acknowledged' → supervisor WS sees incident.updated within 5s.

        Per Doc #1 §5.1 FR-4: the change must reach the supervisor rollup within 5 seconds.
        """
        fast_cheap_provider._result = {
            "category": "general",
            "severity_signal": "low",
            "confidence": 0.9,
            "reasoning_summary": "Test incident for FR-4 propagation.",
            "requires_emergency_escalation": False,
        }
        create_resp = overridden_client.post(
            "/api/v1/incidents",
            json={"zone_id": "zone_east_concourse", "description": "Test incident for FR-4"},
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert create_resp.status_code == 201
        incident_id = create_resp.json()["incident_id"]

        ticket_resp = overridden_client.post(
            "/api/v1/auth/ws-ticket",
            headers=_auth_header(supervisor_token),
        )
        ws_ticket = ticket_resp.json()["ticket"]

        # Walk to Dispatched (the state from which "Acknowledged" is a valid FR-4 tap)
        _walk_to(
            overridden_client, incident_id, volunteer_token_zone_a,
            "Triaged", "Dispatched",
        )

        received_events: list[dict[str, Any]] = []
        start = time.monotonic()

        with overridden_client.websocket_connect(
            f"/api/v1/ws/supervisor?ticket={ws_ticket}",
        ) as ws:
            time.sleep(0.15)

            # FR-4 one-tap: volunteer taps "Acknowledged"
            status_resp = overridden_client.patch(
                f"/api/v1/incidents/{incident_id}/status",
                json={"status": "Acknowledged"},
                headers=_auth_header(volunteer_token_zone_a),
            )
            assert status_resp.status_code == 200

            deadline = start + 5.0
            while time.monotonic() < deadline:
                try:
                    raw = ws.receive_text()
                    msg = json.loads(raw)
                    received_events.append(msg)
                    if msg.get("event") == "incident.updated":
                        break
                except Exception:
                    time.sleep(0.05)

            elapsed = time.monotonic() - start

        assert elapsed < 5.0, f"Propagation took {elapsed:.2f}s (limit 5s)"
        update_events = [e for e in received_events if e.get("event") == "incident.updated"]
        assert len(update_events) > 0, "No incident.updated on supervisor WS"
        last = update_events[-1]
        assert last["data"]["status"] == "Acknowledged"
        assert last["data"]["incident_id"] == incident_id

    def test_en_route_maps_to_in_progress(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
        supervisor_token: str,
        fast_cheap_provider: StubProvider,
    ) -> None:
        """Per G14: "En Route" button → status ``in_progress``."""
        fast_cheap_provider._result = {
            "category": "general",
            "severity_signal": "low",
            "confidence": 0.9,
            "reasoning_summary": "Test incident for En Route mapping.",
            "requires_emergency_escalation": False,
        }
        create_resp = overridden_client.post(
            "/api/v1/incidents",
            json={"zone_id": "zone_east_concourse", "description": "FR-4 En Route test"},
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert create_resp.status_code == 201
        incident_id = create_resp.json()["incident_id"]

        ticket_resp = overridden_client.post(
            "/api/v1/auth/ws-ticket",
            headers=_auth_header(supervisor_token),
        )
        ws_ticket = ticket_resp.json()["ticket"]

        _walk_to(
            overridden_client, incident_id, volunteer_token_zone_a,
            "Triaged", "Dispatched", "Acknowledged",
        )

        received_events: list[dict[str, Any]] = []
        with overridden_client.websocket_connect(
            f"/api/v1/ws/supervisor?ticket={ws_ticket}",
        ) as ws:
            time.sleep(0.15)

            # FR-4 one-tap: volunteer taps "En Route" → InProgress per G14
            status_resp = overridden_client.patch(
                f"/api/v1/incidents/{incident_id}/status",
                json={"status": "InProgress"},
                headers=_auth_header(volunteer_token_zone_a),
            )
            assert status_resp.status_code == 200

            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                try:
                    raw = ws.receive_text()
                    msg = json.loads(raw)
                    received_events.append(msg)
                    update = msg.get("data", {})
                    if update.get("incident_id") == incident_id and update.get("status") == "InProgress":
                        break
                except Exception:
                    time.sleep(0.05)

        updates = [e for e in received_events if e.get("data", {}).get("incident_id") == incident_id]
        assert len(updates) > 0, "No events for incident on supervisor WS"
        last = updates[-1]
        assert last["data"]["status"] == "InProgress", (
            f"G14: En Route → InProgress, got {last['data']['status']}"
        )
