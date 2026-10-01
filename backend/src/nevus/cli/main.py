"""`nevus` command-line tools."""

from __future__ import annotations

import argparse
import sys

from nevus import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nevus", description="neVus command-line tools")
    parser.add_argument("--version", action="version", version=f"nevus {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("serve", help="run the web application")
    sub.add_parser("openapi", help="print the OpenAPI schema as JSON")
    card = sub.add_parser("card", help="write the printable reference card sheet as PDF")
    card.add_argument("--page", choices=["a4", "letter"], default="a4")
    card.add_argument("--lang", choices=["en", "es"], default="en")
    card.add_argument("--out", required=True, help="output file, or - for standard output")
    args = parser.parse_args(argv)
    if args.command == "serve":
        return _serve()
    if args.command == "openapi":
        return _openapi()
    if args.command == "card":
        return _card(args.page, args.lang, args.out)
    return 2


def _card(page: str, lang: str, out: str) -> int:
    from pathlib import Path

    from nevus.cv.card_sheet import render_sheet

    pdf = render_sheet(page, lang)
    if out == "-":
        sys.stdout.buffer.write(pdf)
    else:
        Path(out).write_bytes(pdf)
    return 0


def _openapi() -> int:
    import json
    import tempfile
    from pathlib import Path

    from nevus.app import create_app
    from nevus.config import Settings

    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(Settings(data_dir=Path(tmp), log_level="warning"))
        schema = app.openapi()
        # The snapshot feeds the frontend's generated types; the release version would only make it stale.
        schema["info"]["version"] = "snapshot"
        print(json.dumps(schema, indent=2, sort_keys=True))
    return 0


def _serve() -> int:
    import uvicorn

    from nevus.config import get_settings

    settings = get_settings()
    uvicorn.run(
        "nevus.app:create_app",
        factory=True,
        host=settings.bind,
        port=settings.port,
        log_level=settings.log_level,
        workers=1,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
