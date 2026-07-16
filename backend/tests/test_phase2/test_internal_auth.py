"""Test internal auth: /internal/* routes reject user JWTs.

ADDENDUM G13: Internal-only route family authenticated by static service credential.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestInternalRoutesRejectUserJwt:
    """/internal/* routes must reject any request bearing a user JWT."""

    def test_internal_route_no_auth_returns_401(self, client: TestClient) -> None:
        response = client.post("/internal/ingest/incidents", json={"test": True})
        assert response.status_code == 401, "No auth should return 401"

    def test_internal_route_with_user_jwt_returns_403(self, client: TestClient, volunteer_token_zone_a: str) -> None:
        response = client.post(
            "/internal/ingest/incidents",
            json={"test": True},
            headers={"Authorization": f"Bearer {volunteer_token_zone_a}"},
        )
        assert response.status_code == 403, (
            "User JWT on internal route should return 403"
        )

    def test_internal_route_with_service_credential_returns_not_501(self, client: TestClient) -> None:
        response = client.post(
            "/internal/ingest/incidents",
            json={"test": True, "source": "SIMULATED"},
            headers={"Authorization": "Bearer sim-service-token-change-in-prod"},
        )
        assert response.status_code != 401, "Service credential should be accepted"
        assert response.status_code != 403, "Service credential should be authorized"
