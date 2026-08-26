"""P7 security audit.

Revision ID: 20260826_0009
Revises: 20260826_0008
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_0009"
down_revision = "20260826_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "security_audit_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("actor_user_id", sa.String(), nullable=False),
        sa.Column("actor_credential_id", sa.String(), nullable=True),
        sa.Column("actor_credential_kind", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["actor_credential_id"], ["credentials.id"]),
    )
    op.create_index("ix_security_audit_events_org_id", "security_audit_events", ["org_id"])
    op.create_index("ix_security_audit_events_project_id", "security_audit_events", ["project_id"])
    op.create_index("ix_security_audit_events_actor_user_id", "security_audit_events", ["actor_user_id"])
    op.create_index("ix_security_audit_events_actor_credential_id", "security_audit_events", ["actor_credential_id"])
    op.create_index("ix_security_audit_events_actor_credential_kind", "security_audit_events", ["actor_credential_kind"])
    op.create_index("ix_security_audit_events_action", "security_audit_events", ["action"])
    op.create_index("ix_security_audit_events_target_type", "security_audit_events", ["target_type"])
    op.create_index("ix_security_audit_events_target_id", "security_audit_events", ["target_id"])
    op.create_index("ix_security_audit_events_decision", "security_audit_events", ["decision"])


def downgrade() -> None:
    op.drop_index("ix_security_audit_events_decision", table_name="security_audit_events")
    op.drop_index("ix_security_audit_events_target_id", table_name="security_audit_events")
    op.drop_index("ix_security_audit_events_target_type", table_name="security_audit_events")
    op.drop_index("ix_security_audit_events_action", table_name="security_audit_events")
    op.drop_index("ix_security_audit_events_actor_credential_kind", table_name="security_audit_events")
    op.drop_index("ix_security_audit_events_actor_credential_id", table_name="security_audit_events")
    op.drop_index("ix_security_audit_events_actor_user_id", table_name="security_audit_events")
    op.drop_index("ix_security_audit_events_project_id", table_name="security_audit_events")
    op.drop_index("ix_security_audit_events_org_id", table_name="security_audit_events")
    op.drop_table("security_audit_events")
