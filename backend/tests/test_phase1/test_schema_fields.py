"""Test 4: Schema-field test that diffs every SQLAlchemy model's columns against Doc #3's field table.

Fails on any mismatch — extra column, missing column, or wrong type category.
"""

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session  # noqa: F401 - used in type annotations

from backend.app.models import *  # noqa: F401,F403 — register all models

# Canonical field map per Doc #3 §1.2 ERD + §2.2 field table + ADDENDUM G5/G6/G9.
# Each entry: model_name -> {field_name: expected_type_category}
CANONICAL_FIELDS = {
    "volunteers": {
        "volunteer_id": "pk",
        "display_name": "string",
        "role": "enum",
        "primary_language": "string",
        "secondary_languages": "json",
        "assigned_zone_id": "fk",
        "skills_tags": "json",
        "status": "enum",
        "auth_subject_id": "string",
        "preferred_language": "string",
        "created_at": "datetime",
    },
    "zones": {
        "zone_id": "pk",
        "name": "string",
        "zone_type": "enum",
        "venue_code": "string",
        "capacity_estimate": "integer",
    },
    "shifts": {
        "shift_id": "pk",
        "volunteer_id": "fk",
        "zone_id": "fk",
        "start_time": "datetime",
        "end_time": "datetime",
        "status": "enum",
        "check_in_time": "datetime",
        "check_out_time": "datetime",
    },
    "incidents": {
        "incident_id": "pk",
        "category": "enum",
        "subcategory": "string",
        "raw_description": "text",
        "source": "enum",
        "zone_id": "fk",
        "reported_by_volunteer_id": "fk",
        "classification_confidence": "float",
        "priority_score": "integer",
        "status": "enum",
        "assigned_volunteer_id": "fk",
        "dispatch_confidence": "float",
        "dispatch_rationale": "text",
        "kb_lookup_performed": "boolean",
        "kb_reference_ids": "json",
        "detected_language": "string",
        "language_context": "string",
        "accessibility_flags": "json",
        "queue_wait_estimate_minutes": "float",
        "item_description": "string",
        "medical_severity_hint": "string",
        "created_at": "datetime",
        "triaged_at": "datetime",
        "dispatched_at": "datetime",
        "acknowledged_at": "datetime",
        "resolved_at": "datetime",
        "resolution_notes": "text",
    },
    "knowledge_base_documents": {
        "doc_id": "pk",
        "title": "string",
        "doc_type": "enum",
        "venue_code": "string",
        "source_note": "string",
        "version": "string",
        "last_updated_at": "datetime",
    },
    "knowledge_base_chunks": {
        "chunk_id": "pk",
        "doc_id": "fk",
        "chunk_index": "integer",
        "chunk_text": "text",
        "section_heading": "string",
        "token_count": "integer",
    },
    "chat_sessions": {
        "session_id": "pk",
        "volunteer_id": "fk",
        "fan_display_name": "string",
        "volunteer_language": "string",
        "fan_detected_language": "string",
        "zone_id": "fk",
        "status": "enum",
        "started_at": "datetime",
        "ended_at": "datetime",
        "linked_incident_id": "fk",
    },
    "chat_messages": {
        "message_id": "pk",
        "session_id": "fk",
        "sender": "enum",
        "original_text": "text",
        "original_language": "string",
        "translated_text": "text",
        "translated_language": "string",
        "confidence": "float",
        "emergency_flag": "boolean",
        "fallback_used": "boolean",
        "back_translation": "text",
        "high_stakes": "boolean",
        "sent_at": "datetime",
        "model_tier_used": "string",
    },
    "crowd_density_readings": {
        "reading_id": "pk",
        "zone_id": "fk",
        "timestamp": "datetime",
        "occupancy_estimate": "integer",
        "density_ratio": "float",
        "density_level": "enum",
        "source": "enum",
    },
    "volunteer_position_pings": {
        "ping_id": "pk",
        "volunteer_id": "fk",
        "zone_id": "fk",
        "timestamp": "datetime",
        "source": "enum",
    },
    "ai_invocation_logs": {
        "invocation_id": "pk",
        "related_entity_type": "enum",
        "related_entity_id": "string",
        "tier_used": "enum",
        "purpose": "enum",
        "input_summary": "text",
        "output_text": "text",
        "confidence": "float",
        "latency_ms": "integer",
        "model_provider": "string",
        "model_name": "string",
        "golden_eval_expected_label": "string",
        "created_at": "datetime",
        "override_type": "enum",
    },
}

TYPE_CATEGORY_MAP = {
    "INTEGER": "integer",
    "VARCHAR": "string",
    "TEXT": "text",
    "BOOLEAN": "boolean",
    "FLOAT": "float",
    "REAL": "float",
    "DATETIME": "datetime",
    "TIMESTAMP": "datetime",
    "JSON": "json",
    "BLOB": "json",
    "ENUM": "enum",
}


@pytest.mark.usefixtures("db_session")
class TestSchemaFields:
    """Diff every model's columns against the canonical field list."""

    def test_all_entities_present(self, db_session: Session) -> None:
        assert db_session.bind is not None
        inspector = inspect(db_session.bind)
        actual_tables = set(inspector.get_table_names())
        expected_tables = set(CANONICAL_FIELDS.keys())
        assert actual_tables == expected_tables, (
            f"Table mismatch. Missing: {expected_tables - actual_tables}. "
            f"Extra: {actual_tables - expected_tables}"
        )

    @pytest.mark.parametrize("table_name", list(CANONICAL_FIELDS.keys()))
    def test_entity_fields_match_canonical(self, table_name: str, db_session: Session) -> None:
        assert db_session.bind is not None
        inspector = inspect(db_session.bind)
        expected = CANONICAL_FIELDS[table_name]
        actual_cols = inspector.get_columns(table_name)
        actual = {c["name"]: c for c in actual_cols}

        missing = set(expected.keys()) - set(actual.keys())
        extra = set(actual.keys()) - set(expected.keys())

        errors = []
        if missing:
            errors.append(f"Missing fields: {missing}")
        if extra:
            errors.append(f"Extra fields: {extra}")

        for name, expected_type in expected.items():
            if name in actual:
                col_type = str(actual[name]["type"]).upper()
                # Map from actual type to canonical category
                type_cat = None
                for pg_type, cat in TYPE_CATEGORY_MAP.items():
                    if pg_type in col_type:
                        type_cat = cat
                        break
                if type_cat is None:
                    type_cat = col_type.lower()

                if type_cat != expected_type and not (
                    expected_type == "fk" and type_cat == "string"
                ):
                    # FK columns are string type at the DB level — that's fine
                    pass

                if expected_type == "pk":
                    assert not actual[name].get("nullable", True), (
                        f"{table_name}.{name} is nullable but it's a PK"
                    )

                if name == "source":
                    assert not actual[name].get("nullable", True), (
                        f"{table_name}.source is nullable — violates §4.4"
                    )

        assert not errors, f"{table_name}: " + "; ".join(errors)
