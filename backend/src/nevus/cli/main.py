"""`nevus` command: serve the application. Backup, restore and verify arrive with their features."""

from __future__ import annotations

import argparse
import sys

from nevus import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nevus", description="neVus command-line tools")
    parser.add_argument("--version", action="version", version=f"nevus {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("serve", help="run the web application")
    args = parser.parse_args(argv)
    if args.command == "serve":
        return _serve()
    return 2


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
