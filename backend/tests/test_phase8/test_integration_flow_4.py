"""Doc #7 §4 — Integration flow #4: Ask CrewLink full stack.

Tests the full HTTP-to-service pipeline:
1. POST /api/v1/knowledge-base/ask with a facility question
   → 200 with grounded answer (facility branch, with retrieval)
2. POST /api/v1/knowledge-base/ask with an out-of-scope question
   → 200 with grounded=false and fallback_message
3. POST /api/v1/knowledge-base/ask when retrieval returns nothing
   → 200 with grounded=false and fallback (no 503)
4. POST /api/v1/knowledge-base/ask with auth failure
   → 401

Uses the same dependency-override pattern as Phase 6/7 integration tests.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from tests.test_orchestration.stub_provider import StubProvider


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestAskCrewLinkIntegration:
    """Doc #7 §4 — Integration flow #4: full stack."""

    def test_facility_question_returns_grounded_answer(
        self,
        overridden_client: TestClient,
        fast_cheap_provider: StubProvider,
        reasoning_provider: StubProvider,
        volunteer_token_zone_a: str,
        mock_retrieved_chunks: list[dict[str, Any]],
    ) -> None:
        """POST /knowledge-base/ask with facility question → grounded answer."""

        # Arrange: intent router returns facility
        fast_cheap_provider._result = {
            "intent": "facility_safety_procedure",
            "confidence": 0.95,
            "detected_language": "en",
        }

        # Arrange: synthesis returns grounded answer
        reasoning_provider._result = {
            "answer": "Accessible restrooms are on the East Concourse near Gate 4.",
            "grounded": True,
            "sources": ["abc123_chunk_east_concourse"],
        }

        # Act: POST to the endpoint with patched retrieval
        with patch(
            "backend.app.services.ask_crewlink.retrieve_chunks",
            AsyncMock(return_value=mock_retrieved_chunks),
        ):
            resp = overridden_client.post(
                "/api/v1/knowledge-base/ask",
                json={"question": "Where is the nearest accessible restroom to the East Concourse?"},
                headers=_auth_header(volunteer_token_zone_a),
            )

        # Assert
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["grounded"] is True, f"Expected grounded=true, got {data}"
        assert data["answer"] is not None, "Answer should not be null"
        assert len(data["sources"]) > 0, "Should have sources"
        assert data.get("fallback_message") is None, "No fallback for successful query"
        # Verify source structure
        first_source = data["sources"][0]
        assert "chunk_id" in first_source, "Source should have chunk_id"
        assert "document_id" in first_source, "Source should have document_id"

    def test_out_of_scope_returns_fallback(
        self,
        overridden_client: TestClient,
        fast_cheap_provider: StubProvider,
        volunteer_token_zone_a: str,
    ) -> None:
        """POST /knowledge-base/ask with out-of-scope question → fallback."""

        # Arrange: intent router returns out_of_scope
        fast_cheap_provider._result = {
            "intent": "out_of_scope",
            "confidence": 0.85,
            "detected_language": "en",
        }

        # Act
        resp = overridden_client.post(
            "/api/v1/knowledge-base/ask",
            json={"question": "What's the score of the match?"},
            headers=_auth_header(volunteer_token_zone_a),
        )

        # Assert
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["grounded"] is False, "Out-of-scope should not be grounded"
        assert data["answer"] is None, "Answer should be null for out-of-scope"
        assert data.get("fallback_message") is not None, (
            "Should have fallback_message for out-of-scope"
        )

    def test_retrieval_empty_returns_fallback(
        self,
        overridden_client: TestClient,
        fast_cheap_provider: StubProvider,
        volunteer_token_zone_a: str,
    ) -> None:
        """POST /knowledge-base/ask with empty retrieval → fallback, not 503."""

        # Arrange: intent router returns facility
        fast_cheap_provider._result = {
            "intent": "facility_safety_procedure",
            "confidence": 0.95,
            "detected_language": "en",
        }

        # Act: return no chunks from retrieval
        with patch(
            "backend.app.services.ask_crewlink.retrieve_chunks",
            AsyncMock(return_value=[]),
        ):
            resp = overridden_client.post(
                "/api/v1/knowledge-base/ask",
                json={"question": "Where is Gate 4?"},
                headers=_auth_header(volunteer_token_zone_a),
            )

        # Assert: 200 with grounded=false, never 503
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["grounded"] is False, "Should not be grounded when retrieval is empty"
        assert data["answer"] is None, "Answer should be null"
        assert data.get("fallback_message") is not None, (
            "Should have fallback_message when retrieval is empty"
        )
        # Verify that no reasoning tier was used — no sources
        assert len(data.get("sources", [])) == 0, "No sources when retrieval is empty"

    def test_unauthenticated_request_returns_401(
        self,
        overridden_client: TestClient,
    ) -> None:
        """POST /knowledge-base/ask without auth → 401."""
        resp = overridden_client.post(
            "/api/v1/knowledge-base/ask",
            json={"question": "Where is Gate 4?"},
        )
        assert resp.status_code == 401, (
            f"Expected 401, got {resp.status_code}: {resp.text}"
        )
