# SPDX-License-Identifier: AGPL-3.0-only
"""How the full-body session matching does on real photographs taken years apart.

The ISIC Archive's collection 217, "Longitudinal overview images of posterior trunks" (University of
Pittsburgh Medical Center and Hillman Cancer Center, CC-BY, https://doi.org/10.34970/630662), holds
36 photos of the backs of 17 persons, each photographed again after months or years. This script
downloads them into a cache outside the repository (nothing is committed), finds the spots on each
with `candidates`, and lines up:

- each person's consecutive photos: a good matcher lines up many, and every alignment it makes must
  be right (write overlays with --overlays and look at them: red and cyan fringes mean a misfit);
- every pair of photos of different persons: none may be lined up.

    uv run --project backend python tools/evaluation/longitudinal_backs.py [--cache DIR] [--overlays DIR]
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from nevus.cv import candidates, constellation

API = "https://api.isic-archive.com/api/v2/images/search/?collections=217&limit=100"


def download(cache: Path) -> list[dict[str, object]]:
    cache.mkdir(parents=True, exist_ok=True)
    index = cache / "index.json"
    if not index.exists():
        with urllib.request.urlopen(API, timeout=60) as response:
            results = json.load(response)["results"]
        fetched: list[dict[str, object]] = []
        for item in results:
            if item["copyright_license"] != "CC-BY":
                raise SystemExit(f"{item['isic_id']} is not CC-BY; stopping.")
            clinical = item["metadata"]["clinical"]
            fetched.append(
                {
                    "isic_id": item["isic_id"],
                    "person": clinical["patient_id"],
                    "day": clinical["acquisition_day"],
                    "attribution": item["attribution"],
                    "url": item["files"]["full"]["url"],
                }
            )
        index.write_text(json.dumps(fetched, indent=1))
    rows: list[dict[str, object]] = json.loads(index.read_text())
    for row in rows:
        target = cache / f"{row['isic_id']}.jpg"
        if not target.exists():
            url = str(row["url"])
            if not url.startswith("https://"):
                raise SystemExit(f"Refusing to fetch {url}: only https.")
            with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 - scheme checked above
                target.write_bytes(response.read())
    return rows


def read(path: Path) -> np.ndarray:
    image = cv2.imread(str(path))
    if image is None:
        raise SystemExit(f"{path} could not be read; delete it and run again.")
    return image


def overlay(earlier: np.ndarray, later: np.ndarray, matrix: list[list[float]], path: Path) -> None:
    """The earlier photo, lined up, in red; the later in cyan. Where they agree the picture is grey."""
    h, w = later.shape[:2]
    warped = cv2.warpPerspective(earlier, np.asarray(matrix), (w, h))
    red = cv2.equalizeHist(cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY))
    cyan = cv2.equalizeHist(cv2.cvtColor(later, cv2.COLOR_BGR2GRAY))
    picture = np.dstack([cyan, cyan, red])
    cv2.imwrite(str(path), cv2.resize(picture, (1200, int(1200 * h / w)), interpolation=cv2.INTER_AREA))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cache", type=Path, default=Path.home() / ".cache" / "nevus-evaluation" / "isic-217")
    parser.add_argument("--overlays", type=Path, help="write an overlay of each aligned pair here")
    args = parser.parse_args(argv)
    rows = download(args.cache)
    images = {str(row["isic_id"]): read(args.cache / f"{row['isic_id']}.jpg") for row in rows}
    spots = {key: candidates.detect(image)["candidates"] for key, image in images.items()}
    size = {key: (image.shape[1], image.shape[0]) for key, image in images.items()}

    def line_up(a: str, b: str) -> dict[str, object]:
        return constellation.match(spots[a], size[a], spots[b], size[b])

    by_person: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        by_person.setdefault(str(row["person"]), []).append(row)
    print("Consecutive photos of the same person:")
    same = aligned = 0
    for person, photos in sorted(by_person.items()):
        photos.sort(key=lambda row: int(str(row["day"])))
        for earlier, later in itertools.pairwise(photos):
            a, b = str(earlier["isic_id"]), str(later["isic_id"])
            result = line_up(a, b)
            same += 1
            days = int(str(later["day"])) - int(str(earlier["day"]))
            if result["status"] == "aligned":
                aligned += 1
                if args.overlays:
                    args.overlays.mkdir(parents=True, exist_ok=True)
                    overlay(images[a], images[b], result["matrix"], args.overlays / f"{person}-{a}-{b}.jpg")  # type: ignore[arg-type]
            print(
                f"  {person}  {days:5d} days apart  {len(spots[a]):3d} and {len(spots[b]):3d} spots  "
                f"{result['status']:9}  {len(result['pairs']):3d} pairs  {result['reason'] or ''}"  # type: ignore[arg-type]
            )
    print(f"  {aligned} of {same} lined up.")
    reasons: Counter[str] = Counter()
    wrong = 0
    pairs = [(a, b) for a, b in itertools.permutations(rows, 2) if a["person"] != b["person"]]
    for first, second in pairs:
        result = line_up(str(first["isic_id"]), str(second["isic_id"]))
        wrong += result["status"] == "aligned"
        reasons[str(result["reason"])] += 1
    print(f"Photos of different persons: {wrong} of {len(pairs)} pairs lined up (there should be none).")
    print("  Reasons given:", ", ".join(f"{reason} {count}" for reason, count in reasons.most_common()))
    return 0 if wrong == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
