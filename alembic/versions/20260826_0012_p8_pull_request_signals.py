"""P8 pull request signals.

Revision ID: 20260826_0012
Revises: 20260826_0011
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_0012"
down_revision = "20260826_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pull_request_signals",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("work_item_id", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("repository_identity", sa.String(), nullable=False),
        sa.Column("pull_request_id", sa.String(), nullable=False),
        sa.Column("pull_request_url", sa.Text(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("source_branch", sa.String(), nullable=True),
        sa.Column("target_branch", sa.String(), nullable=False),
        sa.Column("head_sha", sa.String(), nullable=True),
        sa.Column("merge_commit_sha", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_pull_request_signals_org_id", "pull_request_signals", ["org_id"])
    op.create_index("ix_pull_request_signals_project_id", "pull_request_signals", ["project_id"])
    op.create_index("ix_pull_request_signals_work_item_id", "pull_request_signals", ["work_item_id"])
    op.create_index("ix_pull_request_signals_provider", "pull_request_signals", ["provider"])
    op.create_index("ix_pull_request_signals_repository_identity", "pull_request_signals", ["repository_identity"])
    op.create_index("ix_pull_request_signals_pull_request_id", "pull_request_signals", ["pull_request_id"])
    op.create_index("ix_pull_request_signals_action", "pull_request_signals", ["action"])
    op.create_index("ix_pull_request_signals_status", "pull_request_signals", ["status"])
    op.create_index("ix_pull_request_signals_created_by_user_id", "pull_request_signals", ["created_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_pull_request_signals_created_by_user_id", table_name="pull_request_signals")
    op.drop_index("ix_pull_request_signals_status", table_name="pull_request_signals")
    op.drop_index("ix_pull_request_signals_action", table_name="pull_request_signals")
    op.drop_index("ix_pull_request_signals_pull_request_id", table_name="pull_request_signals")
    op.drop_index("ix_pull_request_signals_repository_identity", table_name="pull_request_signals")
    op.drop_index("ix_pull_request_signals_provider", table_name="pull_request_signals")
    op.drop_index("ix_pull_request_signals_work_item_id", table_name="pull_request_signals")
    op.drop_index("ix_pull_request_signals_project_id", table_name="pull_request_signals")
    op.drop_index("ix_pull_request_signals_org_id", table_name="pull_request_signals")
    op.drop_table("pull_request_signals")
