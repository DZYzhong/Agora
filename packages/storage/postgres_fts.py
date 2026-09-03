"""PR4: PostgreSQL full-text search adapter (20260902_0019).

The runtime still uses the in-process Fake indexes for context assembly; this
module provides the real PostgreSQL retrieval path over the generated
`assets.search_tsv` column (simple-dictionary tsvector over
title + content + summary) with a GIN index. Search endpoints switch over in
a later PR4 batch; this module and its tests prove the retrieval path and
rebuild semantics.

Search is scoped by project (and optionally org/type) and ranked by ts_rank.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine


def search_assets(
    connection: Connection,
    *,
    project_id: str,
    query: str,
    org_id: str | None = None,
    type_filter: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Ranked full-text search over a project's assets (PostgreSQL only)."""
    clauses = ["search_tsv @@ plainto_tsquery('simple', :query)", "project_id = :project_id"]
    params: dict[str, Any] = {"query": query, "project_id": project_id, "limit": limit}
    if org_id is not None:
        clauses.append("org_id = :org_id")
        params["org_id"] = org_id
    if type_filter is not None:
        clauses.append("type = :type_filter")
        params["type_filter"] = type_filter
    statement = (
        "SELECT id, type, source, source_uri, title, summary, "
        "ts_rank(search_tsv, plainto_tsquery('simple', :query)) AS rank "
        f"FROM assets WHERE {' AND '.join(clauses)} "
        "ORDER BY rank DESC, id ASC LIMIT :limit"
    )
    rows = connection.execute(text(statement), params).mappings().all()
    return [dict(row) for row in rows]


def has_fts_support(engine: Engine) -> bool:
    """True when the database actually carries the FTS column (PostgreSQL)."""
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'assets' AND column_name = 'search_tsv'"
            )
        ).first()
        return row is not None


def rebuild_signal(engine: Engine) -> dict[str, Any]:
    """Confirm the generated column covers existing rows (rebuild proof).

    Generated stored columns are backfilled by PostgreSQL on migration, so
    this returns counts; a VACUUM/REINDEX is unnecessary for correctness.
    """
    with engine.connect() as connection:
        total = connection.execute(text("SELECT count(*) FROM assets")).scalar()
        nonempty = connection.execute(
            text("SELECT count(*) FROM assets WHERE search_tsv IS NOT NULL")
        ).scalar()
        return {"total_assets": int(total or 0), "fts_indexed": int(nonempty or 0)}
