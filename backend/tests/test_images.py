"""Uploading photographs: metadata scrubbing, content addressing, renditions, access and limits."""

from __future__ import annotations

import io
import struct
import zlib

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from PIL.TiffImagePlugin import IFDRational

from nevus.storage.scrub import scrub, strip_jpeg, strip_png
from tests.test_accounts import ADMIN, MEMBER, claim


def jpeg_with_metadata(orientation: int = 6, size: tuple[int, int] = (640, 480)) -> bytes:
    """A JPEG carrying capture time, orientation, GPS and a comment, like a phone would produce."""
    image = Image.new("RGB", size, (200, 120, 90))
    exif = Image.Exif()
    exif[0x0112] = orientation
    exif[0x0132] = "2026:09:12 10:41:07"
    exif[0x010F] = "PhoneMaker"
    exif[0x0110] = "Phone 12"
    ifd = exif.get_ifd(0x8769)
    ifd[0x9003] = "2026:09:12 10:41:07"
    gps = exif.get_ifd(0x8825)
    gps[0x0001] = "N"
    gps[0x0002] = (IFDRational(40, 1), IFDRational(25, 1), IFDRational(0, 1))
    gps[0x0003] = "W"
    gps[0x0004] = (IFDRational(3, 1), IFDRational(42, 1), IFDRational(0, 1))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90, exif=exif.tobytes(), comment=b"private comment")
    return buffer.getvalue()


def png_with_text(size: tuple[int, int] = (300, 200)) -> bytes:
    image = Image.new("RGB", size, (10, 20, 30))
    buffer = io.BytesIO()
    from PIL import PngImagePlugin

    meta = PngImagePlugin.PngInfo()
    meta.add_text("Author", "somebody")
    meta.add_text("Comment", "private")
    image.save(buffer, format="PNG", pnginfo=meta)
    return buffer.getvalue()


def test_jpeg_scrubbing_removes_metadata_and_keeps_the_scan_bytes() -> None:
    original = jpeg_with_metadata()
    result = scrub(original)
    assert result.mime == "image/jpeg" and result.source_format == "JPEG" and not result.re_encoded
    assert result.orientation == 6
    assert result.captured_at is not None and result.captured_at.isoformat().startswith("2026-09-12T10:41:07")
    cleaned = result.data
    assert b"Exif" not in cleaned and b"PhoneMaker" not in cleaned and b"private comment" not in cleaned
    # the compressed image data is byte-identical: pixels untouched
    assert original[original.index(b"\xff\xda") :] == cleaned[cleaned.index(b"\xff\xda") :]
    with Image.open(io.BytesIO(cleaned)) as image:
        assert image.size == (640, 480)
        assert dict(image.getexif()) == {}


def test_png_scrubbing_drops_text_chunks_and_keeps_pixels() -> None:
    original = png_with_text()
    cleaned = strip_png(original)
    assert b"somebody" not in cleaned and b"private" not in cleaned
    with Image.open(io.BytesIO(original)) as a, Image.open(io.BytesIO(cleaned)) as b:
        assert list(a.getdata()) == list(b.getdata())


def test_non_images_are_rejected() -> None:
    with pytest.raises(Exception, match="not a readable image"):
        scrub(b"definitely not an image")
    with pytest.raises(Exception, match="Not a JPEG"):
        strip_jpeg(b"\x89PNG")


