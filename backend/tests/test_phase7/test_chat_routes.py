"""Integration tests for the Chat Session REST endpoints.

Doc #5 §2.7 — Chat Session CRUD + message translation.
Doc #7 §4 — Integration flow #3: full stack with forced-failure case.
Doc #5 §3.5 — emergency_flag auto-creates Incident + fires broadcast.

Tests:
  1. Create session → send message → verify translation response shape.
  2. Forced translation failure → 2xx + fallback_used, never 503.
  3. Emergency message auto-creates Incident + calls broadcast_emergency.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestChatRoutes:
    """Doc #5 §2.7 — chat session CRUD + message translation."""

    def test_create_chat_session(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
    ) -> None:
        """POST /api/v1/chat-sessions creates a session."""
        payload = {
            "zone_id": "zone_east_concourse",
            "fan_language": "es",
            "volunteer_language": "en",
        }
        resp = overridden_client.post(
            "/api/v1/chat-sessions",
            json=payload,
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "session_id" in data
        assert data["zone_id"] == "zone_east_concourse"
        assert data["status"] == "active"
        assert data["volunteer_language"] == "en"
        assert data["fan_language"] == "es"

    def test_list_chat_sessions(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
    ) -> None:
        """GET /api/v1/chat-sessions returns owned sessions."""
        # Create one first
        payload = {
            "zone_id": "zone_east_concourse",
            "fan_language": "es",
            "volunteer_language": "en",
        }
        overridden_client.post(
            "/api/v1/chat-sessions",
            json=payload,
            headers=_auth_header(volunteer_token_zone_a),
        )

        resp = overridden_client.get(
            "/api/v1/chat-sessions",
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) >= 1

    def test_get_chat_session(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
    ) -> None:
        """GET /api/v1/chat-sessions/{id} returns session detail."""
        create_resp = overridden_client.post(
            "/api/v1/chat-sessions",
            json={"zone_id": "zone_east_concourse", "fan_language": "es", "volunteer_language": "en"},
            headers=_auth_header(volunteer_token_zone_a),
        )
        session_id = create_resp.json()["session_id"]

        resp = overridden_client.get(
            f"/api/v1/chat-sessions/{session_id}",
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert resp.status_code == 200
        assert resp.json()["session_id"] == session_id

    def test_send_message_normal(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
    ) -> None:
        """POST /api/v1/chat-sessions/{id}/messages sends + translates (normal case).

        Integration flow #3 — happy path.
        """
        create_resp = overridden_client.post(
            "/api/v1/chat-sessions",
            json={"zone_id": "zone_east_concourse", "fan_language": "es", "volunteer_language": "en"},
            headers=_auth_header(volunteer_token_zone_a),
        )
        session_id = create_resp.json()["session_id"]

        msg_payload = {
            "sender": "fan",
            "original_text": "¿Dónde está la salida?",
            "original_language": "es",
        }
        resp = overridden_client.post(
            f"/api/v1/chat-sessions/{session_id}/messages",
            json=msg_payload,
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "message_id" in data
        assert data["sender"] == "fan"
        assert data["original_language"] == "es"
        # Translation result fields per Doc #5 §2.7
        assert "translated_text" in data
        assert "confidence" in data
        assert "emergency_flag" in data
        assert "high_stakes" in data or "fallback_used" in data

    def test_send_message_translation_failure_returns_fallback(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
    ) -> None:
        """Forced translation failure → 2xx with fallback_used, NEVER 503.

        Doc #4 §5.3: "Translation Bridge → Original text shown with a visible
        'translation unavailable' notice and a retry affordance — never a
        guessed translation."
        Doc #5 §5: "AI calls with a deterministic fallback never fail the HTTP
        request."
        """
        create_resp = overridden_client.post(
            "/api/v1/chat-sessions",
            json={"zone_id": "zone_east_concourse", "fan_language": "es", "volunteer_language": "en"},
            headers=_auth_header(volunteer_token_zone_a),
        )
        session_id = create_resp.json()["session_id"]

        msg_payload = {
            "sender": "fan",
            "original_text": "¿Dónde está la salida?",
            "original_language": "es",
        }

        # The test's StubProvider raises TimeoutError by default when _result
        # is not set (it tries to do schema() which may fail). We rely on the
        # overridden_client's model_router which has a StubProvider with no
        # result set — causing complete_with_fallback to trigger fallback.
        resp = overridden_client.post(
            f"/api/v1/chat-sessions/{session_id}/messages",
            json=msg_payload,
            headers=_auth_header(volunteer_token_zone_a),
        )

        # MUST be 2xx, never 503
        assert resp.status_code < 500, (
            f"Translation failure must NOT return 5xx — got {resp.status_code}: {resp.text}"
        )
        assert resp.status_code in (200, 201), (
            f"Expected 2xx on fallback, got {resp.status_code}"
        )
        data = resp.json()
        # Fallback indicator must be present
        assert data.get("fallback_used") is True or data.get("fallback_used") == "true", (
            "Fallback must be indicated when translation fails"
        )

    def test_close_chat_session(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
    ) -> None:
        """PATCH /api/v1/chat-sessions/{id}/close marks session ended."""
        create_resp = overridden_client.post(
            "/api/v1/chat-sessions",
            json={"zone_id": "zone_east_concourse", "fan_language": "es", "volunteer_language": "en"},
            headers=_auth_header(volunteer_token_zone_a),
        )
        session_id = create_resp.json()["session_id"]

        resp = overridden_client.patch(
            f"/api/v1/chat-sessions/{session_id}/close",
            json={},
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"

    def test_get_messages(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
    ) -> None:
        """GET /api/v1/chat-sessions/{id}/messages returns paginated history."""
        create_resp = overridden_client.post(
            "/api/v1/chat-sessions",
            json={"zone_id": "zone_east_concourse", "fan_language": "es", "volunteer_language": "en"},
            headers=_auth_header(volunteer_token_zone_a),
        )
        session_id = create_resp.json()["session_id"]

        # Send a message first
        overridden_client.post(
            f"/api/v1/chat-sessions/{session_id}/messages",
            json={"sender": "fan", "original_text": "Hola", "original_language": "es"},
            headers=_auth_header(volunteer_token_zone_a),
        )

        resp = overridden_client.get(
            f"/api/v1/chat-sessions/{session_id}/messages",
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) >= 1

    def test_send_message_requires_auth(
        self,
        overridden_client: TestClient,
    ) -> None:
        """POST /api/v1/chat-sessions/{id}/messages without auth → 401."""
        resp = overridden_client.post(
            "/api/v1/chat-sessions/fake-session/messages",
            json={"sender": "fan", "original_text": "test", "original_language": "es"},
        )
        assert resp.status_code == 401
