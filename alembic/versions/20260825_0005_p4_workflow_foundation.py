"""P4 workflow foundation.

Revision ID: 20260825_0005
Revises: 20260825_0004
Create Date: 2026-08-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260825_0005"
down_revision = "20260825_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("work_items", sa.Column("workflow_version_id", sa.String(), nullable=True))
    op.add_column("work_items", sa.Column("workflow_execution_id", sa.String(), nullable=True))
    op.create_index("ix_work_items_workflow_version_id", "work_items", ["workflow_version_id"])
    op.create_index("ix_work_items_workflow_execution_id", "work_items", ["workflow_execution_id"])

    op.add_column("work_sessions", sa.Column("workflow_version_id", sa.String(), nullable=True))
    op.add_column("work_sessions", sa.Column("workflow_execution_id", sa.String(), nullable=True))
    op.create_index("ix_work_sessions_workflow_version_id", "work_sessions", ["workflow_version_id"])
    op.create_index("ix_work_sessions_workflow_execution_id", "work_sessions", ["workflow_execution_id"])

    op.create_table(
        "workflow_definitions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("org_id", "project_id", "slug", name="uq_workflow_definitions_scope_slug"),
    )
    op.create_index("ix_workflow_definitions_org_id", "workflow_definitions", ["org_id"])
    op.create_index("ix_workflow_definitions_project_id", "workflow_definitions", ["project_id"])
    op.create_index("ix_workflow_definitions_slug", "workflow_definitions", ["slug"])
    op.create_index("ix_workflow_definitions_status", "workflow_definitions", ["status"])

    op.create_table(
        "workflow_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("workflow_definition_id", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("policy", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["workflow_definition_id"], ["workflow_definitions.id"]),
        sa.UniqueConstraint("workflow_definition_id", "version", name="uq_workflow_versions_definition_version"),
    )
    op.create_index("ix_workflow_versions_org_id", "workflow_versions", ["org_id"])
    op.create_index("ix_workflow_versions_project_id", "workflow_versions", ["project_id"])
    op.create_index("ix_workflow_versions_workflow_definition_id", "workflow_versions", ["workflow_definition_id"])
    op.create_index("ix_workflow_versions_status", "workflow_versions", ["status"])

    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("work_item_id", sa.String(), nullable=False),
        sa.Column("workflow_version_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_step_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"]),
        sa.ForeignKeyConstraint(["workflow_version_id"], ["workflow_versions.id"]),
        sa.UniqueConstraint("work_item_id", name="uq_workflow_executions_work_item"),
    )
    op.create_index("ix_workflow_executions_org_id", "workflow_executions", ["org_id"])
    op.create_index("ix_workflow_executions_project_id", "workflow_executions", ["project_id"])
    op.create_index("ix_workflow_executions_work_item_id", "workflow_executions", ["work_item_id"])
    op.create_index("ix_workflow_executions_workflow_version_id", "workflow_executions", ["workflow_version_id"])
    op.create_index("ix_workflow_executions_status", "workflow_executions", ["status"])
    op.create_index("ix_workflow_executions_current_step_key", "workflow_executions", ["current_step_key"])

    op.create_table(
        "workflow_step_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("workflow_execution_id", sa.String(), nullable=False),
        sa.Column("work_item_id", sa.String(), nullable=False),
        sa.Column("step_key", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("required_artifacts", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["workflow_execution_id"], ["workflow_executions.id"]),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"]),
        sa.UniqueConstraint("workflow_execution_id", "step_key", name="uq_workflow_step_runs_execution_step"),
    )
    op.create_index("ix_workflow_step_runs_org_id", "workflow_step_runs", ["org_id"])
    op.create_index("ix_workflow_step_runs_project_id", "workflow_step_runs", ["project_id"])
    op.create_index("ix_workflow_step_runs_workflow_execution_id", "workflow_step_runs", ["workflow_execution_id"])
    op.create_index("ix_workflow_step_runs_work_item_id", "workflow_step_runs", ["work_item_id"])
    op.create_index("ix_workflow_step_runs_step_key", "workflow_step_runs", ["step_key"])
    op.create_index("ix_workflow_step_runs_status", "workflow_step_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_workflow_step_runs_status", table_name="workflow_step_runs")
    op.drop_index("ix_workflow_step_runs_step_key", table_name="workflow_step_runs")
    op.drop_index("ix_workflow_step_runs_work_item_id", table_name="workflow_step_runs")
    op.drop_index("ix_workflow_step_runs_workflow_execution_id", table_name="workflow_step_runs")
    op.drop_index("ix_workflow_step_runs_project_id", table_name="workflow_step_runs")
    op.drop_index("ix_workflow_step_runs_org_id", table_name="workflow_step_runs")
    op.drop_table("workflow_step_runs")

    op.drop_index("ix_workflow_executions_current_step_key", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_status", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_workflow_version_id", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_work_item_id", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_project_id", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_org_id", table_name="workflow_executions")
    op.drop_table("workflow_executions")

    op.drop_index("ix_workflow_versions_status", table_name="workflow_versions")
    op.drop_index("ix_workflow_versions_workflow_definition_id", table_name="workflow_versions")
    op.drop_index("ix_workflow_versions_project_id", table_name="workflow_versions")
    op.drop_index("ix_workflow_versions_org_id", table_name="workflow_versions")
    op.drop_table("workflow_versions")

    op.drop_index("ix_workflow_definitions_status", table_name="workflow_definitions")
    op.drop_index("ix_workflow_definitions_slug", table_name="workflow_definitions")
    op.drop_index("ix_workflow_definitions_project_id", table_name="workflow_definitions")
    op.drop_index("ix_workflow_definitions_org_id", table_name="workflow_definitions")
    op.drop_table("workflow_definitions")

    op.drop_index("ix_work_sessions_workflow_execution_id", table_name="work_sessions")
    op.drop_index("ix_work_sessions_workflow_version_id", table_name="work_sessions")
    op.drop_column("work_sessions", "workflow_execution_id")
    op.drop_column("work_sessions", "workflow_version_id")

    op.drop_index("ix_work_items_workflow_execution_id", table_name="work_items")
    op.drop_index("ix_work_items_workflow_version_id", table_name="work_items")
    op.drop_column("work_items", "workflow_execution_id")
    op.drop_column("work_items", "workflow_version_id")
