import argparse

from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_engine
from apps.workers.workflows.outbox import process_outbox_once


def main() -> None:
    parser = argparse.ArgumentParser(description="Agora worker commands")
    parser.add_argument("command", nargs="?", default="outbox-once", choices=["outbox-once"])
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--max-attempts", type=int, default=3)
    args = parser.parse_args()

    session_factory = sessionmaker(bind=get_engine())
    with session_factory() as session:
        result = process_outbox_once(session, limit=args.limit, max_attempts=args.max_attempts)
    print(
        "outbox processed="
        f"{result.processed} completed={result.completed} failed={result.failed} dead={result.dead}"
    )


if __name__ == "__main__":
    main()
