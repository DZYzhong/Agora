from __future__ import annotations

import threading
from typing import Callable

from sqlalchemy.orm import Session

from packages.core.models import OutboxEventModel
from packages.core.services.outbox import OutboxProcessResult, OutboxProcessor
from packages.core.services.runtime import CoreRuntime


def process_outbox_once(session: Session, *, limit: int = 20, max_attempts: int = 3) -> OutboxProcessResult:
    # The processor owns transaction boundaries (per-claim and per-outcome
    # commits) for lease-based cross-worker safety; do not wrap in a UoW here.
    runtime = CoreRuntime(session)
    processor = OutboxProcessor(
        session,
        handlers={"context_head_changed": _context_head_changed_handler(runtime)},
        max_attempts=max_attempts,
    )
    return processor.process_next_batch(limit=limit)


def run_worker_loop(
    session_factory: Callable[[], Session],
    *,
    max_attempts: int = 3,
    batch_limit: int = 20,
    idle_delay: float = 1.0,
    shutdown_event: threading.Event | None = None,
) -> int:
    """Run the persistent outbox worker until the shutdown event is set.

    Returns the total number of events processed. The shutdown event doubles as
    the backoff sleep, so SIGTERM stops the loop promptly even while idle.
    """
    shutdown = shutdown_event or threading.Event()
    processed_total = 0
    while not shutdown.is_set():
        with session_factory() as session:
            result = process_outbox_once(session, limit=batch_limit, max_attempts=max_attempts)
        processed_total += result.processed
        if result.processed == 0:
            if shutdown.wait(idle_delay):
                break
        elif shutdown.wait(0.05):
            break
    return processed_total


def _context_head_changed_handler(runtime: CoreRuntime):
    def handle(event: OutboxEventModel) -> None:
        payload = event.payload or {}
        stream_id = payload.get("stream_id")
        revision_id = payload.get("revision_id")
        proposal_id = payload.get("proposal_id")
        if not stream_id or not revision_id or not proposal_id:
            raise RuntimeError("context_head_changed payload is missing stream_id, revision_id or proposal_id")
        stream = runtime.get_context_stream(stream_id)
        if stream is None:
            raise RuntimeError(f"Context stream not found for outbox event: {stream_id}")
        if stream.head_revision_id != revision_id:
            raise RuntimeError(
                f"Outbox revision {revision_id} does not match stream head {stream.head_revision_id}"
            )
        revision = runtime.get_context_revision(revision_id)
        if revision is None:
            raise RuntimeError(f"Context revision not found for outbox event: {revision_id}")
        if revision.stream_id != stream.id:
            raise RuntimeError(f"Context revision {revision_id} does not belong to stream {stream.id}")
        proposal = runtime.get_context_proposal(proposal_id)
        if proposal is None:
            raise RuntimeError(f"Context proposal not found for outbox event: {proposal_id}")
        if proposal.accepted_revision_id != revision.id:
            raise RuntimeError(
                f"Context proposal {proposal_id} does not point at accepted revision {revision.id}"
            )

    return handle
