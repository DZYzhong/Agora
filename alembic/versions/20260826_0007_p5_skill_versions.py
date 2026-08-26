"""P5 skill versions.

Revision ID: 20260826_0007
Revises: 20260825_0006
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_0007"
down_revision = "20260825_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("skills", sa.Column("current_version_id", sa.String(), nullable=True))
    op.create_index("ix_skills_current_version_id", "skills", ["current_version_id"])

    op.add_column("skill_runs", sa.Column("skill_version_id", sa.String(), nullable=True))
    op.create_index("ix_skill_runs_skill_version_id", "skill_runs", ["skill_version_id"])

    op.add_column("work_sessions", sa.Column("skill_version_id", sa.String(), nullable=True))
    op.create_index("ix_work_sessions_skill_version_id", "work_sessions", ["skill_version_id"])

    op.create_table(
        "skill_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=True),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("skill_id", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("approved_by_user_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.UniqueConstraint("skill_id", "version", name="uq_skill_versions_skill_version"),
    )
    op.create_index("ix_skill_versions_org_id", "skill_versions", ["org_id"])
    op.create_index("ix_skill_versions_project_id", "skill_versions", ["project_id"])
    op.create_index("ix_skill_versions_skill_id", "skill_versions", ["skill_id"])
    op.create_index("ix_skill_versions_status", "skill_versions", ["status"])
    op.create_index("ix_skill_versions_approved_by_user_id", "skill_versions", ["approved_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_skill_versions_approved_by_user_id", table_name="skill_versions")
    op.drop_index("ix_skill_versions_status", table_name="skill_versions")
    op.drop_index("ix_skill_versions_skill_id", table_name="skill_versions")
    op.drop_index("ix_skill_versions_project_id", table_name="skill_versions")
    op.drop_index("ix_skill_versions_org_id", table_name="skill_versions")
    op.drop_table("skill_versions")

    op.drop_index("ix_work_sessions_skill_version_id", table_name="work_sessions")
    op.drop_column("work_sessions", "skill_version_id")

    op.drop_index("ix_skill_runs_skill_version_id", table_name="skill_runs")
    op.drop_column("skill_runs", "skill_version_id")

    op.drop_index("ix_skills_current_version_id", table_name="skills")
    op.drop_column("skills", "current_version_id")
