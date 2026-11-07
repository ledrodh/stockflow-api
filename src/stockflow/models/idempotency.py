"""PostgreSQL-backed IdempotencyKey model for atomic request deduplication."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from stockflow.db.base import Base, UUIDPrimaryKeyMixin


class IdempotencyStatus(StrEnum):
    """Execution state of an idempotent operation."""

    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class IdempotencyKey(UUIDPrimaryKeyMixin, Base):
    """Persistent idempotency record scoped per user and key."""

    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_idempotency_user_key"),
        CheckConstraint(
            "status IN ('PROCESSING', 'COMPLETED', 'FAILED')",
            name="valid_idempotency_status",
        ),
        Index("ix_idempotency_keys_expires_at", "expires_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    request_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=IdempotencyStatus.PROCESSING.value,
        server_default=IdempotencyStatus.PROCESSING.value,
        nullable=False,
    )
    response_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    response_body: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
