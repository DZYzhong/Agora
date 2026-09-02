"""PR2 outbox lease columns.

Revision ID: 20260902_0016
Revises: 20260902_0015
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260902_0016"
down_revision = "20260902_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("outbox_events") as batch_op:
        batch_op.add_column(sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_outbox_events_processing_started_at", "outbox_events", ["processing_started_at"])


def downgrade() -> None:
    op.drop_index("ix_outbox_events_processing_started_at", table_name="outbox_events")
    with op.batch_alter_table("outbox_events") as batch_op:
        batch_op.drop_column("processing_started_at")
