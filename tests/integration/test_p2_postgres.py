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
