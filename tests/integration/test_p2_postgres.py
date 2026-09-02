import os
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import create_app_engine
from packages.core.models import (
    CredentialModel,
    IdempotencyRecordModel,
    ProjectMembershipModel,
    ProjectModel,
    UserModel,
    WorkItemModel,
    utc_now,
)
from packages.core.schema_manager import ensure_schema
from packages.core.uow import SqlAlchemyUnitOfWork


POSTGRES_URL = os.environ.get("AGORA_TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="AGORA_TEST_POSTGRES_URL is not configured")


def _session():
    assert POSTGRES_URL
    ensure_schema(POSTGRES_URL)
    engine = create_app_engine(POSTGRES_URL)
    return sessionmaker(bind=engine)()


def test_postgres_rolls_back_flushed_work_graph():
    session = _session()
    marker = f"pg-rollback-{utc_now().timestamp()}"
    try:
        with pytest.raises(RuntimeError):
            with SqlAlchemyUnitOfWork(session):
                user = UserModel(org_id=marker, display_name="Rollback User")
                project = ProjectModel(org_id=marker, name="Rollback Project", slug=marker)
                session.add_all([user, project])
                session.flush()
                session.add(ProjectMembershipModel(project_id=project.id, user_id=user.id, role="owner"))
                session.add(WorkItemModel(org_id=marker, project_id=project.id, title="Rollback item"))
                session.flush()
                raise RuntimeError("force rollback")

        assert session.scalar(select(func.count()).select_from(ProjectModel).where(ProjectModel.org_id == marker)) == 0
        assert session.scalar(select(func.count()).select_from(WorkItemModel).where(WorkItemModel.org_id == marker)) == 0
    finally:
        session.close()


def test_postgres_enforces_idempotency_key_uniqueness():
    session = _session()
    marker = f"pg-idempotency-{utc_now().timestamp()}"
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            user = UserModel(org_id=marker, display_name="Agent User")
            session.add(user)
            session.flush()
            credential = CredentialModel(
                user_id=user.id,
                kind="agent",
                token_hash=f"{marker}-hash",
                token_prefix="pgtest",
            )
            session.add(credential)
            session.flush()
            session.add(
                IdempotencyRecordModel(
                    user_id=user.id,
                    credential_id=credential.id,
                    operation="agora_start_work",
                    idempotency_key="same-key",
                    request_hash="hash-1",
                    status="completed",
                    response_json={"ok": True},
                    replay_expires_at=utc_now() + timedelta(hours=1),
                )
            )
            session.flush()
            uow.commit()

        with pytest.raises(IntegrityError):
            with SqlAlchemyUnitOfWork(session):
                session.add(
                    IdempotencyRecordModel(
                        user_id=user.id,
                        credential_id=credential.id,
                        operation="agora_start_work",
                        idempotency_key="same-key",
                        request_hash="hash-2",
                        status="in_progress",
                        replay_expires_at=utc_now() + timedelta(hours=1),
                    )
                )
                session.flush()
    finally:
        session.rollback()
        session.close()


def test_postgres_audit_actor_credential_is_polymorphic():
    """Web-session and grant actors audit with ids outside credentials.id.

    security_audit_events.actor_credential_id must not be foreign-key
    constrained to credentials.id because web sessions and one-time approval
    grants are separate tables. SQLite does not enforce foreign keys by
    default, so this only fails on PostgreSQL (regression for 20260902_0017).
    """
    from packages.core.repositories.security import SecurityRepository

    session = _session()
    marker = f"pg-audit-{utc_now().timestamp()}"
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            user = UserModel(org_id=marker, display_name="Audit Actor User")
            session.add(user)
            session.flush()
            SecurityRepository(session).create_audit_event(
                org_id=marker,
                project_id=None,
                actor_user_id=user.id,
                # A web-session actor id: present in web_sessions, not credentials.
                actor_credential_id="web-session-not-a-credential-id",
                actor_credential_kind="web_session",
                action="user.create",
                target_type="user",
                target_id=user.id,
                decision="allow",
                reason="polymorphic actor regression check",
            )
            uow.commit()
    finally:
        session.close()


def test_postgres_schema_fingerprint_matches_canonical():
    """The live PostgreSQL schema must hash identically to the canonical
    SQLite replay of the same migration head (cross-backend normalization)."""
    from packages.core.schema_manager import (
        _canonical_signature,
        _schema_signature,
        get_alembic_heads,
    )

    engine = create_app_engine(POSTGRES_URL)
    try:
        heads = get_alembic_heads()
        assert len(heads) == 1
        with engine.connect() as connection:
            assert _schema_signature(connection) == _canonical_signature(heads[0])
    finally:
        engine.dispose()
