# SPDX-License-Identifier: AGPL-3.0-only
"""Turning report data into a PDF/A-3 document, in a worker process.

Templates only lay out: every number and date is formatted here, in the report's language. The page
can load nothing but its own stylesheet, fonts and wordmark and the photos chosen for it, never the
network, whatever a note might contain (notes are escaped anyway).
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from jinja2 import Environment, FileSystemLoader, select_autoescape

from nevus.reports import svg
from nevus.reports.i18n import Words
from nevus.reports.tokens import COLOURS

HERE = Path(__file__).resolve().parent
BAR_STEPS_MM = (1, 2, 5, 10, 20, 50)
CHECK_FLAGS = ("blurry", "too_dark", "too_bright", "glare", "low_resolution", "tilted", "card_small")
MEASUREMENT_FLAGS = ("tilted", "unverified_card", "tilt_unknown")
SYMPTOMS = ("itching", "bleeding", "pain", "looks_different")
ROLES = ("close_up", "with_reference", "overview", "other")


def css_string(text: str) -> str:
    """A CSS string literal for user text placed inside a stylesheet (page footers)."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("<", "\\3C ")
    return f'"{escaped}"'


def _fetcher(allowed: set[Path]) -> Any:
    from weasyprint.urls import URLFetcher

    class OnlyTheseFiles(URLFetcher):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__(allowed_protocols=("file",), allow_redirects=False)

        def fetch(self, url: str, headers: dict[str, str] | None = None) -> Any:
            parsed = urlparse(url)
            path = Path(unquote(parsed.path)).resolve()
            inside_package = path.is_relative_to(HERE / "assets") or path.is_relative_to(HERE / "fonts")
            if parsed.scheme != "file" or not (inside_package or path in allowed):
                raise ValueError(f"reports load only their own files, not {url!r}")
            return super().fetch(path.as_uri(), headers)

    return OnlyTheseFiles()


def _local(value: str | None, zone: ZoneInfo) -> datetime | None:
    return datetime.fromisoformat(value).astimezone(zone) if value else None


def _short(words: Words, value: datetime | None) -> str:
    return words.short_day(value) if value else "—"


def _bar(photo: dict[str, Any]) -> dict[str, Any] | None:
    """A round length near a quarter of the photo's width, as a percentage of it."""
    if not photo.get("mm_per_px"):
        return None
    width_mm = photo["upright_width"] * float(photo["mm_per_px"])
    fitting = [mm for mm in BAR_STEPS_MM if mm <= 0.3 * width_mm]
    if not fitting:
        return None
    return {"mm": fitting[-1], "percent": round(fitting[-1] / width_mm * 100, 2)}


def _outline(photo: dict[str, Any]) -> dict[str, Any] | None:
    shape = photo.get("shape")
    if not shape:
        return None
    if shape.get("type") == "circle":
        cx, cy, r = float(shape["cx"]), float(shape["cy"]), float(shape["r"])
        points = [(cx + r * math.cos(a / 48 * 2 * math.pi), cy + r * math.sin(a / 48 * 2 * math.pi)) for a in range(48)]
    else:
        points = [(float(x), float(y)) for x, y in shape.get("points", [])]
    if len(points) < 3:
        return None
    # The figure is about 160 pt wide: strokes of about 1.3 pt and a white halo, whatever the photo's size.
    unit = photo["upright_width"] / 160
    return {
        "points": " ".join(f"{x:.1f},{y:.1f}" for x, y in points),
        "stroke": round(1.3 * unit, 1),
        "halo": round(3.2 * unit, 1),
    }


def _shape_words(described: dict[str, Any] | None, words: Words) -> str | None:
    if not described:
        return None
    shape = described["shape"]
    return words(
        "shape_values", compactness=words.number(shape["compactness"], 2), aspect=words.number(shape["aspect"], 2)
    )


def _colour_words(described: dict[str, Any] | None, words: Words) -> str | None:
    colour = (described or {}).get("colour")
    if not colour:
        return None
    reference = words("colour_card") if colour["reference"] == "card_grey" else words("colour_camera")
    return words(
        "colour_values",
        lightness=words.number(colour["mark"]["L"], 0),
        skin=words.number(colour["skin"]["L"], 0),
        contrast=words.number(colour["contrast"], 0),
        reference=reference,
    )


