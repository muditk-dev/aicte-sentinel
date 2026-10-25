from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.application import Application


class WorkflowTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workflow_templates"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    versions: Mapped[List["WorkflowVersion"]] = relationship(
        "WorkflowVersion", back_populates="template", cascade="all, delete-orphan", lazy="selectin"
    )
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="template")


class WorkflowVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workflow_versions"

    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    aph_edition: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "APH 2026-27"
    
    # Serialized JSON state machine & statutory criteria
    state_machine_json: Mapped[str] = mapped_column(Text, nullable=False)
    checklist_rules_json: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Maker-Checker verification
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    proposed_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    approved_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    approval_timestamp: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    template: Mapped[WorkflowTemplate] = relationship("WorkflowTemplate", back_populates="versions")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="version")
