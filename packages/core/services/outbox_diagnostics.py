from datetime import datetime, timezone

from sqlalchemy import func, or_, select

from packages.core.models import OutboxEventModel


def build_outbox_summary(session, *, max_attempts: int = 3, dead_limit: int = 10) -> dict:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if dead_limit < 1:
        raise ValueError("dead_limit must be at least 1")
    return {
        "format": "agora-outbox-summary/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": _count_total(session),
        "by_status": _count_by(session, OutboxEventModel.status),
        "by_type": _count_by(session, OutboxEventModel.type),
        "retryable": _count_retryable(session, max_attempts=max_attempts),
        "dead_events": _dead_event_samples(session, limit=dead_limit),
    }


def _count_total(session) -> int:
    return int(session.scalar(select(func.count()).select_from(OutboxEventModel)) or 0)


def _count_by(session, column) -> dict[str, int]:
    rows = session.execute(
        select(column, func.count()).select_from(OutboxEventModel).group_by(column).order_by(column)
    ).all()
    return {str(key): int(count) for key, count in rows}


def _count_retryable(session, *, max_attempts: int) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(OutboxEventModel)
            .where(
                or_(
                    OutboxEventModel.status == "pending",
                    (OutboxEventModel.status == "failed") & (OutboxEventModel.attempts < max_attempts),
                )
            )
        )
        or 0
    )


def _dead_event_samples(session, *, limit: int) -> list[dict]:
    events = session.scalars(
        select(OutboxEventModel)
        .where(OutboxEventModel.status == "dead")
        .order_by(OutboxEventModel.updated_at.desc(), OutboxEventModel.id.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": event.id,
            "org_id": event.org_id,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": event.aggregate_id,
            "type": event.type,
            "attempts": event.attempts,
            "last_error": event.last_error,
            "idempotency_key": event.idempotency_key,
            "updated_at": event.updated_at.isoformat() if event.updated_at else None,
        }
        for event in events
    ]
