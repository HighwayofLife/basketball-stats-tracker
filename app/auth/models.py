"""Authentication models for user management."""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy import Enum as SQLEnum

from app.data_access.models import Base


class UserRole(str, Enum):
    """User role enumeration."""

    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime)

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}', role='{self.role}')>"
