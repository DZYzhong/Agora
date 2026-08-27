from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, func, select

from packages.core.models import OutboxEventModel


@dataclass(frozen=True)
class RetentionPolicy:
    export_retention_days: int = 30
    outbox_retention_days: int = 14

    def __post_init__(self):
        if self.export_retention_days < 1:
            raise ValueError("export_retention_days must be at least 1")
        if self.outbox_retention_days < 1:
            raise ValueError("outbox_retention_days must be at least 1")


def build_retention_summary(session, *, export_dir: Path | None, policy: RetentionPolicy) -> dict:
    export_candidates = _export_candidates(export_dir, retention_days=policy.export_retention_days)
    outbox_counts = _outbox_candidate_counts(session, retention_days=policy.outbox_retention_days)
    return {
        "format": "agora-retention-summary/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "export_retention_days": policy.export_retention_days,
            "outbox_retention_days": policy.outbox_retention_days,
        },
        "exports": {
            "directory": str(export_dir.expanduser().resolve()) if export_dir else None,
            "candidates": len(export_candidates),
            "candidate_paths": [str(path) for path in export_candidates],
        },
        "outbox": {
            "terminal_statuses": ["completed", "dead"],
            "candidates_by_status": outbox_counts,
            "candidate_total": sum(outbox_counts.values()),
        },
    }


def cleanup_retention(session, *, export_dir: Path | None, policy: RetentionPolicy) -> dict:
    summary = build_retention_summary(session, export_dir=export_dir, policy=policy)
    deleted_exports = 0
    for candidate in summary["exports"]["candidate_paths"]:
        path = Path(candidate)
        if path.is_dir():
            shutil.rmtree(path)
            deleted_exports += 1
        elif path.exists():
            path.unlink()
            deleted_exports += 1
    deleted_outbox = _delete_outbox_candidates(session, retention_days=policy.outbox_retention_days)
    summary["exports"]["deleted"] = deleted_exports
    summary["outbox"]["deleted"] = deleted_outbox
    return summary


def _export_candidates(export_dir: Path | None, *, retention_days: int) -> list[Path]:
    if export_dir is None:
        return []
    root = export_dir.expanduser().resolve()
    if not root.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    candidates = []
    for child in root.iterdir():
        modified = datetime.fromtimestamp(child.stat().st_mtime, timezone.utc)
        if modified < cutoff:
            candidates.append(child.resolve())
    return sorted(candidates)


def _outbox_candidate_counts(session, *, retention_days: int) -> dict[str, int]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    rows = session.execute(
        select(OutboxEventModel.status, func.count())
        .where(OutboxEventModel.status.in_(["completed", "dead"]))
        .where(OutboxEventModel.updated_at < cutoff)
        .group_by(OutboxEventModel.status)
        .order_by(OutboxEventModel.status)
    ).all()
    return {str(status): int(count) for status, count in rows}


def _delete_outbox_candidates(session, *, retention_days: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    result = session.execute(
        delete(OutboxEventModel)
        .where(OutboxEventModel.status.in_(["completed", "dead"]))
        .where(OutboxEventModel.updated_at < cutoff)
    )
    return int(result.rowcount or 0)
