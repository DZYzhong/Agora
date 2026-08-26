"""P6 quality evidence.

Revision ID: 20260826_0008
Revises: 20260826_0007
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_0008"
down_revision = "20260826_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quality_evidence",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("work_item_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("evidence_type", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("conclusion", sa.Text(), nullable=False),
        sa.Column("command", sa.Text(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("raw_ref", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["work_sessions.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_quality_evidence_org_id", "quality_evidence", ["org_id"])
    op.create_index("ix_quality_evidence_project_id", "quality_evidence", ["project_id"])
    op.create_index("ix_quality_evidence_work_item_id", "quality_evidence", ["work_item_id"])
    op.create_index("ix_quality_evidence_session_id", "quality_evidence", ["session_id"])
    op.create_index("ix_quality_evidence_evidence_type", "quality_evidence", ["evidence_type"])
    op.create_index("ix_quality_evidence_source", "quality_evidence", ["source"])
    op.create_index("ix_quality_evidence_status", "quality_evidence", ["status"])
    op.create_index("ix_quality_evidence_created_by_user_id", "quality_evidence", ["created_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_quality_evidence_created_by_user_id", table_name="quality_evidence")
    op.drop_index("ix_quality_evidence_status", table_name="quality_evidence")
    op.drop_index("ix_quality_evidence_source", table_name="quality_evidence")
    op.drop_index("ix_quality_evidence_evidence_type", table_name="quality_evidence")
    op.drop_index("ix_quality_evidence_session_id", table_name="quality_evidence")
    op.drop_index("ix_quality_evidence_work_item_id", table_name="quality_evidence")
    op.drop_index("ix_quality_evidence_project_id", table_name="quality_evidence")
    op.drop_index("ix_quality_evidence_org_id", table_name="quality_evidence")
    op.drop_table("quality_evidence")
