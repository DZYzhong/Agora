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


def test_postgres_fts_search_indexes_and_ranks_assets():
    """PR4: the PostgreSQL FTS path (migration 20260902_0019) searches a
    project's assets and the fingerprint stays canonical (FTS artifacts are
    excluded from the cross-backend signature)."""
    from packages.core.models import AssetModel
    from packages.storage.postgres_fts import has_fts_support, rebuild_signal, search_assets

    engine = create_app_engine(POSTGRES_URL)
    session = _session()
    marker = f"pg-fts-{utc_now().timestamp()}"
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            user = UserModel(org_id=marker, display_name="FTS User")
            project = ProjectModel(org_id=marker, name="FTS Project", slug=marker)
            session.add_all([user, project])
            session.flush()
            project_id = project.id
            session.add_all(
                [
                    AssetModel(
                        org_id=marker,
                        project_id=project_id,
                        type="code_file",
                        source="upload",
                        source_uri="src/payments/refund.py",
                        title="Refund retry idempotency",
                        content="Refund retry uses idempotency keys and rollback evidence.",
                        summary="refund retry evidence",
                    ),
                    AssetModel(
                        org_id=marker,
                        project_id=project_id,
                        type="doc",
                        source="upload",
                        source_uri="docs/onboarding.md",
                        title="Team onboarding",
                        content="How new engineers onboard to the repository.",
                        summary="onboarding guide",
                    ),
                ]
            )
            uow.commit()

        assert has_fts_support(engine) is True
        signal = rebuild_signal(engine)
        assert signal["total_assets"] >= 2
        assert signal["fts_indexed"] >= 2

        with engine.connect() as connection:
            hits = search_assets(connection, project_id=project_id, query="refund retry")
            assert hits, "expected FTS hits for refund retry"
            assert hits[0]["title"] == "Refund retry idempotency"
            unrelated = search_assets(connection, project_id=project_id, query="onboarding")
            assert unrelated and unrelated[0]["title"] == "Team onboarding"
    finally:
        session.rollback()
        session.close()
        engine.dispose()


def test_postgres_fts_matches_fake_keyword_retrieval_on_distinctive_query():
    """PR4-B3 replacement evidence: the PG FTS path and the runtime
    FakeKeywordIndex agree on the top asset for a distinctive query, so the
    keyword retrieval can be switched to PostgreSQL without behavioral
    regression (approximate parity: overlap of top hit)."""
    from packages.core.models import AssetModel
    from packages.domain.schemas import AssetCreate
    from packages.storage.opensearch.fake import FakeKeywordIndex
    from packages.storage.postgres_fts import search_assets

    engine = create_app_engine(POSTGRES_URL)
    session = _session()
    marker = f"pg-fts-parity-{utc_now().timestamp()}"
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            user = UserModel(org_id=marker, display_name="Parity User")
            project = ProjectModel(org_id=marker, name="Parity Project", slug=marker)
            session.add_all([user, project])
            session.flush()
            project_id = project.id
            refund = AssetModel(
                org_id=marker, project_id=project_id, type="code_file", source="upload",
                source_uri="src/refund.py", title="Refund retry service",
                content="Refund retry uses idempotency keys.", summary="refund evidence",
            )
            onboard = AssetModel(
                org_id=marker, project_id=project_id, type="doc", source="upload",
                source_uri="docs/onboarding.md", title="Engineer onboarding",
                content="How engineers onboard to the repository.", summary="onboarding",
            )
            session.add_all([refund, onboard])
            uow.commit()
            refund_id = refund.id

        fake = FakeKeywordIndex()
        for asset in (refund, onboard):
            fake.index_asset(
                asset.id,
                AssetCreate(
                    org_id=marker, project_id=project_id, type=asset.type, source=asset.source,
                    source_uri=asset.source_uri, title=asset.title, content=asset.content,
                    summary=asset.summary, content_hash=asset.content_hash,
                ),
            )
        fake_top = fake.search(org_id=marker, project_id=project_id, query="refund retry", limit=1)
        with engine.connect() as connection:
            pg_hits = search_assets(connection, project_id=project_id, query="refund retry", limit=1)
        assert fake_top and fake_top[0].asset_id == refund_id
        assert pg_hits and pg_hits[0]["id"] == refund_id
    finally:
        session.rollback()
        session.close()
        engine.dispose()


def test_context_engine_retrieves_assets_through_postgres_keyword_index():
    """PR4-B3 runtime path: ContextEngine with the PG-backed keyword index
    returns the matching asset as a keyword candidate (per-request Fake would
    be empty; PG queries committed assets)."""
    from packages.core.models import AssetModel
    from packages.knowledge.context_engine import ContextEngine
    from packages.storage.postgres_fts import PostgresKeywordIndex
    from packages.storage.qdrant.fake import FakeVectorIndex

    engine = create_app_engine(POSTGRES_URL)
    session = _session()
    marker = f"pg-engine-{utc_now().timestamp()}"
    try:
        with SqlAlchemyUnitOfWork(session) as uow:
            user = UserModel(org_id=marker, display_name="Engine User")
            project = ProjectModel(org_id=marker, name="Engine Project", slug=marker)
            session.add_all([user, project])
            session.flush()
            project_id = project.id
            session.add(
                AssetModel(
                    org_id=marker, project_id=project_id, type="code_file", source="upload",
                    source_uri="src/payments/refund.py", title="Refund retry service",
                    content="Refund retry uses idempotency keys and rollback evidence.",
                    summary="refund evidence",
                )
            )
            uow.commit()

        index = PostgresKeywordIndex(POSTGRES_URL)
        engine_ctx = ContextEngine(keyword_index=index, vector_index=FakeVectorIndex())
        plan = engine_ctx.plan_context(
            org_id=marker, project_id=project_id, intent="implementation", query="refund retry"
        )
        assert plan.source_refs, "expected a source ref from the PG keyword index"
        assert "Refund retry service" in plan.summary
    finally:
        session.rollback()
        session.close()
        engine.dispose()