def test_upload_stores_scrubbed_original_and_renditions_with_orientation_applied(client: TestClient) -> None:
    claim(client)
    person_id = client.post("/api/persons", json={"display_name": "Ana"}).json()["id"]
    response = client.post(
        f"/api/persons/{person_id}/images",
        files={"file": ("IMG_0001.JPG", jpeg_with_metadata(orientation=6), "image/jpeg")},
        data={"role": "with_reference", "modality": "camera", "captured_tz": "Europe/Madrid"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role"] == "with_reference" and body["orientation"] == 6 and body["source_format"] == "JPEG"
    assert body["captured_at"].startswith("2026-09-12T10:41:07")
    kinds = {r["kind"]: (r["width"], r["height"]) for r in body["renditions"]}
    assert set(kinds) == {"full", "preview", "thumb"}
    assert kinds["full"] == (480, 640)  # orientation 6 rotates the 640x480 source upright
    assert kinds["thumb"] == (192, 256)

    thumb = client.get(f"/api/images/{body['id']}/thumb")
    assert thumb.status_code == 200 and thumb.headers["content-type"] == "image/jpeg"
    assert thumb.headers["cache-control"] == "private, max-age=31536000, immutable"
    with Image.open(io.BytesIO(thumb.content)) as image:
        assert image.size == (192, 256) and dict(image.getexif()) == {}
    etag = thumb.headers["etag"]
    assert client.get(f"/api/images/{body['id']}/thumb", headers={"if-none-match": etag}).status_code == 304

    original = client.get(f"/api/images/{body['id']}/original")
    assert original.status_code == 200 and b"Exif" not in original.content
    assert client.get(f"/api/persons/{person_id}/images").json()[0]["id"] == body["id"]


def test_identical_uploads_share_one_blob(client: TestClient, settings) -> None:  # type: ignore[no-untyped-def]
    claim(client)
    person_id = client.post("/api/persons", json={"display_name": "Ana"}).json()["id"]
    payload = jpeg_with_metadata(orientation=1)
    first = client.post(f"/api/persons/{person_id}/images", files={"file": ("a.jpg", payload, "image/jpeg")}).json()
    second = client.post(f"/api/persons/{person_id}/images", files={"file": ("b.jpg", payload, "image/jpeg")}).json()
    assert first["id"] != second["id"] and first["sha256"] == second["sha256"]
    originals = list((settings.blobs_dir / "originals").rglob("*"))
    assert len([p for p in originals if p.is_file()]) == 1


def test_access_rules_apply_to_images(client: TestClient) -> None:
    claim(client)
    assert client.post("/api/users", json=MEMBER).status_code == 201
    member = TestClient(client.app, base_url="http://localhost")
    member.post("/api/auth/login", json=MEMBER)
    person_id = client.post("/api/persons", json={"display_name": "Ana"}).json()["id"]
    image_id = client.post(
        f"/api/persons/{person_id}/images", files={"file": ("a.jpg", jpeg_with_metadata(), "image/jpeg")}
    ).json()["id"]
    # not shared: invisible
    assert member.get(f"/api/images/{image_id}/thumb").status_code == 404
    assert (
        member.post(
            f"/api/persons/{person_id}/images", files={"file": ("a.jpg", jpeg_with_metadata(), "image/jpeg")}
        ).status_code
        == 404
    )
    # viewer: may look, may not upload or delete
    client.put(f"/api/persons/{person_id}/access", json={"username": "ana", "role": "viewer"})
    assert member.get(f"/api/images/{image_id}/thumb").status_code == 200
    assert (
        member.post(
            f"/api/persons/{person_id}/images", files={"file": ("a.jpg", jpeg_with_metadata(), "image/jpeg")}
        ).status_code
        == 403
    )
    assert member.delete(f"/api/images/{image_id}").status_code == 403
    # manager: may upload and delete
    client.put(f"/api/persons/{person_id}/access", json={"username": "ana", "role": "manager"})
    assert (
        member.post(
            f"/api/persons/{person_id}/images", files={"file": ("a.jpg", jpeg_with_metadata(), "image/jpeg")}
        ).status_code
        == 201
    )
    assert member.delete(f"/api/images/{image_id}").status_code == 204
    assert client.get(f"/api/images/{image_id}").status_code == 404
    assert client.get("/api/auth/session").json()["user"]["username"] == ADMIN["username"].lower()


def test_limits_and_unsupported_files(client: TestClient, settings) -> None:  # type: ignore[no-untyped-def]
    claim(client)
    person_id = client.post("/api/persons", json={"display_name": "Ana"}).json()["id"]
    assert (
        client.post(f"/api/persons/{person_id}/images", files={"file": ("a.txt", b"hello", "text/plain")}).status_code
        == 415
    )
    huge = jpeg_with_metadata(orientation=1, size=(6000, 4100))  # 24.6 megapixels
    assert (
        client.post(f"/api/persons/{person_id}/images", files={"file": ("a.jpg", huge, "image/jpeg")}).status_code
        == 413
    )
    assert (
        client.post(f"/api/persons/{person_id}/images", files={"file": ("a.jpg", b"", "image/jpeg")}).status_code == 400
    )


def test_low_disk_space_refuses_uploads(client: TestClient) -> None:
    claim(client)
    person_id = client.post("/api/persons", json={"display_name": "Ana"}).json()["id"]
    client.app.state.blob_store.min_free_bytes = 10**18  # more than any disk has
    assert (
        client.post(
            f"/api/persons/{person_id}/images", files={"file": ("a.jpg", jpeg_with_metadata(), "image/jpeg")}
        ).status_code
        == 507
    )


def test_png_chunk_parser_stops_at_iend_and_keeps_critical_chunks() -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", b"\x00" * 13)
        + chunk(b"tEXt", b"k\x00v")
        + chunk(b"IDAT", b"x")
        + chunk(b"IEND", b"")
    )
    cleaned = strip_png(raw)
    assert b"tEXt" not in cleaned and b"IHDR" in cleaned and cleaned.endswith(chunk(b"IEND", b""))
