from typing import Optional, List
from sqlalchemy import String, Text, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class APHSourceDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "aph_source_documents"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    edition: Mapped[str] = mapped_column(String(50), default="2026-27", nullable=False, index=True)
    official_reference_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    total_chapters: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_clauses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    clauses: Mapped[List["APHClause"]] = relationship(
        "APHClause", back_populates="source_document", cascade="all, delete-orphan", lazy="selectin"
    )


class APHClause(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "aph_clauses"

    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("aph_source_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    chapter_title: Mapped[str] = mapped_column(String(200), nullable=False)
    clause_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    clause_title: Mapped[str] = mapped_column(String(200), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    norm_category: Mapped[str] = mapped_column(String(50), default="GENERAL", nullable=False, index=True)
    embedding_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON-serialized vector for hybrid search

    source_document: Mapped["APHSourceDocument"] = relationship("APHSourceDocument", back_populates="clauses")


class APHAssistantQuery(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "aph_assistant_queries"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    institution_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    retrieval_mode: Mapped[str] = mapped_column(String(50), default="HYBRID_SEMANTIC", nullable=False)
    is_automated_advisory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    uncertainty_warning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1 (useful) or -1 (not useful)
