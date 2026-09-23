"""Persistent model. Identifiers are UUIDv7; timestamps are UTC; soft deletion uses deleted_at."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nevus.db.base import Base
from nevus.db.types import UTCDateTime, utcnow
from nevus.ids import uuid7

ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"
ACCESS_OWNER = "owner"
ACCESS_MANAGER = "manager"
ACCESS_VIEWER = "viewer"
ACCESS_ROLES = (ACCESS_OWNER, ACCESS_MANAGER, ACCESS_VIEWER)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(254))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default=ROLE_MEMBER)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    theme: Mapped[str] = mapped_column(String(8), nullable=False, default="system")
    show_uncertainty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    disabled_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    sessions: Mapped[list[AuthSession]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    @property
    def is_active(self) -> bool:
        return self.disabled_at is None


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    sudo_until: Mapped[datetime | None] = mapped_column(UTCDateTime)
    user_agent: Mapped[str | None] = mapped_column(String(255))
    ip: Mapped[str | None] = mapped_column(String(45))

    user: Mapped[User] = relationship(back_populates="sessions")

    __table_args__ = (Index("ix_auth_sessions_user_id", "user_id"),)


class Person(Base):
    """Somebody whose skin marks are tracked. Not necessarily a user."""

    __tablename__ = "persons"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    birth_year: Mapped[int | None] = mapped_column(Integer)
    skin_tone: Mapped[str | None] = mapped_column(String(16))
    owner_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    experimental_analysis: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    access: Mapped[list[PersonAccess]] = relationship(back_populates="person", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_persons_owner_user_id", "owner_user_id"),)


class PersonAccess(Base):
    __tablename__ = "person_access"

    person_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("persons.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    person: Mapped[Person] = relationship(back_populates="access")

    __table_args__ = (Index("ix_person_access_user_id", "user_id"),)


class AuditLog(Base):
    """Who did what to which record. Identifiers only, never content."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(32))
    target_id: Mapped[str | None] = mapped_column(String(36))
    ip: Mapped[str | None] = mapped_column(String(45))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    __table_args__ = (Index("ix_audit_log_at", "at"),)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict[str, Any] | list[Any] | str | int | bool | None] = mapped_column(JSON)
    encrypted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow)
