from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Callable

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from packages.core.models import OutboxEventModel, utc_now


OutboxHandler = Callable[[OutboxEventModel], None]

DEFAULT_LEASE_TIMEOUT = timedelta(minutes=5)


@dataclass(frozen=True)
class OutboxProcessResult:
    processed: int = 0
    completed: int = 0
    failed: int = 0
    dead: int = 0
    reclaimed: int = 0


class OutboxProcessor:
    """Process outbox events with lease-based, cross-worker-safe claiming.

    Each event is claimed atomically (``pending|failed -> processing`` with a
    lease timestamp) and the claim is committed before the handler runs, so
    concurrent workers never double-process. Outcomes are committed per event,
    so one failing handler cannot roll back other completions. Stale leases
    (crashed workers) are reclaimed after the lease timeout.
    """

    def __init__(
        self,
        session: Session,
        *,
        handlers: dict[str, OutboxHandler],
        max_attempts: int = 3,
        lease_timeout: timedelta = DEFAULT_LEASE_TIMEOUT,
    ):
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.session = session
        self.handlers = handlers
        self.max_attempts = max_attempts
        self.lease_timeout = lease_timeout

    def process_next_batch(self, *, limit: int = 20) -> OutboxProcessResult:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        reclaimed = self._reclaim_stale_leases()
        candidate_ids = self._list_candidates(limit=limit)
        processed = 0
        completed = 0
        failed = 0
        dead = 0
        for event_id in candidate_ids:
            if not self._claim(event_id):
                continue  # another worker claimed it
            processed += 1
            outcome = self._process_claimed(event_id)
            if outcome == "completed":
                completed += 1
            elif outcome == "dead":
                dead += 1
            else:
                failed += 1
        return OutboxProcessResult(
            processed=processed,
            completed=completed,
            failed=failed,
            dead=dead,
            reclaimed=reclaimed,
        )

    def _list_candidates(self, *, limit: int) -> list[str]:
        statement = (
            select(OutboxEventModel.id)
            .where(
                or_(
                    OutboxEventModel.status == "pending",
                    (OutboxEventModel.status == "failed") & (OutboxEventModel.attempts < self.max_attempts),
                )
            )
            .order_by(OutboxEventModel.created_at, OutboxEventModel.id)
            .limit(limit)
        )
        return list(self.session.scalars(statement).all())

    def _claim(self, event_id: str) -> bool:
        result = self.session.execute(
            update(OutboxEventModel)
            .where(
                OutboxEventModel.id == event_id,
                or_(
                    OutboxEventModel.status == "pending",
                    OutboxEventModel.status == "failed",
                ),
            )
            .values(
                status="processing",
                processing_started_at=utc_now(),
                attempts=OutboxEventModel.attempts + 1,
            )
        )
        self.session.commit()
        return result.rowcount == 1

    def _process_claimed(self, event_id: str) -> str:
        event = self.session.get(OutboxEventModel, event_id)
        if event is None:
            self.session.commit()
            return "failed"
        handler = self.handlers.get(event.type)
        try:
            if handler is None:
                raise RuntimeError(f"No outbox handler registered for event type: {event.type}")
            handler(event)
        except Exception as exc:
            event.last_error = str(exc)
            event.processing_started_at = None
            if event.attempts >= self.max_attempts:
                event.status = "dead"
            else:
                event.status = "failed"
            self.session.commit()
            return "dead" if event.attempts >= self.max_attempts else "failed"
        event.status = "completed"
        event.last_error = None
        event.processing_started_at = None
        self.session.commit()
        return "completed"

    def _reclaim_stale_leases(self) -> int:
        cutoff = utc_now() - self.lease_timeout
        result = self.session.execute(
            update(OutboxEventModel)
            .where(
                OutboxEventModel.status == "processing",
                OutboxEventModel.processing_started_at.is_not(None),
                OutboxEventModel.processing_started_at < cutoff,
            )
            .values(status="pending", processing_started_at=None)
        )
        self.session.commit()
        return result.rowcount
