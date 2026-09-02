"""PR1B approval grants.

Revision ID: 20260902_0015
Revises: 20260902_0014
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260902_0015"
down_revision = "20260902_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approval_grants",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("object_type", sa.String(), nullable=False),
        sa.Column("object_id", sa.String(), nullable=False),
        sa.Column("payload_digest", sa.String(), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("policy_version", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_approval_grants_org_id", "approval_grants", ["org_id"])
    op.create_index("ix_approval_grants_user_id", "approval_grants", ["user_id"])
    op.create_index("ix_approval_grants_session_id", "approval_grants", ["session_id"])
    op.create_index("ix_approval_grants_object_type", "approval_grants", ["object_type"])
    op.create_index("ix_approval_grants_object_id", "approval_grants", ["object_id"])
    op.create_index("ix_approval_grants_expires_at", "approval_grants", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_approval_grants_expires_at", table_name="approval_grants")
    op.drop_index("ix_approval_grants_object_id", table_name="approval_grants")
    op.drop_index("ix_approval_grants_object_type", table_name="approval_grants")
    op.drop_index("ix_approval_grants_session_id", table_name="approval_grants")
    op.drop_index("ix_approval_grants_user_id", table_name="approval_grants")
    op.drop_index("ix_approval_grants_org_id", table_name="approval_grants")
    op.drop_table("approval_grants")
