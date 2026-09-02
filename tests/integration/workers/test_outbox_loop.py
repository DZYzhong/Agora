import subprocess
import sys
import threading

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.workers.workflows.outbox import run_worker_loop
from packages.core.models import (
    ContextProposalModel,
    ContextRevisionModel,
    ContextStreamModel,
    OutboxEventModel,
    ProjectModel,
)


def _alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _seed_context_rows(session) -> None:
    session.add(
        ProjectModel(
            id="project-1",
            org_id="org-1",
            name="Payments",
            slug="payments",
            git_remotes=[],
        )
    )
    session.add(
        ContextStreamModel(
            id="stream-1",
            org_id="org-1",
            project_id="project-1",
            name="default",
            branch="main",
            head_revision_id="revision-1",
            repository_identity={},
            status="active",
        )
    )
    session.add(
        ContextRevisionModel(
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
    )
    session.add(
        ContextProposalModel(
            id="proposal-1",
            org_id="org-1",
            project_id="project-1",
            stream_id="stream-1",
            work_item_id=None,
            session_id=None,
            type="task_update",
            status="approved",
            title="退款审计上下文更新",
            summary="更新支付上下文",
            content={"project_overview": "支付上下文"},
            source_anchors=[],
            provenance={},
            target_branch="main",
            expected_head_revision_id=None,
            from_commit_sha=None,
            to_commit_sha=None,
            created_by_user_id="user-1",
            reviewed_by_user_id=None,
            accepted_revision_id="revision-1",
        )
    )


def _session_factory(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora-worker.db'}"
    command.upgrade(_alembic_config(database_url), "head")
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine)
    with factory() as session:
        _seed_context_rows(session)
        session.add(
            OutboxEventModel(
                org_id="org-1",
                aggregate_type="context_stream",
                aggregate_id="stream-1",
                type="context_head_changed",
                payload={
                    "project_id": "project-1",
                    "stream_id": "stream-1",
                    "revision_id": "revision-1",
                    "proposal_id": "proposal-1",
                },
                status="pending",
                attempts=0,
                idempotency_key="loop:stream-1",
            )
        )
        session.commit()
    return factory


def test_run_worker_loop_processes_until_shutdown(tmp_path):
    factory = _session_factory(tmp_path)
    shutdown = threading.Event()
    threading.Timer(0.2, shutdown.set).start()

    result = run_worker_loop(factory, idle_delay=0.01, shutdown_event=shutdown)

    # the loop processes the single event, then waits idle until shutdown
    assert result >= 1
    with factory() as session:
        event = session.query(OutboxEventModel).one()
        assert event.status == "completed"


def test_run_worker_loop_stops_promptly_when_shutdown_preset(tmp_path):
    # With an idle database the loop must stop as soon as shutdown is set,
    # even when the idle delay is long.
    factory = _session_factory(tmp_path)
    # consume the event first
    shutdown_first = threading.Event()
    threading.Timer(0.2, shutdown_first.set).start()
    run_worker_loop(factory, idle_delay=0.01, shutdown_event=shutdown_first)

    shutdown = threading.Event()
    timer = threading.Timer(0.1, shutdown.set)
    timer.start()
    result = run_worker_loop(factory, idle_delay=60, shutdown_event=shutdown)
    timer.join()
    assert result == 0  # nothing left to process; loop exited on shutdown


def test_outbox_loop_once_command_exits_cleanly(tmp_path):
    import os

    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora-worker.db'}"
    command.upgrade(_alembic_config(database_url), "head")
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine)
    with factory() as session:
        session.add(
            OutboxEventModel(
                org_id="org-1",
                aggregate_type="context_stream",
                aggregate_id="stream-1",
                type="context_head_changed",
                payload={
                    "project_id": "project-1",
                    "stream_id": "stream-1",
                    "revision_id": "revision-1",
                    "proposal_id": "proposal-1",
                },
                status="pending",
                attempts=0,
                idempotency_key="cli:stream-1",
            )
        )
        session.commit()

    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.workers.main",
            "outbox-loop",
            "--once",
        ],
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "AGORA_ENV": "test",
            "AGORA_DATABASE_URL": database_url,
            "AGORA_TEST_AUTH_BYPASS": "1",
        },
    )
    assert process.returncode == 0, process.stderr
    assert "processed=1" in process.stdout
