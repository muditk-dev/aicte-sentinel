from typing import Optional
from sqlalchemy import String, Integer, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin, TimestampMixin


class AuditEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "audit_events"

    # Monotonic sequence for cryptographic chaining
    sequence_number: Mapped[int] = mapped_column(Integer, autoincrement=True, unique=True, index=True)
    actor_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Client Metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Cryptographic Chain Hashes
    previous_entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    details_json: Mapped[Optional[str]] = mapped_column(Text, default="{}", nullable=True)


class MerkleRoot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "merkle_roots"

    batch_start_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    batch_end_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    merkle_root_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    total_events: Mapped[int] = mapped_column(Integer, nullable=False)
    signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
