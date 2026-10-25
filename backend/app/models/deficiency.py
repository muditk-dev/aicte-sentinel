from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.institution import Institution
    from app.models.user import User


class DeficiencyNotice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "deficiency_notices"

    notice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    issuing_officer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Lifecycle: DRAFT -> ISSUED -> RESPONSE_SUBMITTED -> UNDER_REVIEW -> RESOLVED (or REOPENED)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False, index=True)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    officer_remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    items: Mapped[List["DeficiencyItem"]] = relationship(
        "DeficiencyItem", back_populates="notice", cascade="all, delete-orphan", lazy="selectin"
    )
    responses: Mapped[List["DeficiencyResponse"]] = relationship(
        "DeficiencyResponse", back_populates="notice", cascade="all, delete-orphan", order_by="DeficiencyResponse.created_at.desc()", lazy="selectin"
    )


class DeficiencyItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "deficiency_items"

    notice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("deficiency_notices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    requirement_title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_corrective_action: Mapped[str] = mapped_column(Text, nullable=False)
    item_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)

    notice: Mapped["DeficiencyNotice"] = relationship("DeficiencyNotice", back_populates="items")


class DeficiencyResponse(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "deficiency_responses"

    notice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("deficiency_notices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    submitted_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    response_remarks: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON array of referenced replacement documents/IDs
    attachments_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    notice: Mapped["DeficiencyNotice"] = relationship("DeficiencyNotice", back_populates="responses")


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notifications"

    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    institution_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="SYSTEM", nullable=False, index=True)
    link_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    delivery_status: Mapped[str] = mapped_column(String(50), default="DELIVERED", nullable=False)
    # Deduplication key to prevent duplicate notifications during periodic worker runs
    dedup_key: Mapped[Optional[str]] = mapped_column(String(150), unique=True, nullable=True, index=True)
