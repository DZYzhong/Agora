"""P4 work artifacts and human confirmations.

Revision ID: 20260825_0006
Revises: 20260825_0005
Create Date: 2026-08-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260825_0006"
down_revision = "20260825_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_artifacts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("work_item_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("workflow_execution_id", sa.String(), nullable=False),
        sa.Column("workflow_step_run_id", sa.String(), nullable=False),
        sa.Column("step_key", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("artifact_metadata", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["work_sessions.id"]),
        sa.ForeignKeyConstraint(["workflow_execution_id"], ["workflow_executions.id"]),
        sa.ForeignKeyConstraint(["workflow_step_run_id"], ["workflow_step_runs.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_work_artifacts_org_id", "work_artifacts", ["org_id"])
    op.create_index("ix_work_artifacts_project_id", "work_artifacts", ["project_id"])
    op.create_index("ix_work_artifacts_work_item_id", "work_artifacts", ["work_item_id"])
    op.create_index("ix_work_artifacts_session_id", "work_artifacts", ["session_id"])
    op.create_index("ix_work_artifacts_workflow_execution_id", "work_artifacts", ["workflow_execution_id"])
    op.create_index("ix_work_artifacts_workflow_step_run_id", "work_artifacts", ["workflow_step_run_id"])
    op.create_index("ix_work_artifacts_step_key", "work_artifacts", ["step_key"])
    op.create_index("ix_work_artifacts_type", "work_artifacts", ["type"])
    op.create_index("ix_work_artifacts_created_by_user_id", "work_artifacts", ["created_by_user_id"])

    op.create_table(
        "human_confirmations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("work_item_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("workflow_execution_id", sa.String(), nullable=False),
        sa.Column("workflow_step_run_id", sa.String(), nullable=False),
        sa.Column("step_key", sa.String(), nullable=False),
        sa.Column("confirmation_type", sa.String(), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("confirmed_by_user_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["work_sessions.id"]),
        sa.ForeignKeyConstraint(["workflow_execution_id"], ["workflow_executions.id"]),
        sa.ForeignKeyConstraint(["workflow_step_run_id"], ["workflow_step_runs.id"]),
        sa.ForeignKeyConstraint(["confirmed_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_human_confirmations_org_id", "human_confirmations", ["org_id"])
    op.create_index("ix_human_confirmations_project_id", "human_confirmations", ["project_id"])
    op.create_index("ix_human_confirmations_work_item_id", "human_confirmations", ["work_item_id"])
    op.create_index("ix_human_confirmations_session_id", "human_confirmations", ["session_id"])
    op.create_index("ix_human_confirmations_workflow_execution_id", "human_confirmations", ["workflow_execution_id"])
    op.create_index("ix_human_confirmations_workflow_step_run_id", "human_confirmations", ["workflow_step_run_id"])
    op.create_index("ix_human_confirmations_step_key", "human_confirmations", ["step_key"])
    op.create_index("ix_human_confirmations_confirmation_type", "human_confirmations", ["confirmation_type"])
    op.create_index("ix_human_confirmations_decision", "human_confirmations", ["decision"])
    op.create_index("ix_human_confirmations_confirmed_by_user_id", "human_confirmations", ["confirmed_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_human_confirmations_confirmed_by_user_id", table_name="human_confirmations")
    op.drop_index("ix_human_confirmations_decision", table_name="human_confirmations")
    op.drop_index("ix_human_confirmations_confirmation_type", table_name="human_confirmations")
    op.drop_index("ix_human_confirmations_step_key", table_name="human_confirmations")
    op.drop_index("ix_human_confirmations_workflow_step_run_id", table_name="human_confirmations")
    op.drop_index("ix_human_confirmations_workflow_execution_id", table_name="human_confirmations")
    op.drop_index("ix_human_confirmations_session_id", table_name="human_confirmations")
    op.drop_index("ix_human_confirmations_work_item_id", table_name="human_confirmations")
    op.drop_index("ix_human_confirmations_project_id", table_name="human_confirmations")
    op.drop_index("ix_human_confirmations_org_id", table_name="human_confirmations")
    op.drop_table("human_confirmations")

    op.drop_index("ix_work_artifacts_created_by_user_id", table_name="work_artifacts")
    op.drop_index("ix_work_artifacts_type", table_name="work_artifacts")
    op.drop_index("ix_work_artifacts_step_key", table_name="work_artifacts")
    op.drop_index("ix_work_artifacts_workflow_step_run_id", table_name="work_artifacts")
    op.drop_index("ix_work_artifacts_workflow_execution_id", table_name="work_artifacts")
    op.drop_index("ix_work_artifacts_session_id", table_name="work_artifacts")
    op.drop_index("ix_work_artifacts_work_item_id", table_name="work_artifacts")
    op.drop_index("ix_work_artifacts_project_id", table_name="work_artifacts")
    op.drop_index("ix_work_artifacts_org_id", table_name="work_artifacts")
    op.drop_table("work_artifacts")
