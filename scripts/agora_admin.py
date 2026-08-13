import argparse
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import create_app_engine
from packages.core.database import Base
import packages.core.models  # noqa: F401
from packages.knowledge.index_rebuilder import rebuild_indexes_from_assets
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex


def _sqlite_file_from_url(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite"):
        return None
    if database_url == "sqlite+pysqlite:///:memory:":
        return None
    marker = "///"
    if marker not in database_url:
        return None
    return Path(database_url.rsplit(marker, 1)[-1])


def rebuild_indexes(database_url: str) -> int:
    engine = create_app_engine(database_url)
    session = sessionmaker(bind=engine)()
    try:
        return rebuild_indexes_from_assets(session, FakeKeywordIndex(), FakeVectorIndex())
    finally:
        session.close()


def reset_local(database_url: str, *, yes: bool) -> None:
    if _sqlite_file_from_url(database_url) is None:
        raise SystemExit("reset-local only supports file-backed SQLite URLs")
    if not yes:
        raise SystemExit("Refusing to reset local database without --yes")

    engine = create_app_engine(database_url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    engine.dispose()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agora local administration commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    rebuild = subparsers.add_parser("rebuild-indexes", help="Rebuild local search indexes from persisted assets")
    rebuild.add_argument("--database-url", required=True)

    reset = subparsers.add_parser("reset-local", help="Reset a file-backed local SQLite database")
    reset.add_argument("--database-url", required=True)
    reset.add_argument("--yes", action="store_true", help="Confirm destructive local reset")
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
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
