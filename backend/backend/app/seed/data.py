"""Seed script for Founders Field demo data.

Idempotent — safe to re-run. Creates zones, volunteer roster (Maria Alvarez),
KB documents + chunks, and seeds Chroma.
"""

import json
from datetime import UTC, datetime

from backend.app.db.base import Base
from backend.app.seed.chroma_seed import get_seed_documents, seed_chroma
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

VENUE_CODE = "founders_field"


def _now() -> datetime:
    return datetime.now(UTC)


ZONES_DATA = [
    {"zone_id": "zone_east_concourse", "name": "East Concourse", "zone_type": "CONCOURSE", "capacity_estimate": 8500},
    {"zone_id": "zone_west_concourse", "name": "West Concourse", "zone_type": "CONCOURSE", "capacity_estimate": 8500},
    {"zone_id": "zone_north_concourse", "name": "North Concourse", "zone_type": "CONCOURSE", "capacity_estimate": 6000},
    {"zone_id": "zone_south_concourse", "name": "South Concourse", "zone_type": "CONCOURSE", "capacity_estimate": 6000},
    {"zone_id": "zone_gate_1", "name": "Gate 1 — Main Lobby", "zone_type": "GATE", "capacity_estimate": 3000},
    {"zone_id": "zone_gate_4", "name": "Gate 4 — East Entry", "zone_type": "GATE", "capacity_estimate": 2000},
    {"zone_id": "zone_gate_7", "name": "Gate 7 — West Entry", "zone_type": "GATE", "capacity_estimate": 2000},
    {"zone_id": "zone_gate_10", "name": "Gate 10 — South Entry", "zone_type": "GATE", "capacity_estimate": 1500},
    {"zone_id": "zone_med_east", "name": "Medical Station East",
     "zone_type": "MEDICAL_STATION", "capacity_estimate": 50},
    {"zone_id": "zone_med_west", "name": "Medical Station West",
     "zone_type": "MEDICAL_STATION", "capacity_estimate": 50},
    {"zone_id": "zone_gs_east", "name": "Guest Services East",
     "zone_type": "GUEST_SERVICES", "capacity_estimate": 100},
    {"zone_id": "zone_gs_west", "name": "Guest Services West",
     "zone_type": "GUEST_SERVICES", "capacity_estimate": 100},
    {"zone_id": "zone_seating_100", "name": "Seating Block 100–120 East",
     "zone_type": "SEATING_BLOCK", "capacity_estimate": 12000},
    {"zone_id": "zone_seating_200", "name": "Seating Block 200–220 North",
     "zone_type": "SEATING_BLOCK", "capacity_estimate": 8000},
]


VOLUNTEERS_DATA = [
    {
        "volunteer_id": "vol_maria_alvarez",
        "display_name": "Maria Alvarez",
        "role": "VOLUNTEER",
        "primary_language": "en",
        "secondary_languages": ["es"],
        "assigned_zone_id": "zone_east_concourse",
        "skills_tags": ["translation_es", "accessibility_trained", "wheelchair_cart_trained"],
        "status": "AVAILABLE",
        "auth_subject_id": "mocked_auth_maria_alvarez",
        "preferred_language": "en",
    },
    {
        "volunteer_id": "vol_john_chen",
        "display_name": "John Chen",
        "role": "VOLUNTEER",
        "primary_language": "en",
        "secondary_languages": ["zh", "es"],
        "assigned_zone_id": "zone_west_concourse",
        "skills_tags": ["translation_zh", "translation_es"],
        "status": "AVAILABLE",
        "auth_subject_id": "mocked_auth_john_chen",
        "preferred_language": "en",
    },
    {
        "volunteer_id": "vol_amina_walker",
        "display_name": "Amina Walker",
        "role": "VOLUNTEER",
        "primary_language": "en",
        "secondary_languages": ["fr", "ar"],
        "assigned_zone_id": "zone_north_concourse",
        "skills_tags": ["translation_fr", "translation_ar", "medical_basic"],
        "status": "AVAILABLE",
        "auth_subject_id": "mocked_auth_amina_walker",
        "preferred_language": "en",
    },
    {
        "volunteer_id": "vol_carlos_rodriguez",
        "display_name": "Carlos Rodriguez",
        "role": "VOLUNTEER",
        "primary_language": "es",
        "secondary_languages": ["en", "pt"],
        "assigned_zone_id": "zone_south_concourse",
        "skills_tags": ["medical_certified", "sign_language"],
        "status": "AVAILABLE",
        "auth_subject_id": "mocked_auth_carlos_rodriguez",
        "preferred_language": "es",
    },
    {
        "volunteer_id": "vol_devon_price",
        "display_name": "Devon Price",
        "role": "SUPERVISOR",
        "primary_language": "en",
        "secondary_languages": [],
        "assigned_zone_id": "zone_east_concourse",
        "skills_tags": ["supervisor"],
        "status": "AVAILABLE",
        "auth_subject_id": "mocked_auth_devon_price",
        "preferred_language": "en",
    },
]


