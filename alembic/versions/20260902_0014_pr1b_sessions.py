"""PR1B web sessions.

Revision ID: 20260902_0014
Revises: 20260902_0013
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260902_0014"
down_revision = "20260902_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "web_sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("csrf_secret_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reauth_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("token_hash", name="uq_web_sessions_token_hash"),
    )
    op.create_index("ix_web_sessions_user_id", "web_sessions", ["user_id"])
    op.create_index("ix_web_sessions_org_id", "web_sessions", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_web_sessions_org_id", table_name="web_sessions")
    op.drop_index("ix_web_sessions_user_id", table_name="web_sessions")
    op.drop_table("web_sessions")
