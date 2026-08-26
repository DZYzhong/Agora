"""P8 work item external task links.

Revision ID: 20260826_0011
Revises: 20260826_0010
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_0011"
down_revision = "20260826_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_item_links",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("work_item_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("external_key", sa.String(), nullable=False),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "provider", "external_key", name="uq_work_item_links_project_provider_key"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_work_item_links_org_id", "work_item_links", ["org_id"])
    op.create_index("ix_work_item_links_project_id", "work_item_links", ["project_id"])
    op.create_index("ix_work_item_links_work_item_id", "work_item_links", ["work_item_id"])
    op.create_index("ix_work_item_links_provider", "work_item_links", ["provider"])
    op.create_index("ix_work_item_links_external_key", "work_item_links", ["external_key"])
    op.create_index("ix_work_item_links_created_by_user_id", "work_item_links", ["created_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_work_item_links_created_by_user_id", table_name="work_item_links")
    op.drop_index("ix_work_item_links_external_key", table_name="work_item_links")
    op.drop_index("ix_work_item_links_provider", table_name="work_item_links")
    op.drop_index("ix_work_item_links_work_item_id", table_name="work_item_links")
    op.drop_index("ix_work_item_links_project_id", table_name="work_item_links")
    op.drop_index("ix_work_item_links_org_id", table_name="work_item_links")
    op.drop_table("work_item_links")
