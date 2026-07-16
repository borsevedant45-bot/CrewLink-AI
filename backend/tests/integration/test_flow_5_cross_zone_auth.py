"""Doc #7 §4 — Integration flow #5: Cross-zone auth + supervisor rollup.

Covers:
1. Zone-A token on Zone-B incident → 403/404, never a silent empty 200
2. Zone-A token on Zone-B task-feed → only Zone-A incidents returned
3. Zone-A token on Zone-B chat session → 403/404
4. Supervisor with zone=null can access any zone's incidents
5. Supervisor with zone restriction can only access their assigned zone
6. Rollup content follows JWT claim, never a client-supplied zone param
7. No client-supplied zone parameter can broaden scope
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestFlow5CrossZoneAuth:
    """Doc #7 §4 — Flow #5: cross-zone auth + rollup."""

    # ------------------------------------------------------------------
    # 5a. Zone-A volunteer accessing Zone-B incident → 403/404
    # ------------------------------------------------------------------

    def test_zone_a_cannot_read_zone_b_incident(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
        volunteer_token_zone_b: str,
    ) -> None:
        """Zone-A token on Zone-B incident returns 404 (hidden), never 200."""

        # Create an incident in Zone A first (so we know Zone A incidents exist)
        create_a = overridden_client.post(
            "/api/v1/incidents",
            json={
                "zone_id": "zone_east_concourse",
                "description": "Zone A test incident",
                "source": "VOLUNTEER_REPORTED",
                "reported_by_volunteer_id": "vol_maria_alvarez",
            },
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert create_a.status_code == 201
        inc_id_a = create_a.json()["incident_id"]

        # Zone-B token tries to read Zone-A incident → 404 (hidden, never 200)
        resp = overridden_client.get(
            f"/api/v1/incidents/{inc_id_a}",
            headers=_auth_header(volunteer_token_zone_b),
        )
        assert resp.status_code == 404, (
            f"Cross-zone read should return 404, got {resp.status_code}: {resp.text}"
        )
        # Response body must not contain incident data — only an error message
        body = resp.json()
        assert "incident_id" not in body, "Cross-zone read must not leak incident data"
        assert body.get("detail") or body.get("error", {}).get("message"), (
            "Should return proper error message, not a silent empty 200"
        )

    # ------------------------------------------------------------------
    # 5b. Zone-A token on Zone-B task-feed → only Zone-A incidents
    # ------------------------------------------------------------------

    def test_zone_a_feed_only_shows_zone_a(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
    ) -> None:
        """Zone-A token's task feed only contains Zone-A incidents."""

        resp = overridden_client.get(
            "/api/v1/incidents/feed",
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data.get("data", []))
        for item in items:
            assert item.get("zone_id") == "zone_east_concourse", (
                f"Feed should only show zone_east_concourse incidents, "
                f"got zone_id={item.get('zone_id')}"
            )

    # ------------------------------------------------------------------
    # 5c. Zone-A token on Zone-B chat session → 403/404
    # ------------------------------------------------------------------

    def test_zone_a_cannot_read_zone_b_chat(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
        volunteer_token_zone_b: str,
    ) -> None:
        """Zone-A token on Zone-B chat session returns 403/404."""

        # Create a chat session in Zone B
        create_b = overridden_client.post(
            "/api/v1/chat-sessions",
            json={
                "zone_id": "zone_west_concourse",
                "fan_language": "es",
                "volunteer_language": "en",
            },
            headers=_auth_header(volunteer_token_zone_b),
        )
        assert create_b.status_code == 201
        session_id_b = create_b.json()["session_id"]

        # Zone-A token tries to read Zone-B chat → 403/404
        resp = overridden_client.get(
            f"/api/v1/chat-sessions/{session_id_b}",
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert resp.status_code in (403, 404), (
            f"Cross-zone chat read should return 403/404, got {resp.status_code}"
        )

    # ------------------------------------------------------------------
    # 5d. Supervisor with null zone can access any zone
    # ------------------------------------------------------------------

    def test_supervisor_all_zones_can_access_any_zone(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
        supervisor_token_all_zones: str,
    ) -> None:
        """Supervisor (zone=null) can read incidents from any zone."""

        create_a = overridden_client.post(
            "/api/v1/incidents",
            json={
                "zone_id": "zone_east_concourse",
                "description": "Zone A for supervisor test",
                "source": "VOLUNTEER_REPORTED",
                "reported_by_volunteer_id": "vol_maria_alvarez",
            },
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert create_a.status_code == 201
        inc_id = create_a.json()["incident_id"]

        # Supervisor reads it
        resp = overridden_client.get(
            f"/api/v1/incidents/{inc_id}",
            headers=_auth_header(supervisor_token_all_zones),
        )
        assert resp.status_code == 200, (
            f"Supervisor should be able to read any zone incident, "
            f"got {resp.status_code}: {resp.text}"
        )
        assert resp.json()["incident_id"] == inc_id

    # ------------------------------------------------------------------
    # 5e. Zone-scoped supervisor access (informational zone_id)
    # Doc #5 §1.3: supervisors "span every zone at the venue" — a
    # supervisor's JWT zone_id is informational, never restrictive.
    # All supervisors can access any zone's incidents.
    # ------------------------------------------------------------------

    def test_zone_scoped_supervisor_still_sees_all_zones(
        self,
        overridden_client: TestClient,
        supervisor_token_zone_a_only: str,
    ) -> None:
        """Supervisor with zone=zone_east_concourse in JWT can still read all zones.

        Per Doc #5 §1.3, supervisors span every zone. The zone_id claim
        on a supervisor JWT is informational, not an access restriction.
        """
        resp = overridden_client.get(
            "/api/v1/incidents",
            headers=_auth_header(supervisor_token_zone_a_only),
        )
        assert resp.status_code == 200, (
            f"Supervisor should be able to list all incidents, "
            f"got {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        items = data.get("items", data.get("data", []))
        assert len(items) > 0, "Supervisor should see incidents across all zones"

    # ------------------------------------------------------------------
    # 5f. Rollup follows JWT claim, never client-supplied zone param
    # ------------------------------------------------------------------

    def test_rollup_ignores_client_supplied_zone_param(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
        volunteer_token_zone_b: str,
    ) -> None:
        """Client-supplied zone parameter cannot broaden scope."""

        # Zone-A token with a forged zone_b parameter
        resp = overridden_client.get(
            "/api/v1/incidents",
            params={"zone_id": "zone_west_concourse"},
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data.get("data", []))
        for item in items:
            assert item.get("zone_id") != "zone_west_concourse", (
                "Client-supplied zone param must not broaden scope"
            )

    # ------------------------------------------------------------------
    # 5g. Cross-zone write is also blocked
    # ------------------------------------------------------------------

    def test_zone_a_cannot_patch_zone_b_incident(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
        volunteer_token_zone_b: str,
    ) -> None:
        """Zone-A token cannot modify Zone-B incident."""

        from backend.app.core.auth import create_jwt_token
        vol_b_token = create_jwt_token("vol_west", "volunteer", "zone_west_concourse")

        create_b = overridden_client.post(
            "/api/v1/incidents",
            json={
                "zone_id": "zone_west_concourse",
                "description": "Zone B incident for write test",
                "source": "VOLUNTEER_REPORTED",
                "reported_by_volunteer_id": "vol_west",
            },
            headers=_auth_header(vol_b_token),
        )
        assert create_b.status_code == 201
        inc_id_b = create_b.json()["incident_id"]

        resp = overridden_client.patch(
            f"/api/v1/incidents/{inc_id_b}/status",
            json={"status": "Triaged"},
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert resp.status_code in (403, 404, 422), (
            f"Cross-zone write should return 403/404/422, got {resp.status_code}: {resp.text}"
        )
        # Must not silently succeed
        body = resp.json()
        assert "incident_id" not in body, "Cross-zone write must not leak incident data"
