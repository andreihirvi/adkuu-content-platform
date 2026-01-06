"""
User model with role-based access control.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import Mapped
import enum

from app.db.base_class import Base


class UserRole(str, enum.Enum):
    """User role enum."""
    ADMIN = "admin"
    USER = "user"


class User(Base):
    """
    User model for authentication and authorization.

    Supports role-based access:
    - ADMIN: Can manage users, full platform access
    - USER: Standard platform access
    """

    __tablename__ = "users"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    email: Mapped[str] = Column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = Column(String(255), nullable=False)
    password_hash: Mapped[str] = Column(String(255), nullable=False)

    # Role-based access
    role: Mapped[str] = Column(
        String(50),
        default=UserRole.USER.value,
        nullable=False,
        index=True
    )

    # Account status
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    last_login_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN.value
