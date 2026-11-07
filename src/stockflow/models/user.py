"""User model with strict database constraints and RBAC roles."""

from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from stockflow.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(StrEnum):
    """Supported Role-Based Access Control (RBAC) roles."""

    ADMIN = "admin"
    CUSTOMER = "customer"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Application user account."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'customer')",
            name="valid_user_role",
        ),
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(32),
        default=UserRole.CUSTOMER.value,
        server_default=UserRole.CUSTOMER.value,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )
