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
    check = sub.add_parser("verify", help="check that every stored photo is present and intact")
    check.add_argument(
        "--backup",
        nargs="?",
        const="latest",
        metavar="FILE",
        help="instead, read a backup back and report whether it would restore (default: the latest)",
    )
    check.add_argument("--passphrase-file", help="file holding the passphrase (default: NEVUS_BACKUP_PASSPHRASE)")
    check.add_argument("--json", action="store_true", help="print the report as JSON")
    sub.add_parser("housekeeping", help="purge the trash and remove unreferenced files now")
    emergency = sub.add_parser(
        "emergency-login", help="print a one-use sign-in link, for when single sign-on is unavailable"
    )
    emergency.add_argument("username")
    emergency.add_argument("--base-url", help="address to put in the link (default: NEVUS_PUBLIC_URL)")
    again = sub.add_parser(
        "reanalyze", help="queue the current analyzers for stored photos again; earlier results are kept"
    )
    again.add_argument("--analyzer", choices=["quality", "card", "segment", "all"], default="all")
    again.add_argument("--person", help="only the photos of this person (id)")
    again.add_argument("--now", action="store_true", help="run the queue here rather than leave it to the server")
    judge = sub.add_parser("evaluate", help="measure the outline analyzer on the labelled evaluation photos")
    judge.add_argument("--json", action="store_true", help="print the report as JSON")
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
        return _verify(args.backup, args.passphrase_file, args.json)
    if args.command == "housekeeping":
        return _housekeeping()
    if args.command == "reanalyze":
        return _reanalyze(args.analyzer, args.person, args.now)
    if args.command == "evaluate":
        return _evaluate(args.json)
    if args.command == "emergency-login":
        return _emergency_login(args.username, args.base_url)
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


def _verify(which: str | None, passphrase_file: str | None, as_json: bool) -> int:
    import json
    from pathlib import Path

    from nevus import backup
    from nevus.config import get_settings

    settings = get_settings()
    if which is None:
        counts = backup.verify(settings)
        print(f"{counts['checked']} files checked, {counts['missing']} missing, {counts['corrupt']} damaged.")
        return 0 if counts["missing"] == 0 and counts["corrupt"] == 0 else 1
    archive = None if which == "latest" else Path(which)
    report = backup.rehearse(settings, _passphrase(passphrase_file, confirm=False), archive)
    print(json.dumps(report, indent=2) if as_json else backup.describe(report))
    return 0 if report["ok"] else 1


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


def _reanalyze(which: str, person: str | None, now: bool) -> int:
    """FR-ANA-04: a newer analyzer version runs over past photos; its results are added, never replacing."""
    import uuid

    from sqlalchemy import select

    from nevus.config import get_settings
    from nevus.cv import card_detect, quality
    from nevus.cv.pipeline import CARD_KIND, QUALITY_KIND, enqueue_proposal
    from nevus.db.engine import make_engine, make_session_factory
    from nevus.db.models import Image
    from nevus.jobs import queue
    from nevus.jobs.runner import JobRunner
    from nevus.storage.blobs import BlobStore

    settings = get_settings()
    factory = make_session_factory(make_engine(settings.effective_database_url))
    counts = {"quality": 0, "card": 0, "segment": 0}
    with factory() as db:
        query = select(Image).where(Image.deleted_at.is_(None))
        if person:
            query = query.where(Image.person_id == uuid.UUID(person))
        for image in db.scalars(query):
            if which in ("quality", "all") and queue.enqueue(
                db, QUALITY_KIND, {"image_id": str(image.id)}, dedupe_key=f"quality:{image.id}:{quality.VERSION}"
            ):
                counts["quality"] += 1
            if (
                which in ("card", "all")
                and image.observation_id is not None
                and queue.enqueue(
                    db, CARD_KIND, {"image_id": str(image.id)}, dedupe_key=f"card:{image.id}:{card_detect.VERSION}"
                )
            ):
                counts["card"] += 1
            if which in ("segment", "all") and enqueue_proposal(db, image):
                counts["segment"] += 1
        db.commit()
    print(
        f"Queued {counts['quality']} quality, {counts['card']} card and {counts['segment']} outline analyses; "
        "photos already analysed by the current versions are skipped."
    )
    if now:
        runner = JobRunner(factory, BlobStore(settings.blobs_dir, settings.min_free_bytes), settings)
        print(f"Ran {runner.run_until_idle()} jobs here.")
    return 0


def _evaluate(as_json: bool) -> int:
    import json

    from nevus import evaluation
    from nevus.config import get_settings
    from nevus.db.engine import make_engine, make_session_factory
    from nevus.storage.blobs import BlobStore

    settings = get_settings()
    factory = make_session_factory(make_engine(settings.effective_database_url))
    with factory() as db:
        report = evaluation.evaluate(
            db, evaluation.fresh_runner(db, BlobStore(settings.blobs_dir, settings.min_free_bytes))
        )
    print(json.dumps(report, indent=2) if as_json else evaluation.table(report))
    return 0


def _emergency_login(username: str, base_url: str | None) -> int:
    from nevus.auth.proxy import EMERGENCY_LINK_MINUTES, EMERGENCY_SESSION_HOURS, emergency_link
    from nevus.auth.service import normalise_username
    from nevus.config import get_settings
    from nevus.db.engine import make_engine, make_session_factory

    settings = get_settings()
    factory = make_session_factory(make_engine(settings.effective_database_url))
    with factory() as db:
        try:
            token = emergency_link(db, settings, normalise_username(username))
        except LookupError as error:
            print(f"neVus: {error}", file=sys.stderr)
            return 1
        db.commit()
    base = (base_url or settings.public_url or f"http://localhost:{settings.port}").rstrip("/")
    print(f"{base}/api/auth/emergency/{token}")
    print(
        f"Open it within {EMERGENCY_LINK_MINUTES} minutes; it works once and signs in for up to "
        f"{EMERGENCY_SESSION_HOURS} hours, without the single sign-on.",
        file=sys.stderr,
    )
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
        # The peer address must stay the real one: proxy sign-in trusts only the proxy's own address.
        # X-Forwarded-* are read by neVus itself when NEVUS_TRUST_PROXY_HEADERS is on.
        proxy_headers=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
