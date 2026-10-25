from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, BigInteger, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.institution import Institution
    from app.models.user import User


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "documents"

    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    uploaded_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Security & Antivirus States: UPLOADED -> QUARANTINED -> SCANNING -> ACCEPTED or REJECTED
    scan_status: Mapped[str] = mapped_column(String(50), default="QUARANTINED", nullable=False, index=True)
    scan_result_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scan_timestamp: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Regulatory Scrutiny Status: PENDING, ACCEPTED, DEFICIENT, REQUIRES_MANUAL_VERIFICATION
    verification_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    versions: Mapped[List["DocumentVersion"]] = relationship(
        "DocumentVersion", back_populates="document", cascade="all, delete-orphan", order_by="DocumentVersion.version_number.desc()"
    )
    scrutiny_findings: Mapped[List["ScrutinyFinding"]] = relationship(
        "ScrutinyFinding", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document_versions"

    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    scan_status: Mapped[str] = mapped_column(String(50), nullable=False)

    document: Mapped["Document"] = relationship("Document", back_populates="versions")


class ScrutinyFinding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "scrutiny_findings"

    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    officer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # ACCEPTED, DEFICIENT, REQUIRES_MANUAL_VERIFICATION
    finding_status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_advisory_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    document: Mapped[Optional["Document"]] = relationship("Document", back_populates="scrutiny_findings")
