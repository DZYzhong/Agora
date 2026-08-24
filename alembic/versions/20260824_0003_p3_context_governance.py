"""P3 context governance foundation.

Revision ID: 20260824_0003
Revises: 20260814_0002
Create Date: 2026-08-24 00:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260824_0003"
down_revision: str | None = "20260814_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "context_streams",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("branch", sa.String(), nullable=False),
        sa.Column("repository_identity", sa.JSON(), nullable=False),
        sa.Column("head_revision_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "name", "branch", name="uq_context_streams_project_name_branch"),
    )
    op.create_index("ix_context_streams_org_id", "context_streams", ["org_id"])
    op.create_index("ix_context_streams_project_id", "context_streams", ["project_id"])
    op.create_index("ix_context_streams_status", "context_streams", ["status"])

    op.create_table(
        "context_revisions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("stream_id", sa.String(), sa.ForeignKey("context_streams.id"), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("parent_revision_id", sa.String(), nullable=True),
        sa.Column("commit_sha", sa.String(), nullable=True),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("source_anchors", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_context_revisions_org_id", "context_revisions", ["org_id"])
    op.create_index("ix_context_revisions_project_id", "context_revisions", ["project_id"])
    op.create_index("ix_context_revisions_stream_id", "context_revisions", ["stream_id"])

    op.create_table(
        "context_proposals",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("stream_id", sa.String(), sa.ForeignKey("context_streams.id"), nullable=False),
        sa.Column("work_item_id", sa.String(), nullable=True),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("source_anchors", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("target_branch", sa.String(), nullable=False),
        sa.Column("expected_head_revision_id", sa.String(), nullable=True),
        sa.Column("from_commit_sha", sa.String(), nullable=True),
        sa.Column("to_commit_sha", sa.String(), nullable=True),
        sa.Column("created_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewed_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("accepted_revision_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_context_proposals_org_id", "context_proposals", ["org_id"])
    op.create_index("ix_context_proposals_project_id", "context_proposals", ["project_id"])
    op.create_index("ix_context_proposals_stream_id", "context_proposals", ["stream_id"])
    op.create_index("ix_context_proposals_status", "context_proposals", ["status"])

    op.create_table(
        "approval_decisions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("proposal_id", sa.String(), sa.ForeignKey("context_proposals.id"), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("decided_by_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_approval_decisions_project_id", "approval_decisions", ["project_id"])
    op.create_index("ix_approval_decisions_proposal_id", "approval_decisions", ["proposal_id"])

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("aggregate_type", sa.String(), nullable=False),
        sa.Column("aggregate_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_outbox_events_idempotency_key"),
    )
    op.create_index("ix_outbox_events_org_id", "outbox_events", ["org_id"])
    op.create_index("ix_outbox_events_status", "outbox_events", ["status"])
    op.create_index("ix_outbox_events_type", "outbox_events", ["type"])


def downgrade() -> None:
    op.drop_index("ix_outbox_events_type", table_name="outbox_events")
    op.drop_index("ix_outbox_events_status", table_name="outbox_events")
    op.drop_index("ix_outbox_events_org_id", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index("ix_approval_decisions_proposal_id", table_name="approval_decisions")
    op.drop_index("ix_approval_decisions_project_id", table_name="approval_decisions")
    op.drop_table("approval_decisions")
    op.drop_index("ix_context_proposals_status", table_name="context_proposals")
    op.drop_index("ix_context_proposals_stream_id", table_name="context_proposals")
    op.drop_index("ix_context_proposals_project_id", table_name="context_proposals")
    op.drop_index("ix_context_proposals_org_id", table_name="context_proposals")
    op.drop_table("context_proposals")
    op.drop_index("ix_context_revisions_stream_id", table_name="context_revisions")
    op.drop_index("ix_context_revisions_project_id", table_name="context_revisions")
    op.drop_index("ix_context_revisions_org_id", table_name="context_revisions")
    op.drop_table("context_revisions")
    op.drop_index("ix_context_streams_status", table_name="context_streams")
    op.drop_index("ix_context_streams_project_id", table_name="context_streams")
    op.drop_index("ix_context_streams_org_id", table_name="context_streams")
    op.drop_table("context_streams")
