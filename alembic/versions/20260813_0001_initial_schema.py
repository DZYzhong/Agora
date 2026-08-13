"""initial schema

Revision ID: 20260813_0001
Revises:
Create Date: 2026-08-13 00:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260813_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("git_remotes", sa.JSON(), nullable=False),
        sa.Column("default_branch", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_projects_org_id", "projects", ["org_id"])
    op.create_index("ix_projects_slug", "projects", ["slug"])

    op.create_table(
        "assets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_uri", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assets_org_id", "assets", ["org_id"])
    op.create_index("ix_assets_project_id", "assets", ["project_id"])
    op.create_index("ix_assets_type", "assets", ["type"])
    op.create_index("ix_assets_source", "assets", ["source"])

    op.create_table(
        "project_initialization_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("repo_path", sa.Text(), nullable=False),
        sa.Column("git_remote", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("asset_count", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_project_initialization_jobs_org_id", "project_initialization_jobs", ["org_id"])
    op.create_index("ix_project_initialization_jobs_project_id", "project_initialization_jobs", ["project_id"])
    op.create_index("ix_project_initialization_jobs_status", "project_initialization_jobs", ["status"])

    op.create_table(
        "context_packs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("key_facts", sa.JSON(), nullable=False),
        sa.Column("source_refs", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_context_packs_org_id", "context_packs", ["org_id"])
    op.create_index("ix_context_packs_project_id", "context_packs", ["project_id"])

    op.create_table(
        "skills",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), nullable=True),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_skills_org_id", "skills", ["org_id"])
    op.create_index("ix_skills_project_id", "skills", ["project_id"])
    op.create_index("ix_skills_slug", "skills", ["slug"])

    op.create_table(
        "skill_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("skill_id", sa.String(), nullable=False),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("output", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_skill_runs_org_id", "skill_runs", ["org_id"])
    op.create_index("ix_skill_runs_project_id", "skill_runs", ["project_id"])
    op.create_index("ix_skill_runs_session_id", "skill_runs", ["session_id"])
    op.create_index("ix_skill_runs_skill_id", "skill_runs", ["skill_id"])

    op.create_table(
        "task_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("agent_type", sa.String(), nullable=False),
        sa.Column("intent", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_task_sessions_org_id", "task_sessions", ["org_id"])
    op.create_index("ix_task_sessions_project_id", "task_sessions", ["project_id"])
    op.create_index("ix_task_sessions_task_id", "task_sessions", ["task_id"])

    op.create_table(
        "session_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_session_events_session_id", "session_events", ["session_id"])

    op.create_table(
        "writebacks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("asset_refs", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("accepted_asset_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_writebacks_org_id", "writebacks", ["org_id"])
    op.create_index("ix_writebacks_project_id", "writebacks", ["project_id"])
    op.create_index("ix_writebacks_session_id", "writebacks", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_writebacks_session_id", table_name="writebacks")
    op.drop_index("ix_writebacks_project_id", table_name="writebacks")
    op.drop_index("ix_writebacks_org_id", table_name="writebacks")
    op.drop_table("writebacks")
    op.drop_index("ix_session_events_session_id", table_name="session_events")
    op.drop_table("session_events")
    op.drop_index("ix_task_sessions_task_id", table_name="task_sessions")
    op.drop_index("ix_task_sessions_project_id", table_name="task_sessions")
    op.drop_index("ix_task_sessions_org_id", table_name="task_sessions")
    op.drop_table("task_sessions")
    op.drop_index("ix_skill_runs_skill_id", table_name="skill_runs")
    op.drop_index("ix_skill_runs_session_id", table_name="skill_runs")
    op.drop_index("ix_skill_runs_project_id", table_name="skill_runs")
    op.drop_index("ix_skill_runs_org_id", table_name="skill_runs")
    op.drop_table("skill_runs")
    op.drop_index("ix_skills_slug", table_name="skills")
    op.drop_index("ix_skills_project_id", table_name="skills")
    op.drop_index("ix_skills_org_id", table_name="skills")
    op.drop_table("skills")
    op.drop_index("ix_context_packs_project_id", table_name="context_packs")
    op.drop_index("ix_context_packs_org_id", table_name="context_packs")
    op.drop_table("context_packs")
    op.drop_index("ix_project_initialization_jobs_status", table_name="project_initialization_jobs")
    op.drop_index("ix_project_initialization_jobs_project_id", table_name="project_initialization_jobs")
    op.drop_index("ix_project_initialization_jobs_org_id", table_name="project_initialization_jobs")
    op.drop_table("project_initialization_jobs")
    op.drop_index("ix_assets_source", table_name="assets")
    op.drop_index("ix_assets_type", table_name="assets")
    op.drop_index("ix_assets_project_id", table_name="assets")
    op.drop_index("ix_assets_org_id", table_name="assets")
    op.drop_table("assets")
    op.drop_index("ix_projects_slug", table_name="projects")
    op.drop_index("ix_projects_org_id", table_name="projects")
    op.drop_table("projects")
