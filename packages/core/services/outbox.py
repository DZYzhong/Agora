from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from packages.core.models import OutboxEventModel


OutboxHandler = Callable[[OutboxEventModel], None]


@dataclass(frozen=True)
class OutboxProcessResult:
    processed: int = 0
    completed: int = 0
    failed: int = 0
    dead: int = 0


class OutboxProcessor:
    def __init__(self, session: Session, *, handlers: dict[str, OutboxHandler], max_attempts: int = 3):
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.session = session
        self.handlers = handlers
        self.max_attempts = max_attempts

    def process_next_batch(self, *, limit: int = 20) -> OutboxProcessResult:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        events = self._list_retryable(limit=limit)
        completed = 0
        failed = 0
        dead = 0
        for event in events:
            outcome = self._process_event(event)
            if outcome == "completed":
                completed += 1
            elif outcome == "dead":
                dead += 1
            else:
                failed += 1
        return OutboxProcessResult(
            processed=len(events),
            completed=completed,
            failed=failed,
            dead=dead,
        )

    def _list_retryable(self, *, limit: int) -> list[OutboxEventModel]:
        statement = (
            select(OutboxEventModel)
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

    def _process_event(self, event: OutboxEventModel) -> str:
        handler = self.handlers.get(event.type)
        event.attempts += 1
        try:
            if handler is None:
                raise RuntimeError(f"No outbox handler registered for event type: {event.type}")
            handler(event)
        except Exception as exc:
            event.last_error = str(exc)
            if event.attempts >= self.max_attempts:
                event.status = "dead"
                return "dead"
            event.status = "failed"
            return "failed"
        event.status = "completed"
        event.last_error = None
        return "completed"
