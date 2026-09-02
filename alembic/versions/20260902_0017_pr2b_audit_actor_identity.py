"""PR2B: audit actor identity is polymorphic (credentials, web sessions, grants).

Revision ID: 20260902_0017
Revises: 20260902_0016
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260902_0017"
down_revision = "20260902_0016"
branch_labels = None
depends_on = None

# SQLAlchemy's default naming convention produces
# security_audit_events_actor_credential_id_fkey on PostgreSQL. SQLite never
# names foreign keys, so the drop is handled with a table rebuild there.
_FK_NAME = "security_audit_events_actor_credential_id_fkey"


def _sqlite_table_without_actor_credential_fk() -> sa.Table:
    indexed_columns = (
        "org_id",
        "project_id",
        "actor_user_id",
        "actor_credential_id",
        "actor_credential_kind",
        "action",
        "target_type",
        "target_id",
        "decision",
    )
    return sa.Table(
        "security_audit_events",
        sa.MetaData(),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
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
        *[
            sa.Index(f"ix_security_audit_events_{column}", column)
            for column in indexed_columns
        ],
    )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint(_FK_NAME, "security_audit_events", type_="foreignkey")
        return
    # SQLite batch mode cannot drop an unnamed foreign key by name; rebuild the
    # table from an explicit definition that omits the actor_credential_id FK.
    # The batch machinery keeps the table's indexes across the rebuild.
    with op.batch_alter_table(
        "security_audit_events",
        recreate="always",
        copy_from=_sqlite_table_without_actor_credential_fk(),
    ):
        pass


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_foreign_key(
            _FK_NAME,
            "security_audit_events",
            "credentials",
            ["actor_credential_id"],
            ["id"],
        )
        return
    table = _sqlite_table_without_actor_credential_fk()
    table.append_constraint(
        sa.ForeignKeyConstraint(["actor_credential_id"], ["credentials.id"])
    )
    with op.batch_alter_table("security_audit_events", recreate="always", copy_from=table):
        pass
