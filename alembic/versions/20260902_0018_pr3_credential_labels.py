"""PR3 B2: credential labels for issued API tokens.

Revision ID: 20260902_0018
Revises: 20260902_0017
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260902_0018"
down_revision = "20260902_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("credentials") as batch_op:
        batch_op.add_column(sa.Column("label", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("credentials") as batch_op:
        batch_op.drop_column("label")
