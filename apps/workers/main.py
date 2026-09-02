import argparse
import signal
import threading

from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import get_engine
from apps.workers.workflows.outbox import process_outbox_once, run_worker_loop


def main() -> None:
    parser = argparse.ArgumentParser(description="Agora worker commands")
    parser.add_argument(
        "command",
        nargs="?",
        default="outbox-once",
        choices=["outbox-once", "outbox-loop"],
    )
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--idle-delay", type=float, default=1.0)
    parser.add_argument("--once", action="store_true", help="outbox-loop: process a single batch and exit")
    args = parser.parse_args()

    session_factory = sessionmaker(bind=get_engine())

    if args.command == "outbox-once":
        with session_factory() as session:
            result = process_outbox_once(session, limit=args.limit, max_attempts=args.max_attempts)
        print(
            "outbox processed="
            f"{result.processed} completed={result.completed} failed={result.failed} dead={result.dead}"
        )
        return

    if args.once:
        with session_factory() as session:
            result = process_outbox_once(session, limit=args.limit, max_attempts=args.max_attempts)
        print(
            "outbox-loop once processed="
            f"{result.processed} completed={result.completed} failed={result.failed} dead={result.dead}"
        )
        return

    shutdown = threading.Event()

    def _handle_signal(signum, frame):
        shutdown.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    total = run_worker_loop(
        session_factory,
        max_attempts=args.max_attempts,
        batch_limit=args.limit,
        idle_delay=args.idle_delay,
        shutdown_event=shutdown,
    )
    print(f"outbox worker stopped after processing {total} events")


if __name__ == "__main__":
    main()
