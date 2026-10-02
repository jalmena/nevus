"""Uploading photographs and serving them to the people allowed to see them."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from nevus.auth import service
from nevus.auth.dependencies import AppSettings, CurrentUser, DbSession, client_ip
from nevus.config import Settings
from nevus.cv.pipeline import enqueue_analyses, refresh_observation_flags
from nevus.db.models import (
    ACCESS_MANAGER,
    ACCESS_OWNER,
    IMAGE_MODALITIES,
    IMAGE_ROLES,
    Image,
    Person,
    PersonAccess,
    Rendition,
    User,
)
from nevus.db.types import utcnow
from nevus.storage.blobs import BlobStore, InsufficientStorageError
from nevus.storage.renditions import make_renditions
from nevus.storage.scrub import UnsupportedImageError, scrub

router = APIRouter(prefix="/api", tags=["images"])

ImageRole = Literal["overview", "close_up", "with_reference", "other"]
Modality = Literal["camera", "dermatoscope"]
RenditionKind = Literal["original", "full", "preview", "thumb"]
IMMUTABLE_PRIVATE = "private, max-age=31536000, immutable"


class RenditionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: str
    width: int
    height: int
    bytes: int


class ImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    person_id: uuid.UUID
    observation_id: uuid.UUID | None
    role: str
    modality: str
    sha256: str
    bytes: int
    mime: str
    width: int
    height: int
    orientation: int
    source_format: str
    re_encoded: bool
    quality_flags: list[str]
    quality_checked_at: datetime | None
    captured_at: datetime | None
    created_at: datetime
    renditions: list[RenditionOut]


def _store(request: Request) -> BlobStore:
    store: BlobStore = request.app.state.blob_store
    return store


def _person_for(db: Session, person_id: uuid.UUID, user: User, *roles: str) -> Person:
    person = db.get(Person, person_id)
    access = db.get(PersonAccess, (person_id, user.id)) if person else None
    if person is None or person.deleted_at is not None or access is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such person.")
    if roles and access.role not in roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your access to this person does not allow that.")
    return person


async def ingest_upload(
    request: Request,
    user: User,
    db: Session,
    settings: Settings,
    person_id: uuid.UUID,
    file: UploadFile,
    role: str,
    modality: str,
    captured_at: datetime | None,
    captured_tz: str | None,
    observation_id: uuid.UUID | None = None,
    fallback_captured_at: datetime | None = None,
    image_id: uuid.UUID | None = None,
) -> Image:
    """Scrub, store and describe one uploaded photograph. Access to the person is checked by the caller.

    The capture time is the explicit value if given, else what the photo itself says, else the fallback
    (an observation's visit time), else nothing.
    """
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "The photo is larger than the upload limit.")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The upload is empty.")
    try:
        scrubbed = scrub(data)
    except UnsupportedImageError as error:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(error)) from error
    if scrubbed.width * scrubbed.height > settings.max_upload_pixels:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "The photo has more pixels than the limit.")
    store = _store(request)
    try:
        digest = store.put(scrubbed.data)
        renditions = make_renditions(scrubbed.data, scrubbed.orientation)
        stored = [(r, store.put(r.data, derived=True)) for r in renditions]
    except InsufficientStorageError as error:
        raise HTTPException(status.HTTP_507_INSUFFICIENT_STORAGE, "The data volume is nearly full.") from error
    when = captured_at or scrubbed.captured_at or fallback_captured_at
    image = Image(
        **({"id": image_id} if image_id else {}),
        person_id=person_id,
        observation_id=observation_id,
        role=role,
        modality=modality,
        sha256=digest,
        bytes=len(scrubbed.data),
        mime=scrubbed.mime,
        width=scrubbed.width,
        height=scrubbed.height,
        orientation=scrubbed.orientation,
        source_format=scrubbed.source_format,
        re_encoded=scrubbed.re_encoded,
        captured_at=when.astimezone() if when and when.tzinfo else when,
        captured_tz=captured_tz,
        created_by=user.id,
    )
    db.add(image)
    db.flush()
    for rendition, rendition_digest in stored:
        db.add(
            Rendition(
                image_id=image.id,
                kind=rendition.kind,
                sha256=rendition_digest,
                bytes=len(rendition.data),
                mime=rendition.mime,
                width=rendition.width,
                height=rendition.height,
            )
        )
    db.flush()
    db.refresh(image)
    enqueue_analyses(db, image)
    details = {"person": str(person_id)}
    if observation_id:
        details["observation"] = str(observation_id)
    service.audit(db, "image.upload", user, "image", image.id, client_ip(request, settings), details)
    return image


@router.post("/persons/{person_id}/images", response_model=ImageOut, status_code=status.HTTP_201_CREATED)
async def upload_image(
    person_id: uuid.UUID,
    request: Request,
    user: CurrentUser,
    db: DbSession,
    settings: AppSettings,
    file: Annotated[UploadFile, File()],
    role: Annotated[ImageRole, Form()] = "close_up",
    modality: Annotated[Modality, Form()] = "camera",
    captured_at: Annotated[datetime | None, Form()] = None,
    captured_tz: Annotated[str | None, Form(max_length=64)] = None,
) -> ImageOut:
    """A photograph of the person not tied to an observation (an overview, for example)."""
    _person_for(db, person_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    image = await ingest_upload(request, user, db, settings, person_id, file, role, modality, captured_at, captured_tz)
    return ImageOut.model_validate(image)


@router.get("/persons/{person_id}/images", response_model=list[ImageOut])
def list_images(person_id: uuid.UUID, user: CurrentUser, db: DbSession) -> list[ImageOut]:
    _person_for(db, person_id, user)
    rows = db.scalars(
        select(Image).where(Image.person_id == person_id, Image.deleted_at.is_(None)).order_by(Image.created_at.desc())
    )
    return [ImageOut.model_validate(i) for i in rows]


def _image_for(db: Session, image_id: uuid.UUID, user: User, *roles: str) -> Image:
    image = db.get(Image, image_id)
    if image is None or image.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such image.")
    _person_for(db, image.person_id, user, *roles)
    return image


@router.get("/images/{image_id}", response_model=ImageOut)
def get_image(image_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ImageOut:
    return ImageOut.model_validate(_image_for(db, image_id, user))


@router.get("/images/{image_id}/{kind}", response_class=FileResponse)
def image_file(
    image_id: uuid.UUID, kind: RenditionKind, request: Request, user: CurrentUser, db: DbSession
) -> Response:
    """The bytes, only for people who may see the person; cacheable forever because the content is addressed by hash."""
    image = _image_for(db, image_id, user)
    store = _store(request)
    if kind == "original":
        digest, mime = image.sha256, image.mime
        path = store.path(digest)
    else:
        rendition = next((r for r in image.renditions if r.kind == kind), None)
        if rendition is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No such rendition.")
        digest, mime = rendition.sha256, rendition.mime
        path = store.path(digest, derived=True)
    if request.headers.get("if-none-match") == f'"{digest}"':
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "The file is missing from the store.")
    return FileResponse(
        path,
        media_type=mime,
        headers={"Cache-Control": IMMUTABLE_PRIVATE, "ETag": f'"{digest}"', "Content-Disposition": "inline"},
    )


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    image_id: uuid.UUID, request: Request, user: CurrentUser, db: DbSession, settings: AppSettings
) -> Response:
    """Moves the image to the trash; the purge and the garbage collection of blobs arrive with data management."""
    image = _image_for(db, image_id, user, ACCESS_OWNER, ACCESS_MANAGER)
    image.deleted_at = utcnow()
    db.flush()
    if image.observation_id is not None:
        refresh_observation_flags(db, image.observation_id)
    service.audit(db, "image.delete", user, "image", image.id, client_ip(request, settings))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["IMAGE_MODALITIES", "IMAGE_ROLES", "ImageOut", "ImageRole", "Modality", "ingest_upload", "router"]
