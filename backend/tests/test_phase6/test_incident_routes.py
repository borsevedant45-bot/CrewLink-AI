"""Integration tests for the incident REST endpoints.

Tests creation, dispatch recommendation, status transitions, and
zone-scoping enforcement.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestIncidentRoutes:
    """Doc #5 §2.5 — incident CRUD + dispatch."""

    def test_create_incident(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
    ) -> None:
        """POST /api/v1/incidents creates an incident."""
        payload = {
            "zone_id": "zone_east_concourse",
            "description": "Fan with minor cut on hand near Gate 2",
            "source": "VOLUNTEER_REPORTED",
            "reported_by_volunteer_id": "vol_maria_alvarez",
        }
        resp = overridden_client.post(
            "/api/v1/incidents",
            json=payload,
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "incident_id" in data
        assert data["zone_id"] == "zone_east_concourse"
        assert data["source"] == "VOLUNTEER_REPORTED"
        assert data["status"] in ("Reported", "Triaged")

    def test_create_incident_requires_auth(
        self,
        overridden_client: TestClient,
    ) -> None:
        """POST /api/v1/incidents without auth → 401."""
        payload = {
            "zone_id": "zone_east_concourse",
            "description": "Test incident",
            "source": "VOLUNTEER_REPORTED",
        }
        resp = overridden_client.post("/api/v1/incidents", json=payload)
        assert resp.status_code == 401

    def test_create_incident_strips_simulated_source_for_volunteer(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
    ) -> None:
        """Volunteer cannot create SIMULATED incident (source override)."""
        payload = {
            "zone_id": "zone_east_concourse",
            "description": "Test",
            "source": "SIMULATED",
        }
        resp = overridden_client.post(
            "/api/v1/incidents",
            json=payload,
            headers=_auth_header(volunteer_token_zone_a),
        )
        # VOLUNTEER_REPORTED takes precedence for volunteer auth
        data = resp.json()
        assert data["source"] != "SIMULATED"

    def test_get_incident(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
    ) -> None:
        """GET /api/v1/incidents/{id} returns the incident."""
        # First create
        payload = {
            "zone_id": "zone_east_concourse",
            "description": "Test incident for detail view",
            "source": "VOLUNTEER_REPORTED",
        }
        create_resp = overridden_client.post(
            "/api/v1/incidents",
            json=payload,
            headers=_auth_header(volunteer_token_zone_a),
        )
        inc_id = create_resp.json()["incident_id"]

        # Then get
        resp = overridden_client.get(
            f"/api/v1/incidents/{inc_id}",
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert resp.status_code == 200
        assert resp.json()["incident_id"] == inc_id

    def test_get_incident_cross_zone_blocked(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
    ) -> None:
        """Volunteer from zone A cannot access incident from zone B."""
        # Create incident in zone A
        payload = {
            "zone_id": "zone_east_concourse",
            "description": "Incident in zone A",
            "source": "VOLUNTEER_REPORTED",
        }
        create_resp = overridden_client.post(
            "/api/v1/incidents",
            json=payload,
            headers=_auth_header(volunteer_token_zone_a),
        )
        inc_id = create_resp.json()["incident_id"]

        # Volunteer token for zone B (different zone)
        from backend.app.core.auth import create_jwt_token
        zone_b_token = create_jwt_token("vol_other", "volunteer", "zone_west_concourse")

        resp = overridden_client.get(
            f"/api/v1/incidents/{inc_id}",
            headers=_auth_header(zone_b_token),
        )
        assert resp.status_code == 404  # hidden behind 404 per Doc #6

    def test_patch_incident_status(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
    ) -> None:
        """PATCH /api/v1/incidents/{id}/status transitions status."""
        # Create
        payload = {
            "zone_id": "zone_east_concourse",
            "description": "Test status transition",
            "source": "VOLUNTEER_REPORTED",
        }
        create_resp = overridden_client.post(
            "/api/v1/incidents",
            json=payload,
            headers=_auth_header(volunteer_token_zone_a),
        )
        inc_id = create_resp.json()["incident_id"]

        # Transition to Triaged
        resp = overridden_client.patch(
            f"/api/v1/incidents/{inc_id}/status",
            json={"status": "Triaged"},
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "Triaged"

    def test_patch_incident_status_invalid(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
    ) -> None:
        """Invalid transition → 422."""
        # Create an incident first
        payload = {
            "zone_id": "zone_east_concourse",
            "description": "Test for invalid transition",
            "source": "VOLUNTEER_REPORTED",
        }
        create_resp = overridden_client.post(
            "/api/v1/incidents",
            json=payload,
            headers=_auth_header(volunteer_token_zone_a),
        )
        inc_id = create_resp.json()["incident_id"]
        # Try invalid transition: Reported -> Resolved (skipping Triaged, Dispatched, etc.)
        resp = overridden_client.patch(
            f"/api/v1/incidents/{inc_id}/status",
            json={"status": "Resolved"},
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert resp.status_code == 422  # Invalid transition

    def test_list_incidents(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
    ) -> None:
        """GET /api/v1/incidents returns paginated list."""
        resp = overridden_client.get(
            "/api/v1/incidents",
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "has_more" in data

    def test_dispatch_recommendation_endpoint(
        self,
        overridden_client: TestClient,
        volunteer_token_zone_a: str,
    ) -> None:
        """POST /api/v1/incidents/{id}/dispatch-recommendation returns recommendation."""
        # Create incident
        payload = {
            "zone_id": "zone_east_concourse",
            "description": "Queue backup at concession",
            "source": "VOLUNTEER_REPORTED",
        }
        create_resp = overridden_client.post(
            "/api/v1/incidents",
            json=payload,
            headers=_auth_header(volunteer_token_zone_a),
        )
        inc_id = create_resp.json()["incident_id"]

        resp = overridden_client.post(
            f"/api/v1/incidents/{inc_id}/dispatch-recommendation",
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "recommended_volunteers" in data or "fallback_used" in data
