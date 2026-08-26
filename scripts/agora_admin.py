import argparse
from pathlib import Path
import sqlite3
import sys

from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import create_app_engine
from packages.core.schema_manager import MigrationRequiredError, ensure_schema
from packages.knowledge.index_rebuilder import rebuild_indexes_from_assets
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex


def _sqlite_file_from_url(database_url: str) -> Path | None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        return None
    if not url.database or url.database == ":memory:":
        return None
    return Path(url.database).expanduser().resolve()


def rebuild_indexes(database_url: str) -> int:
    ensure_schema(database_url)
    engine = create_app_engine(database_url)
    session = sessionmaker(bind=engine)()
    try:
        return rebuild_indexes_from_assets(session, FakeKeywordIndex(), FakeVectorIndex())
    finally:
        session.close()


def reset_local(database_url: str, *, yes: bool) -> None:
    database_path = _sqlite_file_from_url(database_url)
    if database_path is None:
        raise SystemExit("reset-local only supports file-backed SQLite URLs")
    if not yes:
        raise SystemExit("Refusing to reset local database without --yes")

    for path in (database_path, Path(f"{database_path}-wal"), Path(f"{database_path}-shm")):
        path.unlink(missing_ok=True)
    ensure_schema(database_url)


def migrate(database_url: str, *, dry_run: bool, postgres_backup_confirmed: bool):
    return ensure_schema(
        database_url,
        dry_run=dry_run,
        postgres_backup_confirmed=postgres_backup_confirmed,
    )


def backup_sqlite(database_url: str, *, output: Path) -> Path:
    database_path = _sqlite_file_from_url(database_url)
    if database_path is None:
        raise SystemExit("backup-sqlite only supports file-backed SQLite URLs")
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    source_uri = f"file:{database_path}?mode=ro"
    with sqlite3.connect(source_uri, uri=True) as source, sqlite3.connect(output) as destination:
        source.backup(destination)
    return output


def restore_sqlite(*, backup: Path, database_url: str, yes: bool) -> Path:
    if not yes:
        raise SystemExit("Refusing to restore SQLite database without --yes")
    database_path = _sqlite_file_from_url(database_url)
    if database_path is None:
        raise SystemExit("restore-sqlite only supports file-backed SQLite URLs")
    backup = backup.expanduser().resolve()
    if not backup.exists():
        raise SystemExit(f"Backup not found: {backup}")
    database_path.parent.mkdir(parents=True, exist_ok=True)
    for path in (database_path, Path(f"{database_path}-wal"), Path(f"{database_path}-shm")):
        path.unlink(missing_ok=True)
    with sqlite3.connect(backup) as source, sqlite3.connect(database_path) as destination:
        source.backup(destination)
    ensure_schema(database_url)
    return database_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agora local administration commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    rebuild = subparsers.add_parser("rebuild-indexes", help="Rebuild local search indexes from persisted assets")
    rebuild.add_argument("--database-url", required=True)

    reset = subparsers.add_parser("reset-local", help="Reset a file-backed local SQLite database")
    reset.add_argument("--database-url", required=True)
    reset.add_argument("--yes", action="store_true", help="Confirm destructive local reset")

    migrate_parser = subparsers.add_parser("migrate", help="Inspect and migrate the product database")
    migrate_parser.add_argument("--database-url", required=True)
    migrate_parser.add_argument("--dry-run", action="store_true", help="Inspect without changing the database")
    migrate_parser.add_argument(
        "--postgres-backup-confirmed",
        action="store_true",
        help="Confirm an operator backup exists before stamping an unversioned PostgreSQL P1 schema",
    )

    backup = subparsers.add_parser("backup-sqlite", help="Write an online backup of a file-backed SQLite database")
    backup.add_argument("--database-url", required=True)
    backup.add_argument("--output", required=True, type=Path)

    restore = subparsers.add_parser("restore-sqlite", help="Restore a file-backed SQLite database from a backup file")
    restore.add_argument("--backup", required=True, type=Path)
    restore.add_argument("--database-url", required=True)
    restore.add_argument("--yes", action="store_true", help="Confirm replacing the target SQLite database")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "rebuild-indexes":
        count = rebuild_indexes(args.database_url)
        print(f"Rebuilt indexes from {count} persisted assets")
        return 0
    if args.command == "reset-local":
        reset_local(args.database_url, yes=args.yes)
        print("Reset local SQLite database")
        return 0
    if args.command == "migrate":
        try:
            result = migrate(
                args.database_url,
                dry_run=args.dry_run,
                postgres_backup_confirmed=args.postgres_backup_confirmed,
            )
        except MigrationRequiredError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(f"Action: {result.action}")
        print(f"Schema fingerprint: {result.fingerprint}")
        print(f"Revision: {result.revision_before or 'unversioned'} -> {result.revision_after}")
        print(f"Backup: {result.backup_path or 'not-created'}")
        return 0
    if args.command == "backup-sqlite":
        path = backup_sqlite(args.database_url, output=args.output)
        print(f"SQLite backup written: {path}")
        return 0
    if args.command == "restore-sqlite":
        path = restore_sqlite(backup=args.backup, database_url=args.database_url, yes=args.yes)
        print(f"SQLite backup restored: {path}")
        return 0
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
