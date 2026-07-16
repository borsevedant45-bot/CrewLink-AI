from datetime import UTC, datetime
from uuid import uuid4

from backend.app.db.base import Base
from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class KnowledgeBaseDocument(Base):
    __tablename__ = "knowledge_base_documents"

    doc_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    doc_type: Mapped[str] = mapped_column(
        Enum(
            "VENUE_MAP", "SAFETY_PROCEDURE", "ACCESSIBILITY_FACILITIES", "FAQ",
            name="doc_type_enum", create_constraint=True,
        ),
        nullable=False,
    )
    venue_code: Mapped[str] = mapped_column(String(50), nullable=False)
    source_note: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(UTC),
    )

    chunks = relationship("KnowledgeBaseChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<KnowledgeBaseDocument {self.doc_id} {self.title}>"
