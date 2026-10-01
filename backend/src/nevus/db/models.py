"""Persistent model. Identifiers are UUIDv7; timestamps are UTC; soft deletion uses deleted_at."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, Date, Float, ForeignKey, Index, Integer, String, Text, Uuid
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
LESION_TYPES = ("mole", "other")
LESION_STATUSES = ("active", "removed", "resolved")
SYMPTOMS = ("itching", "bleeding", "pain", "looks_different")
DEFAULT_INTERVAL_DAYS = 90


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
    card_line_mm: Mapped[float | None] = mapped_column(Float)
    """What the person measured on the printed card's 50 mm verification line; None = not verified."""
    email_reminders: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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


IMAGE_ROLES = ("overview", "close_up", "with_reference", "other")
IMAGE_MODALITIES = ("camera", "dermatoscope")
RENDITION_KINDS = ("full", "preview", "thumb")


class Image(Base):
    """A stored photograph: the scrubbed original (by content hash) and what little metadata survives."""

    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    person_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("persons.id", ondelete="CASCADE"), nullable=False)
    observation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("observations.id", ondelete="SET NULL"))
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="close_up")
    modality: Mapped[str] = mapped_column(String(16), nullable=False, default="camera")
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    orientation: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source_format: Mapped[str] = mapped_column(String(16), nullable=False)
    re_encoded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Denormalised from the latest quality analysis so lists need no join; the analysis row is the source.
    quality_flags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    quality_checked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    captured_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    captured_tz: Mapped[str | None] = mapped_column(String(64))
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    renditions: Mapped[list[Rendition]] = relationship(back_populates="image", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_images_person_id", "person_id"),
        Index("ix_images_sha256", "sha256"),
        Index("ix_images_observation_id", "observation_id"),
    )


class Rendition(Base):
    __tablename__ = "renditions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    image_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    image: Mapped[Image] = relationship(back_populates="renditions")

    __table_args__ = (Index("ix_renditions_image_id_kind", "image_id", "kind", unique=True),)


