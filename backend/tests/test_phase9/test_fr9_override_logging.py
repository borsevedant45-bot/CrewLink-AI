"""Doc #7 §4 — FR-9: override logging to AIInvocationLog.

Tests FR-9: "Log every triage decision and override — who, what, when,
model output vs. human choice — for the golden-set eval (Doc #7)."
(Doc #1 §5.2 FR-9)

Per G15: manual overrides write ``AIInvocationLog`` rows with
``override_type=HUMAN_RECLASSIFICATION`` or ``HUMAN_REASSIGNMENT`` and
``confidence=null``, distinguishing them from AI model outputs.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.ai_invocation_log import AIInvocationLog
from tests.test_orchestration.stub_provider import StubProvider


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestFR9OverrideLogging:
    """FR-9: manual overrides are logged with distinguishing markers."""

    def test_manual_status_change_logs_human_reclassification(
        self,
        overridden_client: TestClient,
        db_session: Session,
        volunteer_token_zone_a: str,
        fast_cheap_provider: StubProvider,
    ) -> None:
        """PATCH /incidents/{id}/status → AIInvocationLog with override_type=HUMAN_RECLASSIFICATION."""
        fast_cheap_provider._result = {
            "category": "general",
            "severity_signal": "low",
            "confidence": 0.9,
            "reasoning_summary": "Test override logging.",
            "requires_emergency_escalation": False,
        }
        create_resp = overridden_client.post(
            "/api/v1/incidents",
            json={"zone_id": "zone_east_concourse", "description": "FR-9 override test"},
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert create_resp.status_code == 201
        incident_id = create_resp.json()["incident_id"]

        # Trigger a manual status change
        status_resp = overridden_client.patch(
            f"/api/v1/incidents/{incident_id}/status",
            json={"status": "Triaged"},
            headers=_auth_header(volunteer_token_zone_a),
        )
        assert status_resp.status_code == 200

        # Query the log table for the override row
        stmt = select(AIInvocationLog).where(
            AIInvocationLog.related_entity_id == incident_id,
            AIInvocationLog.override_type == "HUMAN_RECLASSIFICATION",
        ).order_by(AIInvocationLog.created_at.desc()).limit(1)
        row = db_session.execute(stmt).scalar_one_or_none()

        assert row is not None, "No override log row found for status change"
        assert row.override_type == "HUMAN_RECLASSIFICATION"
        assert row.confidence is None, "Manual override must have confidence=null"
        assert row.purpose == "CLASSIFICATION"
        assert "Triaged" in row.output_text, f"Output should mention target status, got: {row.output_text}"

    def test_manual_assign_logs_human_reassignment(
        self,
        overridden_client: TestClient,
        db_session: Session,
        supervisor_token: str,
        fast_cheap_provider: StubProvider,
    ) -> None:
        """PATCH /incidents/{id}/assign → AIInvocationLog with override_type=HUMAN_REASSIGNMENT."""
        fast_cheap_provider._result = {
            "category": "general",
            "severity_signal": "low",
            "confidence": 0.9,
            "reasoning_summary": "Test assign override logging.",
            "requires_emergency_escalation": False,
        }
        create_resp = overridden_client.post(
            "/api/v1/incidents",
            json={
                "zone_id": "zone_east_concourse",
                "description": "FR-9 assign override test",
                "reported_by_volunteer_id": "vol_maria_alvarez",
            },
            headers=_auth_header(supervisor_token),
        )
        assert create_resp.status_code == 201
        incident_id = create_resp.json()["incident_id"]

        assign_resp = overridden_client.patch(
            f"/api/v1/incidents/{incident_id}/assign",
            json={"volunteer_id": "vol_maria_alvarez"},
            headers=_auth_header(supervisor_token),
        )
        assert assign_resp.status_code == 200

        stmt = select(AIInvocationLog).where(
            AIInvocationLog.related_entity_id == incident_id,
            AIInvocationLog.override_type == "HUMAN_REASSIGNMENT",
        ).order_by(AIInvocationLog.created_at.desc()).limit(1)
        row = db_session.execute(stmt).scalar_one_or_none()

        assert row is not None, "No override log row found for assign"
        assert row.override_type == "HUMAN_REASSIGNMENT"
        assert row.confidence is None, "Manual override must have confidence=null"
        assert row.purpose == "DISPATCH_RECOMMENDATION"
        assert "vol_maria_alvarez" in row.output_text, (
            f"Output should mention volunteer, got: {row.output_text}"
        )
