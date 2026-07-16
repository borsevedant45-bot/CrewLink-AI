"""Create initial schema for all 11 entities.

Revision ID: 001
Revises:
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "zones",
        sa.Column("zone_id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("zone_type", sa.String(30), nullable=False),
        sa.Column("venue_code", sa.String(50), nullable=False),
        sa.Column("capacity_estimate", sa.Integer, nullable=False),
    )

    op.create_table(
        "volunteers",
        sa.Column("volunteer_id", sa.String(36), primary_key=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("primary_language", sa.String(50), nullable=False),
        sa.Column("secondary_languages", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("assigned_zone_id", sa.String(36), sa.ForeignKey("zones.zone_id"), nullable=False),
        sa.Column("skills_tags", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(20), nullable=False, server_default="OFF_SHIFT"),
        sa.Column("auth_subject_id", sa.String(200), nullable=False),
        sa.Column("preferred_language", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "knowledge_base_documents",
        sa.Column("doc_id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("doc_type", sa.String(30), nullable=False),
        sa.Column("venue_code", sa.String(50), nullable=False),
        sa.Column("source_note", sa.String(500), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "incidents",
        sa.Column("incident_id", sa.String(36), primary_key=True),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("subcategory", sa.String(200), nullable=True),
        sa.Column("raw_description", sa.Text, nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("zone_id", sa.String(36), sa.ForeignKey("zones.zone_id"), nullable=False),
        sa.Column("reported_by_volunteer_id", sa.String(36), sa.ForeignKey("volunteers.volunteer_id"), nullable=True),
        sa.Column("classification_confidence", sa.Float, nullable=True),
        sa.Column("priority_score", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="Reported"),
        sa.Column("assigned_volunteer_id", sa.String(36), sa.ForeignKey("volunteers.volunteer_id"), nullable=True),
        sa.Column("dispatch_confidence", sa.Float, nullable=True),
        sa.Column("dispatch_rationale", sa.Text, nullable=True),
        sa.Column("kb_lookup_performed", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("kb_reference_ids", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("detected_language", sa.String(50), nullable=True),
        sa.Column("language_context", sa.String(50), nullable=True),
        sa.Column("accessibility_flags", sa.JSON, nullable=True),
        sa.Column("queue_wait_estimate_minutes", sa.Float, nullable=True),
        sa.Column("item_description", sa.String(500), nullable=True),
        sa.Column("medical_severity_hint", sa.String(10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("triaged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text, nullable=True),
    )

    op.create_table(
        "shifts",
        sa.Column("shift_id", sa.String(36), primary_key=True),
        sa.Column("volunteer_id", sa.String(36), sa.ForeignKey("volunteers.volunteer_id"), nullable=False),
        sa.Column("zone_id", sa.String(36), sa.ForeignKey("zones.zone_id"), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="SCHEDULED"),
        sa.Column("check_in_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_out_time", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "chat_sessions",
        sa.Column("session_id", sa.String(36), primary_key=True),
        sa.Column("volunteer_id", sa.String(36), sa.ForeignKey("volunteers.volunteer_id"), nullable=False),
        sa.Column("fan_display_name", sa.String(200), nullable=False),
        sa.Column("volunteer_language", sa.String(50), nullable=False),
        sa.Column("fan_detected_language", sa.String(50), nullable=False),
        sa.Column("zone_id", sa.String(36), sa.ForeignKey("zones.zone_id"), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="ACTIVE"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("linked_incident_id", sa.String(36),
                  sa.ForeignKey("incidents.incident_id"), nullable=True, unique=True),
    )

    op.create_table(
        "chat_messages",
        sa.Column("message_id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("chat_sessions.session_id"), nullable=False),
        sa.Column("sender", sa.String(10), nullable=False),
        sa.Column("original_text", sa.Text, nullable=False),
        sa.Column("original_language", sa.String(50), nullable=False),
        sa.Column("translated_text", sa.Text, nullable=False),
        sa.Column("translated_language", sa.String(50), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_tier_used", sa.String(20), nullable=False),
    )

    op.create_table(
        "knowledge_base_chunks",
        sa.Column("chunk_id", sa.String(36), primary_key=True),
        sa.Column("doc_id", sa.String(36), sa.ForeignKey("knowledge_base_documents.doc_id"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("section_heading", sa.String(200), nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False),
    )

    op.create_table(
        "crowd_density_readings",
        sa.Column("reading_id", sa.String(36), primary_key=True),
        sa.Column("zone_id", sa.String(36), sa.ForeignKey("zones.zone_id"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("occupancy_estimate", sa.Integer, nullable=False),
        sa.Column("density_ratio", sa.Float, nullable=False),
        sa.Column("density_level", sa.String(10), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
    )

    op.create_table(
        "volunteer_position_pings",
        sa.Column("ping_id", sa.String(36), primary_key=True),
        sa.Column("volunteer_id", sa.String(36), sa.ForeignKey("volunteers.volunteer_id"), nullable=False),
        sa.Column("zone_id", sa.String(36), sa.ForeignKey("zones.zone_id"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
    )

    op.create_table(
        "ai_invocation_logs",
        sa.Column("invocation_id", sa.String(36), primary_key=True),
        sa.Column("related_entity_type", sa.String(15), nullable=False),
        sa.Column("related_entity_id", sa.String(36), nullable=True),
        sa.Column("tier_used", sa.String(15), nullable=False),
        sa.Column("purpose", sa.String(30), nullable=False),
        sa.Column("input_summary", sa.Text, nullable=False),
        sa.Column("output_text", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=False),
        sa.Column("model_provider", sa.String(100), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("golden_eval_expected_label", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ai_invocation_logs")
    op.drop_table("volunteer_position_pings")
    op.drop_table("crowd_density_readings")
    op.drop_table("knowledge_base_chunks")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("shifts")
    op.drop_table("incidents")
    op.drop_table("knowledge_base_documents")
    op.drop_table("volunteers")
    op.drop_table("zones")
