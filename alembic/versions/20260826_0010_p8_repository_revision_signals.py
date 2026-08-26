"""P8 repository revision signals.

Revision ID: 20260826_0010
Revises: 20260826_0009
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_0010"
down_revision = "20260826_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repository_revision_signals",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("work_item_id", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("repository_identity", sa.String(), nullable=False),
        sa.Column("branch", sa.String(), nullable=False),
        sa.Column("observed_head_sha", sa.String(), nullable=False),
        sa.Column("previous_head_sha", sa.String(), nullable=True),
        sa.Column("signal_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("raw_ref", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_repository_revision_signals_org_id", "repository_revision_signals", ["org_id"])
    op.create_index("ix_repository_revision_signals_project_id", "repository_revision_signals", ["project_id"])
    op.create_index("ix_repository_revision_signals_work_item_id", "repository_revision_signals", ["work_item_id"])
    op.create_index("ix_repository_revision_signals_provider", "repository_revision_signals", ["provider"])
    op.create_index("ix_repository_revision_signals_branch", "repository_revision_signals", ["branch"])
    op.create_index("ix_repository_revision_signals_observed_head_sha", "repository_revision_signals", ["observed_head_sha"])
    op.create_index("ix_repository_revision_signals_signal_type", "repository_revision_signals", ["signal_type"])
    op.create_index("ix_repository_revision_signals_status", "repository_revision_signals", ["status"])
    op.create_index("ix_repository_revision_signals_created_by_user_id", "repository_revision_signals", ["created_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_repository_revision_signals_created_by_user_id", table_name="repository_revision_signals")
    op.drop_index("ix_repository_revision_signals_status", table_name="repository_revision_signals")
    op.drop_index("ix_repository_revision_signals_signal_type", table_name="repository_revision_signals")
    op.drop_index("ix_repository_revision_signals_observed_head_sha", table_name="repository_revision_signals")
    op.drop_index("ix_repository_revision_signals_branch", table_name="repository_revision_signals")
    op.drop_index("ix_repository_revision_signals_provider", table_name="repository_revision_signals")
    op.drop_index("ix_repository_revision_signals_work_item_id", table_name="repository_revision_signals")
    op.drop_index("ix_repository_revision_signals_project_id", table_name="repository_revision_signals")
    op.drop_index("ix_repository_revision_signals_org_id", table_name="repository_revision_signals")
    op.drop_table("repository_revision_signals")
