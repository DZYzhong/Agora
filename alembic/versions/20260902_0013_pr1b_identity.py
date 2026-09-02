"""PR1B identity: users, credentials and organization memberships.

Revision ID: 20260902_0013
Revises: 20260826_0012
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260902_0013"
down_revision = "20260826_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("username", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("password_hash", sa.String(), nullable=True))
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("uq_users_org_username", "users", ["org_id", "username"], unique=True)

    with op.batch_alter_table("credentials") as batch_op:
        batch_op.add_column(sa.Column("single_use", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("security_audit_events") as batch_op:
        batch_op.alter_column("project_id", existing_type=sa.String(), nullable=True)

    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("org_id", "user_id", name="uq_organization_memberships_org_user"),
    )
    op.create_index("ix_organization_memberships_org_id", "organization_memberships", ["org_id"])
    op.create_index("ix_organization_memberships_user_id", "organization_memberships", ["user_id"])
    op.execute(
        "CREATE UNIQUE INDEX uq_organization_memberships_one_admin_per_org "
        "ON organization_memberships (org_id) WHERE role IN ('owner', 'admin')"
    )


def downgrade() -> None:
    op.execute("DROP INDEX uq_organization_memberships_one_admin_per_org")
    op.drop_index("ix_organization_memberships_user_id", table_name="organization_memberships")
    op.drop_index("ix_organization_memberships_org_id", table_name="organization_memberships")
    op.drop_table("organization_memberships")

    with op.batch_alter_table("security_audit_events") as batch_op:
        batch_op.alter_column("project_id", existing_type=sa.String(), nullable=False)

    with op.batch_alter_table("credentials") as batch_op:
        batch_op.drop_column("consumed_at")
        batch_op.drop_column("single_use")

    op.drop_index("uq_users_org_username", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("password_hash")
        batch_op.drop_column("username")
