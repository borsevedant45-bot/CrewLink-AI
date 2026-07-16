from uuid import uuid4

from backend.app.db.base import Base
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship


class KnowledgeBaseChunk(Base):
    __tablename__ = "knowledge_base_chunks"

    chunk_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    doc_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_base_documents.doc_id"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    section_heading: Mapped[str] = mapped_column(String(200), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)

    document = relationship("KnowledgeBaseDocument", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<KnowledgeBaseChunk {self.chunk_id} doc={self.doc_id} idx={self.chunk_index}>"