class Lesion(Base):
    """A tracked mark: where it is on the body map, what it is called, and how often to look at it.

    The location is a zone code plus a point normalised to the map's view box, tagged with the
    map version, so stored points keep their meaning if the artwork changes.
    """

    __tablename__ = "lesions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    person_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("persons.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False, default="mole")
    label: Mapped[str | None] = mapped_column(String(120))
    zone_code: Mapped[str] = mapped_column(String(8), nullable=False)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    body_map_version: Mapped[str] = mapped_column(String(32), nullable=False)
    first_noticed_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=DEFAULT_INTERVAL_DAYS)
    snoozed_until: Mapped[date | None] = mapped_column(Date)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    observations: Mapped[list[Observation]] = relationship(back_populates="lesion", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_lesions_person_id", "person_id"),)


class Observation(Base):
    """One dated look at a lesion: photographs, the person's own notes and symptom flags. Never interpreted."""

    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    lesion_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("lesions.id", ondelete="CASCADE"), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    captured_tz: Mapped[str | None] = mapped_column(String(64))
    captured_local_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    symptoms: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    quality_flags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    lesion: Mapped[Lesion] = relationship(back_populates="observations")
    images: Mapped[list[Image]] = relationship(
        primaryjoin="Observation.id == Image.observation_id", foreign_keys="Image.observation_id", viewonly=True
    )

    __table_args__ = (
        Index("ix_observations_lesion_id", "lesion_id"),
        Index("ix_observations_captured_at", "captured_at"),
    )


JOB_QUEUED = "queued"
JOB_RUNNING = "running"
JOB_DONE = "done"
JOB_FAILED = "failed"


class Job(Base):
    """A unit of background work, leased by a worker for a bounded time so a crash never loses it."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    dedupe_key: Mapped[str | None] = mapped_column(String(200), unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=JOB_QUEUED)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    run_after: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    lease_until: Mapped[datetime | None] = mapped_column(UTCDateTime)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    __table_args__ = (Index("ix_jobs_status_run_after", "status", "run_after"),)


class Analysis(Base):
    """One run of one analyzer version over one input. Never updated in place: a new version adds a row.

    `decision` is `automatic` for analyses whose output is used as is (quality checks, reference
    detection) and `pending` / `confirmed` / `rejected` for experimental proposals the person decides on.
    """

    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    analyzer: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    params_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    outputs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ok")
    error: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(16), nullable=False, default="automatic")
    decided_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    __table_args__ = (
        Index(
            "ux_analyses_identity",
            "target_type",
            "target_id",
            "analyzer",
            "version",
            "params_hash",
            "input_hash",
            unique=True,
        ),
        Index("ix_analyses_target", "target_type", "target_id"),
    )


SCALE_KINDS = ("card", "coin", "manual")
MEASUREMENT_METHODS = ("assisted", "manual")


class ScaleReference(Base):
    """How millimetres were obtained for one photo: the detected card, a coin, or a line of known length."""

    __tablename__ = "scale_references"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    image_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    reference_mm: Mapped[float | None] = mapped_column(Float)
    geometry: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    mm_per_px: Mapped[float] = mapped_column(Float, nullable=False)
    sigma_scale: Mapped[float] = mapped_column(Float, nullable=False)
    tilt_deg: Mapped[float | None] = mapped_column(Float)
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("analyses.id", ondelete="SET NULL"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    __table_args__ = (Index("ix_scale_references_image_id", "image_id"),)


class Measurement(Base):
    """A confirmed measurement of a lesion on one photo, with its uncertainty and its provenance."""

    __tablename__ = "measurements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    observation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("observations.id", ondelete="CASCADE"), nullable=False
    )
    lesion_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("lesions.id", ondelete="CASCADE"), nullable=False)
    image_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    scale_reference_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("scale_references.id", ondelete="RESTRICT"), nullable=False
    )
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    shape: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    longest_mm: Mapped[float] = mapped_column(Float, nullable=False)
    perpendicular_mm: Mapped[float] = mapped_column(Float, nullable=False)
    area_mm2: Mapped[float] = mapped_column(Float, nullable=False)
    sigma_longest_mm: Mapped[float] = mapped_column(Float, nullable=False)
    sigma_perpendicular_mm: Mapped[float] = mapped_column(Float, nullable=False)
    sigma_area_mm2: Mapped[float] = mapped_column(Float, nullable=False)
    tilt_deg: Mapped[float | None] = mapped_column(Float)
    flags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("analyses.id", ondelete="SET NULL"))
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    confirmed_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    __table_args__ = (
        Index("ix_measurements_lesion_id", "lesion_id"),
        Index("ix_measurements_observation_id", "observation_id"),
    )


class NotificationDelivery(Base):
    """One message sent (or attempted) on one channel for one occasion: the key makes it happen once."""

    __tablename__ = "notification_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    __table_args__ = (Index("ux_notification_deliveries_once", "user_id", "channel", "key", unique=True),)


WEBHOOK_PRESETS = ("generic", "home_assistant", "n8n", "ntfy", "gotify")


class Webhook(Base):
    """An administrator's outgoing webhook: the daily digest of the marks they follow, sent to a URL.

    It covers the persons its owner owns or manages, as the email digest does. The URL and the secret
    often carry credentials, so both are sealed; the interface shows only `url_hint`.
    """

    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    preset: Mapped[str] = mapped_column(String(16), nullable=False, default="generic")
    sealed_url: Mapped[str] = mapped_column(Text, nullable=False)
    url_hint: Mapped[str] = mapped_column(String(200), nullable=False)
    sealed_secret: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_status: Mapped[str | None] = mapped_column(String(16))
    last_error: Mapped[str | None] = mapped_column(String(200))
    last_sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    __table_args__ = (Index("ix_webhooks_user_id", "user_id"),)


class CalendarFeed(Base):
    """A secret calendar link for one person, made by one user; it stops when their access does.

    Only a hash of the token is kept: the link is shown once, and making a new one ends the old one.
    """

    __tablename__ = "calendar_feeds"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    person_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("persons.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    __table_args__ = (
        Index("ux_calendar_feeds_token_hash", "token_hash", unique=True),
        Index("ux_calendar_feeds_person_user", "person_id", "user_id", unique=True),
    )


class Export(Base):
    """An encrypted export being built or ready to download. The passphrase is sealed until the job uses it."""

    __tablename__ = "exports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    person_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("persons.id", ondelete="CASCADE"))
    requested_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    file_name: Mapped[str | None] = mapped_column(String(200))
    bytes: Mapped[int | None] = mapped_column(BigInteger)
    sealed_passphrase: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    __table_args__ = (Index("ix_exports_requested_by", "requested_by"),)


REPORT_SCOPES = ("lesion", "profile", "visit")


class Report(Base):
    """A PDF report of one mark or of a person's whole map, rendered in the background, kept until deleted.

    The PDF is a derived blob; `analyzer_versions` records which analyzers produced the numbers in it,
    so a report can always be traced back to the code that measured.
    """

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    person_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("persons.id", ondelete="CASCADE"), nullable=False)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    lesion_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    paper: Mapped[str] = mapped_column(String(8), nullable=False, default="a4")
    options: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    blob_sha256: Mapped[str | None] = mapped_column(String(64))
    bytes: Mapped[int | None] = mapped_column(BigInteger)
    pages: Mapped[int | None] = mapped_column(Integer)
    analyzer_versions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    __table_args__ = (Index("ix_reports_person_id", "person_id"),)


class Appointment(Base):
    """A planned visit to a clinician: the date to prepare for, a note, and the report made for it."""

    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid7)
    person_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("persons.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    report_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("reports.id", ondelete="SET NULL"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (Index("ix_appointments_person_id_date", "person_id", "date"),)
