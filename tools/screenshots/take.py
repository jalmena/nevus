# /// script
# requires-python = ">=3.13"
# dependencies = ["playwright>=1.47", "pillow>=11", "httpx>=0.27"]
# ///
# SPDX-License-Identifier: AGPL-3.0-only
"""Take the store screenshots from a real, seeded instance at phone size.

Starts the backend on a scratch data directory (serving the built frontend), seeds a person with marks and
visits through the API, signs in with the session cookie and photographs the three main pages in light and
dark themes. Run `pnpm build` in frontend/ first; `python -m playwright install chromium` once.

Usage: uv run tools/screenshots/take.py [--out docs/design/screenshots]
"""

from __future__ import annotations

import argparse
import io
import os
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFilter
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
PORT = 8791
BASE = f"http://127.0.0.1:{PORT}"
VIEWPORT = {"width": 390, "height": 844}


def skin_photo(seed: int, spot: tuple[int, int] = (600, 450), radius: int = 70) -> bytes:
    """A plausible close-up: warm skin tone with grain and one soft, slightly irregular dark spot."""
    rng = random.Random(seed)
    width, height = 1200, 900
    base = Image.new("RGB", (width, height), (222, 182, 156))
    noise = Image.effect_noise((width, height), 18).convert("L")
    grain = Image.merge("RGB", (noise, noise, noise)).point(lambda v: int(v * 0.25))
    base = Image.blend(base, Image.composite(base, grain, noise), 0.35)
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx, cy = spot
    for step in range(6):
        r = radius - step * 9 + rng.randint(-4, 4)
        dx, dy = rng.randint(-6, 6), rng.randint(-6, 6)
        colour = (92 - step * 6, 58 - step * 4, 44 - step * 3, 150)
        draw.ellipse((cx - r + dx, cy - r * 0.85 + dy, cx + r + dx, cy + r * 0.85 + dy), fill=colour)
    layer = layer.filter(ImageFilter.GaussianBlur(4))
    base = Image.alpha_composite(base.convert("RGBA"), layer).convert("RGB")
    buffer = io.BytesIO()
    base.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


def wait_healthy(client: httpx.Client) -> None:
    for _ in range(120):
        try:
            if client.get(f"{BASE}/healthz").status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise SystemExit("backend did not start")


def seed(client: httpx.Client) -> dict[str, str]:
    headers = {"sec-fetch-site": "same-origin"}
    r = client.post(f"{BASE}/api/auth/claim", json={"username": "Jose", "password": "correct horse battery"}, headers=headers)
    r.raise_for_status()
    client.patch(f"{BASE}/api/auth/me", json={"language": "en"}, headers=headers)
    person = client.post(f"{BASE}/api/persons", json={"display_name": "Ana"}, headers=headers).json()
    pid = person["id"]
    marks = [
        ("Chest, near the sternum", "1250", 0.42, 0.26, "2025-11-03", 90),
        ("Left forearm", "1751", 0.72, 0.36, "2026-02-14", 180),
        ("Right shoulder blade", "2251", 0.56, 0.24, "2026-05-20", 90),
    ]
    ids: list[str] = []
    for label, zone, x, y, noticed, interval in marks:
        lesion = client.post(
            f"{BASE}/api/persons/{pid}/lesions",
            json={"label": label, "location": {"zone": zone, "x": x, "y": y}, "first_noticed_on": noticed, "status": "active", "interval_days": interval},
            headers=headers,
        ).json()
        ids.append(lesion["id"])
    visits = [
        (ids[0], "2026-03-08T10:12:00+01:00", "Same as last time, as far as I can tell.", [], 1),
        (ids[0], "2026-06-14T18:40:00+02:00", "Edge looks a little more irregular to me.", ["looks_different"], 2),
        (ids[0], "2026-09-20T09:05:00+02:00", None, [], 3),
        (ids[1], "2026-08-02T11:30:00+02:00", "Itched for a few days after the beach.", ["itching"], 4),
    ]
    first_observation = None
    for lesion_id, when, notes, symptoms, seed_no in visits:
        observation = client.post(
            f"{BASE}/api/lesions/{lesion_id}/observations",
            json={"captured_at": when, "captured_tz": "Europe/Madrid", "notes": notes, "symptoms": symptoms},
            headers=headers,
        ).json()
        first_observation = first_observation or observation["id"]
        for role, spot in (("close_up", (600, 450)), ("with_reference", (520, 470))):
            client.post(
                f"{BASE}/api/observations/{observation['id']}/images",
                files={"file": (f"photo-{seed_no}.jpg", skin_photo(seed_no * 7 + len(role), spot), "image/jpeg")},
                data={"role": role, "captured_at": when, "captured_tz": "Europe/Madrid"},
                headers=headers,
            ).raise_for_status()
    return {"person": pid, "lesion": ids[0], "observation": str(first_observation)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "design" / "screenshots")
    args = parser.parse_args()
    if not (ROOT / "frontend" / "dist" / "index.html").exists():
        raise SystemExit("frontend/dist is missing: run pnpm build in frontend/ first")
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "NEVUS_DATA_DIR": tmp, "NEVUS_ALLOWED_HOSTS": "localhost", "NEVUS_PORT": str(PORT), "NEVUS_LOG_LEVEL": "warning"}
        server = subprocess.Popen(["uv", "run", "nevus", "serve"], cwd=ROOT / "backend", env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            with httpx.Client(timeout=30) as client:
                wait_healthy(client)
                ids = seed(client)
                cookie = client.cookies.get("nevus_session")
            assert cookie
            pages = [
                ("person", f"/persons/{ids['person']}"),
                ("mark", f"/lesions/{ids['lesion']}"),
                ("visit", f"/observations/{ids['observation']}"),
            ]
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                for scheme in ("light", "dark"):
                    context = browser.new_context(viewport=VIEWPORT, device_scale_factor=2, color_scheme=scheme, locale="en-GB")
                    context.add_cookies([{"name": "nevus_session", "value": cookie, "url": BASE}])
                    page = context.new_page()
                    for name, path in pages:
                        page.goto(f"{BASE}{path}", wait_until="networkidle")
                        page.evaluate("document.fonts.ready")
                        page.wait_for_timeout(300)
                        target = args.out / f"{name}-{scheme}.png"
                        page.screenshot(path=str(target), full_page=False)
                        print("wrote", target.relative_to(ROOT))
                    context.close()
                browser.close()
        finally:
            server.terminate()
            server.wait(timeout=10)


if __name__ == "__main__":
    sys.exit(main())