def _measurement_row(m: dict[str, Any], words: Words, zone: ZoneInfo) -> dict[str, Any]:
    at = _local(m["captured_at"], zone)
    change = m.get("change")
    return {
        "date": words.day(at),
        "longest": words.mm(m["longest_mm"], m["sigma_longest_mm"]),
        "across": words.mm(m["perpendicular_mm"], m["sigma_perpendicular_mm"]),
        "area": words.area(m["area_mm2"], m["sigma_area_mm2"]),
        "scale": words(f"scale_{m['scale_kind']}") if m.get("scale_kind") in ("card", "coin", "manual") else "",
        "shape": _shape_words(m.get("descriptors"), words),
        "colour": _colour_words(m.get("descriptors"), words),
        "tilt": "" if m.get("tilt_deg") is None else f"{words.number(m['tilt_deg'], 0)}°",
        "change": None
        if change is None
        else {
            "value": words.mm(change["delta_mm"], change["sigma_mm"], sign=True),
            "verdict": words("measured_change") if change["detectable"] else words("no_detectable_change"),
            "detectable": change["detectable"],
        },
        "flags": [words(f"flag_{f}") for f in m.get("flags", []) if f in MEASUREMENT_FLAGS],
    }


def _title(lesion: dict[str, Any], words: Words) -> str:
    return str(lesion["label"] or words.zone(lesion["zone"]))


def _due_state(lesion: dict[str, Any], words: Words, zone: ZoneInfo, today: date) -> str:
    if lesion["status"] != "active" or not lesion["next_due_on"]:
        return words("not_followed")
    next_on = date.fromisoformat(lesion["next_due_on"])
    if lesion.get("snoozed_until") and date.fromisoformat(lesion["snoozed_until"]) >= today:
        return f"{words.short_day(next_on)} · {words('snoozed')}"
    if lesion["due"]:
        return f"{words.short_day(next_on)} · {words('overdue') if next_on < today else words('due_now')}"
    return words.short_day(next_on)


