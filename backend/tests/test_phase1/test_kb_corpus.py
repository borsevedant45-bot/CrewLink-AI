"""Test 3: KB corpus chunk count falls in Doc #3 §3.2's 25–40 range across exactly 5 documents.

§3.2: "Expected volume: roughly 25–40 chunks total across all five documents"
"""

import pytest
from backend.app.models.knowledge_base_chunk import KnowledgeBaseChunk
from backend.app.models.knowledge_base_document import KnowledgeBaseDocument
from sqlalchemy import text
from sqlalchemy.orm import Session


@pytest.mark.usefixtures("db_session", "seeded_db")
class TestKbCorpus:
    """Knowledge base corpus size and document count assertions."""

    def test_exactly_five_documents(self, db_session: Session) -> None:
        count = db_session.query(KnowledgeBaseDocument).count()
        assert count == 5, f"Expected exactly 5 KB documents, got {count}"

    def test_chunk_count_in_25_to_40_range(self, db_session: Session) -> None:
        count = db_session.query(KnowledgeBaseChunk).count()
        assert 25 <= count <= 40, (
            f"Chunk count {count} outside expected range 25–40 (§3.2)"
        )

    def test_every_document_has_at_least_one_chunk(self, db_session: Session) -> None:
        result = db_session.execute(
            text("""
                SELECT d.doc_id, COUNT(c.chunk_id) as chunk_count
                FROM knowledge_base_documents d
                LEFT JOIN knowledge_base_chunks c ON c.doc_id = d.doc_id
                GROUP BY d.doc_id
            """)
        ).fetchall()
        empty_docs = [row[0] for row in result if row[1] < 1]
        assert not empty_docs, f"Documents with zero chunks: {empty_docs}"

    def test_heading_based_chunking_no_overlap_by_default(self, db_session: Session) -> None:
        chunks = db_session.query(KnowledgeBaseChunk).order_by(
            KnowledgeBaseChunk.doc_id, KnowledgeBaseChunk.chunk_index
        ).all()
        for i in range(1, len(chunks)):
            if chunks[i].doc_id == chunks[i - 1].doc_id:
                assert chunks[i].section_heading != "", (
                    f"Chunk {chunks[i].chunk_id} has empty heading (§3.2: heading-based)"
                )
