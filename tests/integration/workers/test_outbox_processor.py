from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.workers.workflows.outbox import process_outbox_once
from packages.core.models import ContextProposalModel, ContextRevisionModel, ContextStreamModel, ProjectModel
from packages.core.models import OutboxEventModel
from packages.core.services.outbox import OutboxProcessor


def _alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _session(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    command.upgrade(_alembic_config(database_url), "head")
    engine = create_engine(database_url)
    return sessionmaker(bind=engine)()


def _event(**overrides) -> OutboxEventModel:
    values = {
        "org_id": "org-1",
        "aggregate_type": "context_stream",
        "aggregate_id": "stream-1",
        "type": "context_head_changed",
        "payload": {
            "project_id": "project-1",
            "stream_id": "stream-1",
            "revision_id": "revision-1",
            "proposal_id": "proposal-1",
        },
        "status": "pending",
        "attempts": 0,
        "idempotency_key": "context_head_changed:stream-1:revision-1",
    }
    values.update(overrides)
    return OutboxEventModel(**values)


def _process_and_commit(processor: OutboxProcessor, *, limit: int = 10):
    # The processor owns transaction boundaries (per-claim/per-outcome commits).
    return processor.process_next_batch(limit=limit)


def test_outbox_processor_marks_successful_event_completed_once(tmp_path):
    session = _session(tmp_path)
    session.add(_event())
    session.commit()
    calls = []

    def handle(event):
        calls.append(event.idempotency_key)

    processor = OutboxProcessor(session, handlers={"context_head_changed": handle})

    first = _process_and_commit(processor, limit=10)
    second = _process_and_commit(processor, limit=10)

    event = session.query(OutboxEventModel).one()
    assert first.processed == 1
    assert first.completed == 1
    assert second.processed == 0
    assert calls == ["context_head_changed:stream-1:revision-1"]
    assert event.status == "completed"
    assert event.attempts == 1
    assert event.last_error is None


def test_outbox_processor_retries_failed_event_and_records_last_error(tmp_path):
    session = _session(tmp_path)
    session.add(_event())
    session.commit()
    calls = []

    def flaky(event):
        calls.append(event.id)
        if len(calls) == 1:
            raise RuntimeError("projection temporarily unavailable")

    processor = OutboxProcessor(session, handlers={"context_head_changed": flaky}, max_attempts=3)

    failed = _process_and_commit(processor, limit=10)
    retry = _process_and_commit(processor, limit=10)

    event = session.query(OutboxEventModel).one()
    assert failed.processed == 1
    assert failed.failed == 1
    assert retry.processed == 1
    assert retry.completed == 1
    assert len(calls) == 2
    assert event.status == "completed"
    assert event.attempts == 2
    assert event.last_error is None


def test_outbox_processor_marks_event_dead_after_retry_limit(tmp_path):
    session = _session(tmp_path)
    session.add(_event())
    session.commit()

    def always_fails(_event):
        raise RuntimeError("projection schema mismatch")

    processor = OutboxProcessor(session, handlers={"context_head_changed": always_fails}, max_attempts=2)

    first = _process_and_commit(processor, limit=10)
    second = _process_and_commit(processor, limit=10)
    third = _process_and_commit(processor, limit=10)

    event = session.query(OutboxEventModel).one()
    assert first.failed == 1
    assert second.dead == 1
    assert third.processed == 0
    assert event.status == "dead"
    assert event.attempts == 2
    assert event.last_error == "projection schema mismatch"


def test_outbox_workflow_processes_context_head_changed_event(tmp_path):
    session = _session(tmp_path)
    project = ProjectModel(
        id="project-1",
        org_id="org-1",
        name="Payments",
        slug="payments",
        git_remotes=[],
    )
    stream = ContextStreamModel(
        id="stream-1",
        org_id="org-1",
        project_id="project-1",
        name="default",
        branch="main",
        head_revision_id="revision-1",
        repository_identity={},
        status="active",
    )
    revision = ContextRevisionModel(
        id="revision-1",
        org_id="org-1",
        project_id="project-1",
        stream_id="stream-1",
        schema_version="context-revision/v1",
        parent_revision_id=None,
        commit_sha="abc123",
        content={"project_overview": "支付上下文"},
        source_anchors=[],
        provenance={},
        created_by_user_id="user-1",
    )
    proposal = ContextProposalModel(
        id="proposal-1",
        org_id="org-1",
        project_id="project-1",
        stream_id="stream-1",
        work_item_id=None,
        session_id=None,
        type="task_update",
        status="approved",
        title="PAY-318 退款审计上下文更新",
        summary="记录退款状态审计。",
        content=revision.content,
        source_anchors=[],
        provenance={},
        target_branch="main",
        expected_head_revision_id=None,
        from_commit_sha=None,
        to_commit_sha="abc123",
        created_by_user_id="user-1",
        accepted_revision_id="revision-1",
    )
    session.add_all([project, stream, revision, proposal, _event()])
    session.commit()

    result = process_outbox_once(session, limit=10)

    event = session.query(OutboxEventModel).one()
    assert result.completed == 1
    assert event.status == "completed"
    assert event.last_error is None


def test_outbox_workflow_marks_inconsistent_context_head_event_dead(tmp_path):
    session = _session(tmp_path)
    project = ProjectModel(
        id="project-1",
        org_id="org-1",
        name="Payments",
        slug="payments",
        git_remotes=[],
    )
    stream = ContextStreamModel(
        id="stream-1",
        org_id="org-1",
        project_id="project-1",
        name="default",
        branch="main",
        head_revision_id="other-revision",
        repository_identity={},
        status="active",
    )
    session.add_all([project, stream, _event()])
    session.commit()

    result = process_outbox_once(session, limit=10, max_attempts=1)

    event = session.query(OutboxEventModel).one()
    assert result.dead == 1
    assert event.status == "dead"
    assert "does not match stream head" in event.last_error


def test_lease_claim_prevents_double_processing_by_concurrent_workers(tmp_path):
    session = _session(tmp_path)
    session.add(_event())
    session.commit()
    calls = []

    def handle(event):
        calls.append(event.id)

    # Worker A claims and completes the event.
    worker_a = OutboxProcessor(session, handlers={"context_head_changed": handle})
    first = _process_and_commit(worker_a, limit=10)

    # Worker B (a different session on the same DB) sees nothing to process.
    engine = session.get_bind()
    session_b = sessionmaker(bind=engine)()
    try:
        worker_b = OutboxProcessor(session_b, handlers={"context_head_changed": handle})
        second = _process_and_commit(worker_b, limit=10)
    finally:
        session_b.close()

    assert first.processed == 1
    assert second.processed == 0
    assert len(calls) == 1


def test_stale_processing_event_is_reclaimed_after_lease_timeout(tmp_path):
    from datetime import timedelta

    session = _session(tmp_path)
    event = session.add(_event())
    session.flush()
    # Simulate a crashed worker: claim the event, then abandon it without completion.
    processor = OutboxProcessor(session, handlers={"context_head_changed": lambda e: None})
    processor._claim(session.query(OutboxEventModel).one().id)
    event = session.query(OutboxEventModel).one()
    assert event.status == "processing"

    # A processor with an expired lease reclaims and processes it.
    from packages.core.models import utc_now

    event.processing_started_at = utc_now() - timedelta(minutes=10)
    session.commit()

    calls = []

    def handle(e):
        calls.append(e.id)

    reclaiming = OutboxProcessor(
        session,
        handlers={"context_head_changed": handle},
        lease_timeout=timedelta(minutes=5),
    )
    result = _process_and_commit(reclaiming, limit=10)

    assert result.reclaimed == 1
    assert result.completed == 1
    assert len(calls) == 1
    assert session.query(OutboxEventModel).one().status == "completed"


def test_failed_handler_does_not_roll_back_other_completions(tmp_path):
    session = _session(tmp_path)
    session.add(_event(idempotency_key="context_head_changed:stream-1:revision-1"))
    session.add(_event(idempotency_key="context_head_changed:stream-2:revision-2", aggregate_id="stream-2"))
    session.commit()
    calls = []

    def flaky(event):
        calls.append(event.id)
        if event.aggregate_id == "stream-1":
            raise RuntimeError("projection schema mismatch")

    processor = OutboxProcessor(session, handlers={"context_head_changed": flaky})

    result = _process_and_commit(processor, limit=10)

    events = session.query(OutboxEventModel).order_by(OutboxEventModel.aggregate_id).all()
    assert result.processed == 2
    assert result.failed == 1
    assert result.completed == 1
    assert {event.status for event in events} == {"failed", "completed"}
