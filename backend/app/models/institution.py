from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.application import Application


class Institution(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "institutions"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    institution_type: Mapped[str] = mapped_column(String(100), nullable=False)
    established_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="institution", cascade="all, delete-orphan")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="institution", cascade="all, delete-orphan")
