# SPDX-License-Identifier: AGPL-3.0-only
"""How well the analyzers do on the operator's own labelled photos, per skin tone (FR-ANA-05).

The labels are the truth: an outline the operator drew or corrected, and a good or poor judgement of
the photo. For outlines this reports how often a mark was found, the overlap with the label (IoU and
Dice) and the error of the equivalent diameter; for quality, how the automatic warnings agree with the
judgement. Everything stays on the server; nothing here is sent anywhere.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from nevus import analysis
from nevus.cv import card_detect, segment
from nevus.cv.pipeline import load_upright
from nevus.db.models import EvaluationLabel, Image, Person
from nevus.storage.blobs import BlobStore

Runner = Callable[[Image], dict[str, Any] | None]


def overlap(a: list[list[float]], b: list[list[float]]) -> tuple[float, float]:
    """IoU and Dice of two outlines, rasterised together on a canvas of at most 1024 pixels."""
    pa, pb = np.asarray(a, np.float64), np.asarray(b, np.float64)
    both = np.vstack([pa, pb])
    lo, hi = both.min(axis=0), both.max(axis=0)
    scale = 1024 / max(float((hi - lo).max()), 1.0)
    size = (math.ceil((hi[1] - lo[1]) * scale) + 3, math.ceil((hi[0] - lo[0]) * scale) + 3)
    masks = []
    for points in (pa, pb):
        mask = np.zeros(size, np.uint8)
        cv2.fillPoly(mask, [np.round((points - lo) * scale + 1).astype(np.int32)], 1)
        masks.append(mask.astype(bool))
    inter = float((masks[0] & masks[1]).sum())
    union = float((masks[0] | masks[1]).sum())
    total = float(masks[0].sum() + masks[1].sum())
    return (inter / union if union else 0.0), (2 * inter / total if total else 0.0)


def equivalent_diameter(outline: list[list[float]]) -> float:
    return 2 * math.sqrt(abs(float(cv2.contourArea(np.asarray(outline, np.float32)))) / math.pi)


@dataclass
class Outlines:
    photos: int = 0
    found: int = 0
    iou: list[float] = field(default_factory=list)
    dice: list[float] = field(default_factory=list)
    diameter_error: list[float] = field(default_factory=list)

    def add(self, label: list[list[float]], result: dict[str, Any] | None) -> None:
        self.photos += 1
        if not result or not result.get("found") or not result.get("outline"):
            return
        self.found += 1
        iou, dice = overlap(label, result["outline"])
        self.iou.append(iou)
        self.dice.append(dice)
        truth = equivalent_diameter(label)
        if truth > 0:
            self.diameter_error.append(abs(equivalent_diameter(result["outline"]) - truth) / truth)

    def summary(self) -> dict[str, Any]:
        def mean(values: list[float]) -> float | None:
            return round(sum(values) / len(values), 3) if values else None

        return {
            "photos": self.photos,
            "found": self.found,
            "mean_iou": mean(self.iou),
            "mean_dice": mean(self.dice),
            "mean_diameter_error": mean(self.diameter_error),
            "worst_diameter_error": round(max(self.diameter_error), 3) if self.diameter_error else None,
        }


@dataclass
class Quality:
    poor_caught: int = 0
    poor_missed: int = 0
    good_flagged: int = 0
    good_clear: int = 0

    def add(self, label: str, flags: list[str]) -> None:
        warned = bool(flags)
        if label == "bad":
            self.poor_caught += warned
            self.poor_missed += not warned
        else:
            self.good_flagged += warned
            self.good_clear += not warned

    def summary(self) -> dict[str, Any]:
        total = self.poor_caught + self.poor_missed + self.good_flagged + self.good_clear
        agree = self.poor_caught + self.good_clear
        return {
            "photos": total,
            "agreement": round(agree / total, 3) if total else None,
            "poor_caught": self.poor_caught,
            "poor_missed": self.poor_missed,
            "good_flagged": self.good_flagged,
            "good_clear": self.good_clear,
        }


def stored_runner(db: Session) -> Runner:
    """The latest outline proposal already recorded for the photo, if any."""

    def run(image: Image) -> dict[str, Any] | None:
        row = analysis.latest(db, "image", image.id, segment.NAME)
        return row.outputs if row is not None else None

    return run


def fresh_runner(db: Session, store: BlobStore) -> Runner:
    """The current outline analyzer run now on the photo; nothing is recorded."""

    def run(image: Image) -> dict[str, Any] | None:
        card = analysis.latest(db, "image", image.id, card_detect.NAME)
        return segment.propose(load_upright(store, image), card.outputs if card else None)

    return run


def evaluate(db: Session, run: Runner) -> dict[str, Any]:
    rows = db.execute(
        select(EvaluationLabel, Image, Person)
        .join(Image, Image.id == EvaluationLabel.image_id)
        .join(Person, Person.id == Image.person_id)
        .where(Image.deleted_at.is_(None), Person.deleted_at.is_(None))
    ).all()
    outlines: dict[str, Outlines] = {}
    quality: dict[str, Quality] = {}
    every_outline, every_quality = Outlines(), Quality()
    for label, image, person in rows:
        tone = person.skin_tone or "unknown"
        if label.outline:
            result = run(image)
            outlines.setdefault(tone, Outlines()).add(label.outline, result)
            every_outline.add(label.outline, result)
        if label.quality in ("good", "bad"):
            quality.setdefault(tone, Quality()).add(label.quality, list(image.quality_flags or []))
            every_quality.add(label.quality, list(image.quality_flags or []))
    return {
        "analyzer": {"name": segment.NAME, "version": segment.VERSION},
        "labelled": len(rows),
        "outline": {
            "overall": every_outline.summary(),
            "by_tone": {tone: tally.summary() for tone, tally in sorted(outlines.items())},
        },
        "quality": {
            "overall": every_quality.summary(),
            "by_tone": {tone: tally.summary() for tone, tally in sorted(quality.items())},
        },
    }


def table(report: dict[str, Any]) -> str:
    """The report as plain text for the command line."""

    def pct(value: float | None) -> str:
        return "—" if value is None else f"{value * 100:.1f} %"

    def num(value: float | None) -> str:
        return "—" if value is None else f"{value:.2f}"

    lines = [
        f"Outline ({report['analyzer']['name']} {report['analyzer']['version']}), "
        f"{report['outline']['overall']['photos']} labelled photos",
        f"{'tone':10} {'photos':>6} {'found':>6} {'IoU':>6} {'Dice':>6} {'diameter error (mean / worst)':>32}",
    ]
    for tone, row in [*report["outline"]["by_tone"].items(), ("all", report["outline"]["overall"])]:
        lines.append(
            f"{tone:10} {row['photos']:>6} {row['found']:>6} {num(row['mean_iou']):>6} {num(row['mean_dice']):>6} "
            f"{pct(row['mean_diameter_error']) + ' / ' + pct(row['worst_diameter_error']):>32}"
        )
    q = report["quality"]["overall"]
    lines += [
        "",
        f"Quality warnings, {q['photos']} labelled photos: agreement {pct(q['agreement'])}; "
        f"poor photos warned {q['poor_caught']} of {q['poor_caught'] + q['poor_missed']}, "
        f"good photos warned {q['good_flagged']} of {q['good_flagged'] + q['good_clear']}",
    ]
    return "\n".join(lines)
