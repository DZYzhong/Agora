"""P2 harness identity and work foundation.

Revision ID: 20260814_0002
Revises: 20260813_0001
Create Date: 2026-08-14 00:00:00
"""
from collections.abc import Sequence
from datetime import datetime, timezone
import hashlib

from alembic import op
import sqlalchemy as sa


revision: str = "20260814_0002"
down_revision: str | None = "20260813_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _legacy_id(kind: str, *parts: str) -> str:
    value = ":".join(("agora", "legacy", kind, *parts))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def _legacy_organizations(connection: sa.Connection) -> set[str]:
    organizations: set[str] = set()
    for table_name in (
        "projects",
        "assets",
        "project_initialization_jobs",
        "context_packs",
        "skills",
        "skill_runs",
        "task_sessions",
        "writebacks",
    ):
        rows = connection.execute(sa.text(f"SELECT DISTINCT org_id FROM {table_name} WHERE org_id IS NOT NULL"))
        organizations.update(row[0] for row in rows)
    return organizations


def upgrade() -> None:
    users = op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("is_placeholder", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("ix_users_status", "users", ["status"])

    op.create_table(
        "credentials",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("token_prefix", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_credentials_token_hash"),
    )
    op.create_index("ix_credentials_user_id", "credentials", ["user_id"])
    op.create_index("ix_credentials_kind", "credentials", ["kind"])
    op.create_index("ix_credentials_status", "credentials", ["status"])

    op.create_table(
        "project_memberships",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_memberships_project_user"),
    )
    op.create_index("ix_project_memberships_project_id", "project_memberships", ["project_id"])
    op.create_index("ix_project_memberships_user_id", "project_memberships", ["user_id"])

    work_items = op.create_table(
        "work_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("external_key", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_work_items_org_id", "work_items", ["org_id"])
    op.create_index("ix_work_items_project_id", "work_items", ["project_id"])
    op.create_index("ix_work_items_status", "work_items", ["status"])
    op.create_index("ix_work_items_stage", "work_items", ["stage"])
    op.create_index("ix_work_items_owner_id", "work_items", ["owner_id"])
    op.create_index("ix_work_items_source", "work_items", ["source"])
    op.create_index(
        "ux_work_items_project_external_key",
        "work_items",
        ["project_id", "external_key"],
        unique=True,
        sqlite_where=sa.text("external_key IS NOT NULL"),
        postgresql_where=sa.text("external_key IS NOT NULL"),
    )

    work_sessions = op.create_table(
        "work_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("work_item_id", sa.String(), sa.ForeignKey("work_items.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("credential_id", sa.String(), sa.ForeignKey("credentials.id"), nullable=True),
        sa.Column("initial_request_id", sa.String(), nullable=True),
        sa.Column("agent_type", sa.String(), nullable=False),
        sa.Column("intent", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("legacy_imported", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_work_sessions_work_item_id", "work_sessions", ["work_item_id"])
    op.create_index("ix_work_sessions_user_id", "work_sessions", ["user_id"])
    op.create_index("ix_work_sessions_credential_id", "work_sessions", ["credential_id"])
    op.create_index("ix_work_sessions_initial_request_id", "work_sessions", ["initial_request_id"])
    op.create_index("ix_work_sessions_status", "work_sessions", ["status"])

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("credential_id", sa.String(), sa.ForeignKey("credentials.id"), nullable=False),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("request_hash", sa.String(), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("replay_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "credential_id",
            "operation",
            "idempotency_key",
            name="uq_idempotency_records_credential_operation_key",
        ),
    )
    op.create_index("ix_idempotency_records_user_id", "idempotency_records", ["user_id"])
    op.create_index("ix_idempotency_records_credential_id", "idempotency_records", ["credential_id"])
    op.create_index("ix_idempotency_records_status", "idempotency_records", ["status"])
    op.create_index("ix_idempotency_records_replay_expires_at", "idempotency_records", ["replay_expires_at"])

    connection = op.get_bind()
    now = datetime.now(timezone.utc)
    organizations = _legacy_organizations(connection)
    placeholder_ids = {org_id: _legacy_id("user", org_id) for org_id in organizations}
    if placeholder_ids:
        op.bulk_insert(
            users,
            [
                {
                    "id": user_id,
                    "org_id": org_id,
                    "display_name": f"Legacy user ({org_id})",
                    "status": "disabled",
                    "is_placeholder": True,
                    "created_at": now,
                    "updated_at": now,
                }
                for org_id, user_id in sorted(placeholder_ids.items())
            ],
        )

    legacy_sessions = sa.table(
        "task_sessions",
        sa.column("id", sa.String()),
        sa.column("org_id", sa.String()),
        sa.column("project_id", sa.String()),
        sa.column("task_id", sa.String()),
        sa.column("agent_type", sa.String()),
        sa.column("intent", sa.String()),
        sa.column("status", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("closed_at", sa.DateTime(timezone=True)),
    )
    session_rows = connection.execute(sa.select(legacy_sessions).order_by(legacy_sessions.c.created_at)).mappings().all()

    work_item_rows: dict[tuple[str, ...], dict[str, object]] = {}
    work_session_rows: list[dict[str, object]] = []
    for session in session_rows:
        task_id = session["task_id"]
        if task_id is None:
            grouping_key = ("taskless", session["id"])
            work_item_id = _legacy_id("work-session", session["id"])
            external_key = None
            title = f"Legacy session {session['id']}"
        else:
            grouping_key = ("task", session["project_id"], task_id)
            work_item_id = _legacy_id("work-task", session["project_id"], task_id)
            external_key = task_id
            title = f"Legacy task {task_id}"

        updated_at = session["closed_at"] or session["created_at"]
        existing = work_item_rows.get(grouping_key)
        if existing is None:
            work_item_rows[grouping_key] = {
                "id": work_item_id,
                "org_id": session["org_id"],
                "project_id": session["project_id"],
                "external_key": external_key,
                "title": title,
                "description": None,
                "status": "closed" if session["closed_at"] is not None else "active",
                "stage": "legacy_imported",
                "owner_id": placeholder_ids[session["org_id"]],
                "source": "legacy",
                "created_at": session["created_at"],
                "updated_at": updated_at,
            }
        else:
            existing["status"] = "active" if session["closed_at"] is None else existing["status"]
            existing["updated_at"] = max(existing["updated_at"], updated_at)

        work_session_rows.append(
            {
                "id": session["id"],
                "work_item_id": work_item_id,
                "user_id": placeholder_ids[session["org_id"]],
                "credential_id": None,
                "initial_request_id": None,
                "agent_type": session["agent_type"],
                "intent": session["intent"],
                "status": session["status"],
                "created_at": session["created_at"],
                "closed_at": session["closed_at"],
                "legacy_imported": True,
            }
        )

    if work_item_rows:
        op.bulk_insert(work_items, list(work_item_rows.values()))
    if work_session_rows:
        op.bulk_insert(work_sessions, work_session_rows)


def downgrade() -> None:
    op.drop_index("ix_idempotency_records_replay_expires_at", table_name="idempotency_records")
    op.drop_index("ix_idempotency_records_status", table_name="idempotency_records")
    op.drop_index("ix_idempotency_records_credential_id", table_name="idempotency_records")
    op.drop_index("ix_idempotency_records_user_id", table_name="idempotency_records")
    op.drop_table("idempotency_records")
    op.drop_index("ix_work_sessions_status", table_name="work_sessions")
    op.drop_index("ix_work_sessions_initial_request_id", table_name="work_sessions")
    op.drop_index("ix_work_sessions_credential_id", table_name="work_sessions")
    op.drop_index("ix_work_sessions_user_id", table_name="work_sessions")
    op.drop_index("ix_work_sessions_work_item_id", table_name="work_sessions")
    op.drop_table("work_sessions")
    op.drop_index("ux_work_items_project_external_key", table_name="work_items")
    op.drop_index("ix_work_items_source", table_name="work_items")
    op.drop_index("ix_work_items_owner_id", table_name="work_items")
    op.drop_index("ix_work_items_stage", table_name="work_items")
    op.drop_index("ix_work_items_status", table_name="work_items")
    op.drop_index("ix_work_items_project_id", table_name="work_items")
    op.drop_index("ix_work_items_org_id", table_name="work_items")
    op.drop_table("work_items")
    op.drop_index("ix_project_memberships_user_id", table_name="project_memberships")
    op.drop_index("ix_project_memberships_project_id", table_name="project_memberships")
    op.drop_table("project_memberships")
    op.drop_index("ix_credentials_status", table_name="credentials")
    op.drop_index("ix_credentials_kind", table_name="credentials")
    op.drop_index("ix_credentials_user_id", table_name="credentials")
    op.drop_table("credentials")
    op.drop_index("ix_users_status", table_name="users")
    op.drop_index("ix_users_org_id", table_name="users")
    op.drop_table("users")
