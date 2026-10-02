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
    make = sub.add_parser("backup", help="write an encrypted backup of everything neVus owns")
    make.add_argument("--out", help="directory (default: the data directory's backups/)")
    make.add_argument("--passphrase-file", help="file holding the passphrase (default: NEVUS_BACKUP_PASSPHRASE)")
    back = sub.add_parser("restore", help="restore an encrypted backup into an empty data directory")
    back.add_argument("file")
    back.add_argument("--passphrase-file")
    back.add_argument("--force", action="store_true", help="restore over a data directory that is not empty")
    sub.add_parser("verify", help="check that every stored photo is present and intact")
    sub.add_parser("housekeeping", help="purge the trash and remove unreferenced files now")
    args = parser.parse_args(argv)
    if args.command == "serve":
        return _serve()
    if args.command == "openapi":
        return _openapi()
    if args.command == "card":
        return _card(args.page, args.lang, args.out)
    if args.command == "backup":
        return _backup(args.out, args.passphrase_file)
    if args.command == "restore":
        return _restore(args.file, args.passphrase_file, args.force)
    if args.command == "verify":
        return _verify()
    if args.command == "housekeeping":
        return _housekeeping()
    return 2


def _passphrase(path: str | None, *, confirm: bool) -> str:
    import getpass
    import os
    from pathlib import Path

    if path:
        return Path(path).read_text().strip()
    if os.environ.get("NEVUS_BACKUP_PASSPHRASE"):
        return os.environ["NEVUS_BACKUP_PASSPHRASE"]
    first = getpass.getpass("Backup passphrase: ")
    if confirm and getpass.getpass("Repeat it: ") != first:
        raise SystemExit("The passphrases differ.")
    return first


def _backup(out: str | None, passphrase_file: str | None) -> int:
    from pathlib import Path

    from nevus import backup
    from nevus.config import get_settings

    settings = get_settings()
    path = backup.create(settings, _passphrase(passphrase_file, confirm=True), out_dir=Path(out) if out else None)
    print(path)
    if not settings.is_sqlite:
        print("PostgreSQL mode: this backup holds the photographs and the server secret.")
        print("Back up the database itself with pg_dump (see docs/DEPLOYMENT.md).")
    return 0


def _restore(file: str, passphrase_file: str | None, force: bool) -> int:
    from pathlib import Path

    from nevus import backup
    from nevus.config import get_settings

    settings = get_settings()
    try:
        manifest = backup.restore(
            Path(file), _passphrase(passphrase_file, confirm=False), settings.data_dir, force=force
        )
    except (backup.RestoreError, ValueError) as error:
        print(f"Restore refused: {error}", file=sys.stderr)
        return 1
    print(
        f"Restored the backup of {manifest['created_at']} (neVus {manifest['nevus_version']}) into {settings.data_dir}."
    )
    return 0


def _verify() -> int:
    from nevus import backup
    from nevus.config import get_settings

    counts = backup.verify(get_settings())
    print(f"{counts['checked']} files checked, {counts['missing']} missing, {counts['corrupt']} damaged.")
    return 0 if counts["missing"] == 0 and counts["corrupt"] == 0 else 1


def _housekeeping() -> int:
    from nevus.config import get_settings
    from nevus.db.engine import make_engine, make_session_factory
    from nevus.jobs.registry import JobContext
    from nevus.maintenance import daily_housekeeping
    from nevus.storage.blobs import BlobStore

    settings = get_settings()
    factory = make_session_factory(make_engine(settings.effective_database_url))
    with factory() as db:
        daily_housekeeping(JobContext(db, BlobStore(settings.blobs_dir, settings.min_free_bytes), settings))
        db.commit()
    print("Done.")
    return 0


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