def run_seed(connection: Connection) -> None:
    """Idempotent seed. Clears existing data, recreates tables, seeds fresh data."""

    Base.metadata.create_all(bind=connection)

    for table in reversed(Base.metadata.sorted_tables):
        connection.execute(text(f"DELETE FROM {table.name}"))

    for zone_data in ZONES_DATA:
        connection.execute(
            text("""
                INSERT OR REPLACE INTO zones (zone_id, name, zone_type, venue_code, capacity_estimate)
                VALUES (:zone_id, :name, :zone_type, :venue_code, :capacity_estimate)
            """),
            {"venue_code": VENUE_CODE, **zone_data},
        )

    for vol_data in VOLUNTEERS_DATA:
        connection.execute(
            text("""
                INSERT OR REPLACE INTO volunteers (volunteer_id, display_name, role, primary_language,
                    secondary_languages, assigned_zone_id, skills_tags, status,
                    auth_subject_id, preferred_language, created_at)
                VALUES (:volunteer_id, :display_name, :role, :primary_language,
                    :secondary_languages, :assigned_zone_id, :skills_tags, :status,
                    :auth_subject_id, :preferred_language, :created_at)
            """),
            {
                "created_at": _now(),
                "secondary_languages": json.dumps(vol_data["secondary_languages"]),
                "skills_tags": json.dumps(vol_data["skills_tags"]),
                **{k: v for k, v in vol_data.items() if k not in ("secondary_languages", "skills_tags")},
            },
        )

    seed_documents = get_seed_documents()
    for doc in seed_documents:
        doc_id = f"kbdoc_{doc['title'].lower().replace(' ', '_').replace('&', 'and')}"
        connection.execute(
            text("""
                INSERT OR REPLACE INTO knowledge_base_documents (doc_id, title, doc_type, venue_code,
                    source_note, version, last_updated_at)
                VALUES (:doc_id, :title, :doc_type, :venue_code, :source_note, :version, :last_updated_at)
            """),
            {
                "doc_id": doc_id,
                "title": doc["title"],
                "doc_type": doc["doc_type"],
                "venue_code": VENUE_CODE,
                "source_note": "Authored for the CrewLink AI demo; not derived from any real venue's operations manual",
                "version": "1.0",
                "last_updated_at": _now(),
            },
        )

        for idx, chunk in enumerate(doc["sections"]):
            chunk_id = f"kbchunk_{doc_id}_{idx}"
            connection.execute(
                text("""
                    INSERT OR REPLACE INTO knowledge_base_chunks (chunk_id, doc_id, chunk_index, chunk_text,
                        section_heading, token_count)
                    VALUES (:chunk_id, :doc_id, :chunk_index, :chunk_text,
                        :section_heading, :token_count)
                """),
                {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "chunk_index": idx,
                    "chunk_text": chunk["text"],
                    "section_heading": chunk["heading"],
                    "token_count": chunk["token_count"],
                },
            )

    connection.commit()


def seed_all(db: Session) -> None:
    run_seed(db.connection())
    seed_chroma()
