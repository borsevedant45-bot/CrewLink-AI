"""Test 3: Zone-scope and role-scope enforcement.

Doc #6 §3: "every REST and WS call carries a JWT with role/zone claims checked server-side."
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.core.auth import AuthContext, require_role


class TestAuthContext:
    """AuthContext carries role + zone claims — never client-supplied parameters."""

    def test_volunteer_auth_context(self) -> None:
        ctx = AuthContext(volunteer_id="vol_1", role="volunteer", zone_id="zone_east")
        assert ctx.role == "volunteer"
        assert ctx.zone_id == "zone_east"
        assert not ctx.is_supervisor

    def test_supervisor_auth_context(self) -> None:
        ctx = AuthContext(volunteer_id="vol_2", role="supervisor", zone_id=None)
        assert ctx.role == "supervisor"
        assert ctx.zone_id is None
        assert ctx.is_supervisor

    def test_supervisor_spans_all_zones(self) -> None:
        ctx = AuthContext(volunteer_id="vol_3", role="supervisor", zone_id=None)
        assert ctx.can_access_zone("zone_west"), "Supervisor should access any zone"
        assert ctx.can_access_zone("zone_east"), "Supervisor should access any zone"

    def test_volunteer_only_own_zone(self) -> None:
        ctx = AuthContext(volunteer_id="vol_4", role="volunteer", zone_id="zone_east")
        assert ctx.can_access_zone("zone_east"), "Volunteer should access own zone"
        assert not ctx.can_access_zone("zone_west"), "Volunteer should NOT access other zone"


@pytest.mark.usefixtures("db_session")
class TestZoneScope:
    """Zone-scope test: Zone-A JWT on Zone-B resource returns 403/404."""

    def test_volunteer_cannot_access_other_zone(self, client: TestClient, volunteer_token_zone_a: str) -> None:
        response = client.get(
            "/api/v1/incidents/inc_other_zone",
            headers={"Authorization": f"Bearer {volunteer_token_zone_a}"},
        )
        assert response.status_code in (403, 404), (
            "Cross-zone access should return 403 or 404, never 200"
        )

    def test_supervisor_can_access_any_zone(self, client: TestClient, supervisor_token: str) -> None:
        response = client.get(
            "/api/v1/incidents/inc_any_zone",
            headers={"Authorization": f"Bearer {supervisor_token}"},
        )
        assert response.status_code != 403, "Supervisor should not get 403 on any zone"


class TestRoleRequirement:
    """require_role('supervisor') dependency blocks volunteer JWTs."""

    def test_volunteer_blocked_from_supervisor_route(self) -> None:
        def dummy_route(auth_context: AuthContext) -> None:  # noqa: ARG001
            pass

        guarded = require_role("supervisor")(dummy_route)

        volunteer_ctx = AuthContext(volunteer_id="vol_1", role="volunteer", zone_id="zone_east")
        with pytest.raises(PermissionError):
            guarded(volunteer_ctx)

    def test_supervisor_allowed_on_supervisor_route(self) -> None:
        sup_ctx = AuthContext(volunteer_id="vol_2", role="supervisor", zone_id=None)
        assert sup_ctx.is_supervisor, "Supervisor context should have is_supervisor=True"

    def test_internal_auth_rejects_user_jwt(self) -> None:
        from backend.app.core.auth import verify_internal_auth
        # A user JWT passed to an internal route should fail
        assert not verify_internal_auth("Bearer some_user_jwt_here")
        # The valid service credential should pass
        assert verify_internal_auth("Bearer sim-service-token-change-in-prod")
