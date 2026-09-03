"""PR4: PostgreSQL full-text search index on assets (PostgreSQL only).

Revision ID: 20260902_0019
Revises: 20260902_0018
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260902_0019"
down_revision = "20260902_0018"
branch_labels = None
depends_on = None

_DDL = """
ALTER TABLE assets
  ADD COLUMN search_tsv tsvector
  GENERATED ALWAYS AS (
    to_tsvector('simple',
      coalesce(title, '') || ' ' ||
      coalesce(content, '') || ' ' ||
      coalesce(summary, ''))
  ) STORED;
CREATE INDEX ix_assets_search_tsv_gin ON assets USING GIN (search_tsv);
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite (and the canonical signature replay) never carries FTS; the
        # fingerprint check excludes the PG-only artifacts explicitly.
        return
    op.execute(_DDL)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP INDEX IF EXISTS ix_assets_search_tsv_gin")
    op.execute("ALTER TABLE assets DROP COLUMN IF EXISTS search_tsv")