def context(payload: dict[str, Any]) -> dict[str, Any]:
    words = Words(payload["language"])
    try:
        zone = ZoneInfo(payload.get("timezone") or "UTC")
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("UTC")
    generated = datetime.fromisoformat(payload["generated_at"]).astimezone(zone)
    person = payload["person"]
    lesions = []
    for lesion in payload["lesions"]:
        measurements = lesion["measurements"]
        points = [
            svg.Point(datetime.fromisoformat(m["captured_at"]), m["longest_mm"], m["sigma_longest_mm"])
            for m in measurements
        ]
        visits = []
        for visit in lesion["visits"]:
            measured = next((m for m in measurements if m["observation_id"] == visit["id"]), None)
            photos = [
                {
                    "src": Path(photo["path"]).as_uri(),
                    "role": photo["role"],
                    "ratio": round(photo["upright_height"] / photo["upright_width"] * 100, 3),
                    "width": photo["upright_width"],
                    "height": photo["upright_height"],
                    "bar": _bar(photo),
                    "outline": _outline(photo),
                }
                for photo in visit["photos"]
            ]
            checks = sorted({f for photo in visit["photos"] for f in photo["flags"] if f in CHECK_FLAGS})
            visits.append(
                {
                    "title": words("visit", date=words.day(date.fromisoformat(visit["local_date"]))),
                    "photos": photos,
                    "measured": _measurement_row(measured, words, zone) if measured else None,
                    "checks": [words(f"check_{flag}") for flag in checks],
                    "notes": visit["notes"],
                    "symptoms": [words(f"symptom_{s}") for s in visit["symptoms"] if s in SYMPTOMS],
                    "has_outline": any(p["outline"] for p in photos),
                }
            )
        latest = measurements[-1] if measurements else None
        change = latest.get("change") if latest else None
        lesions.append(
            {
                "id": lesion["id"],
                "number": lesion["number"],
                "title": _title(lesion, words),
                "zone": words.zone(lesion["zone"]),
                "view": words(lesion["view"]),
                "type": words(f"type_{lesion['type']}") if lesion["type"] in ("mole", "other") else lesion["type"],
                "status": words(f"status_{lesion['status']}"),
                "first_noticed": words.day(date.fromisoformat(lesion["first_noticed_on"]))
                if lesion["first_noticed_on"]
                else words("unknown"),
                "interval": words("days", n=lesion["interval_days"]),
                "notes": lesion["notes"],
                "rows": [_measurement_row(m, words, zone) for m in measurements],
                "chart": svg.size_chart(points, words) if len(points) >= 2 else "",
                "map": svg.body_view(
                    lesion["view"],
                    [svg.Marker(lesion["x"], lesion["y"], "", lesion["view"], highlighted=True)],
                    zone=lesion["zone"],
                    height=200,
                ),
                "visits": visits,
                "latest": words.mm(latest["longest_mm"], latest["sigma_longest_mm"]) if latest else "—",
                "last_visit": _short(words, _local(lesion["last_observed_at"], zone)),
                "next": _due_state(lesion, words, zone, generated.date()),
                "change": None
                if not change
                else {
                    "value": words.mm(change["delta_mm"], change["sigma_mm"], sign=True),
                    "detectable": change["detectable"],
                    "since": words("since", date=words.day(_local(measurements[-2]["captured_at"], zone))),
                },
            }
        )
    markers = [svg.Marker(raw["x"], raw["y"], str(raw["number"]), raw["view"]) for raw in payload["lesions"]]
    scale_kinds = sorted(
        {m["scale_kind"] for raw in payload["lesions"] for m in raw["measurements"] if m["scale_kind"]}
    )
    analyzers = ", ".join(f"{name} {'/'.join(versions)}" for name, versions in payload["analyzers"].items()) or "—"
    page = words("page", page='" counter(page) "', pages='" counter(pages) "')
    scope = payload["scope"]
    first = lesions[0]["title"] if scope == "lesion" and lesions else None
    raw_appointment = payload.get("appointment")
    appointment = None
    if raw_appointment:
        on = words.day(date.fromisoformat(raw_appointment["date"]))
        appointment = {"title": words("appointment_title", date=on), "notes": raw_appointment.get("notes")}
        first = appointment["title"]
    titles = {
        "lesion": "lesion_title",
        "profile": "profile_title",
        "visit": "visit_report_title",
        "selection": "selection_title",
    }
    wanted = set(payload.get("records") or [])
    return {
        "w": words,
        "lang": words.language,
        "scope": scope,
        "paper": "letter" if payload["paper"] == "letter" else "A4",
        "title": words(titles.get(scope, "profile_title")),
        "appointment": appointment,
        "records": [lesion for lesion in lesions if lesion["id"] in wanted],
        "generated": words("generated", date=words.day(generated)),
        "person": person["name"],
        "born": words("born", year=person["birth_year"]) if person.get("birth_year") else None,
        "lesions": lesions,
        "front": svg.body_view("front", markers, height=300, radius=8),
        "back": svg.body_view("back", markers, height=300, radius=8),
        "details": [
            (view, svg.body_view(view, markers, height=300, radius=8))
            for view in ("head", "hands", "feet")
            if any(raw["view"] == view for raw in payload["lesions"])
        ],
        "highlights": [lesion for lesion in lesions if lesion["change"] and lesion["change"]["detectable"]],
        "methods_scale": words("methods_scale", kinds=", ".join(words(f"scale_{k}") for k in scale_kinds))
        if scale_kinds
        else None,
        "methods_software": words("methods_analyzers", version=payload["version"], analyzers=analyzers),
        "footer": css_string(" · ".join(part for part in ("neVus", person["name"], first) if part)),
        "page_counter": f'"{page}"',
        "colours": COLOURS,
        "roles": {role: words(f"role_{role}") for role in ROLES},
    }


def public(payload: dict[str, Any]) -> dict[str, Any]:
    """The attached data: everything shown, without where the files live on the server."""
    data: dict[str, Any] = json.loads(json.dumps(payload))
    for lesion in data["lesions"]:
        for visit in lesion["visits"]:
            for photo in visit["photos"]:
                photo.pop("path", None)
    return data


def render(payload: dict[str, Any]) -> dict[str, Any]:
    from weasyprint import HTML, Attachment
    from weasyprint.text.fonts import FontConfiguration

    env = Environment(
        loader=FileSystemLoader(HERE / "templates"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    html = env.get_template(f"{payload['scope']}.html").render(**context(payload))
    allowed = {
        Path(photo["path"]).resolve()
        for lesion in payload["lesions"]
        for visit in lesion["visits"]
        for photo in visit["photos"]
    }
    fonts = FontConfiguration()
    document = HTML(string=html, base_url=(HERE / "assets").as_uri() + "/", url_fetcher=_fetcher(allowed)).render(
        font_config=fonts
    )
    data = json.dumps(public(payload), ensure_ascii=False, indent=2).encode()
    pdf: bytes = document.write_pdf(
        pdf_variant="pdf/a-3b",
        attachments=[
            Attachment(
                string=data,
                name="nevus-report-data.json",
                description="The data behind this report (neVus report format 1)",
                relationship="Data",
            )
        ],
        uncompressed_pdf=False,
    )
    return {"pdf": pdf, "pages": len(document.pages)}
