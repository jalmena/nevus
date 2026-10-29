# SPDX-License-Identifier: AGPL-3.0-only
"""Copy the body-map zone names of every interface catalogue into the reports' `zone_names.json`.

The reports name zones without depending on the frontend at runtime, so the names are copied here
and a test (`backend/tests/test_reports.py`) keeps the two equal.

Usage: uv run --project backend python tools/i18n/zone_names.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCALES = ROOT / "frontend/src/lib/i18n/locales"
TARGET = ROOT / "backend/src/nevus/reports/zone_names.json"


def main() -> None:
    names = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))["zones"]
        for path in sorted(LOCALES.glob("*.json"))
    }
    TARGET.write_text(
        json.dumps(names, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"{TARGET.relative_to(ROOT)}: {len(names)} languages, {len(names['en'])} zones each"
    )


if __name__ == "__main__":
    main()
