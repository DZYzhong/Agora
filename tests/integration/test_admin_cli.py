import subprocess
import sys
import json
import os
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import create_app_engine
from packages.core.database import Base
import packages.core.models  # noqa: F401
from packages.core.models import (
    ApprovalDecisionModel,
    AssetModel,
    ContextProposalModel,
    ContextRevisionModel,
    ContextStreamModel,
    PullRequestSignalModel,
    QualityEvidenceModel,
    RepositoryRevisionSignalModel,
    OutboxEventModel,
    SecurityAuditEventModel,
    SkillModel,
    SkillVersionModel,
)
from packages.core.repositories.assets import AssetRepository
from packages.core.repositories.projects import ProjectRepository
from packages.core.repositories.work import WorkRepository
from packages.core.uow import SqlAlchemyUnitOfWork


def test_admin_cli_rebuild_indexes_reports_persisted_asset_count(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    engine = create_app_engine(database_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    with SqlAlchemyUnitOfWork(session) as uow:
        project = ProjectRepository(session).create(
            org_id="org_1",
            name="会员中心研发协作平台",
            slug="member-center-rd",
            git_remotes=["git@example.com:member-center-rd.git"],
        )
        AssetRepository(session).create(
            org_id="org_1",
            project_id=project.id,
            type="code_file",
            source="git",
            source_uri="src/member/coupon.py",
            title="coupon.py",
            content="修复优惠券支付后状态刷新缺陷",
        )
        uow.commit()
    session.close()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agora_admin",
            "rebuild-indexes",
            "--database-url",
            database_url,
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert "Rebuilt indexes from 1 persisted assets" in result.stdout


def test_admin_cli_reset_local_recreates_empty_schema(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    engine = create_app_engine(database_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    with SqlAlchemyUnitOfWork(session) as uow:
        ProjectRepository(session).create(
            org_id="org_1",
            name="需求交付平台",
            slug="delivery-platform",
            git_remotes=[],
        )
        uow.commit()
    session.close()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agora_admin",
            "reset-local",
            "--database-url",
            database_url,
            "--yes",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert "Reset local SQLite database" in result.stdout

    inspector = inspect(create_engine(database_url))
    assert "projects" in inspector.get_table_names()
    with sessionmaker(bind=create_engine(database_url))() as restored_session:
        assert ProjectRepository(restored_session).list() == []


def test_admin_cli_backup_and_restore_sqlite_database(tmp_path):
    database_path = tmp_path / "agora.db"
    backup_path = tmp_path / "agora.backup.db"
    restored_path = tmp_path / "agora-restored.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    restored_database_url = f"sqlite+pysqlite:///{restored_path}"
    engine = create_app_engine(database_url)
    session = sessionmaker(bind=engine)()
    with SqlAlchemyUnitOfWork(session) as uow:
        ProjectRepository(session).create(
            org_id="org_1",
            name="研发效能平台",
            slug="dev-productivity",
            git_remotes=["git@example.com:dev-productivity.git"],
        )
        uow.commit()
    session.close()

    backup = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agora_admin",
            "backup-sqlite",
            "--database-url",
            database_url,
            "--output",
            str(backup_path),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    restore = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agora_admin",
            "restore-sqlite",
            "--backup",
            str(backup_path),
            "--database-url",
            restored_database_url,
            "--yes",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert backup.returncode == 0
    assert "SQLite backup written" in backup.stdout
    assert backup_path.exists()
    assert restore.returncode == 0
    assert "SQLite backup restored" in restore.stdout
    with sessionmaker(bind=create_engine(restored_database_url))() as restored_session:
        projects = ProjectRepository(restored_session).list()
    assert [project.slug for project in projects] == ["dev-productivity"]


def test_admin_cli_export_project_archive_writes_manifest_and_jsonl_assets(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    export_dir = tmp_path / "export"
    engine = create_app_engine(database_url)
    session = sessionmaker(bind=engine)()
    with SqlAlchemyUnitOfWork(session) as uow:
        project = ProjectRepository(session).create(
            org_id="org_1",
            name="订单研发平台",
            slug="order-dev-platform",
            git_remotes=["git@example.com:order-dev-platform.git"],
        )
        work_item = WorkRepository(session).create_work_item(
            org_id="org_1",
            project_id=project.id,
            external_key="AG-9101",
            title="订单取消补偿任务",
            source="manual",
        )
        session.add(
            QualityEvidenceModel(
                org_id="org_1",
                project_id=project.id,
                work_item_id=work_item.id,
                session_id=None,
                evidence_type="test",
                source="pytest",
                status="passed",
                conclusion="订单取消补偿回归测试通过。",
                evidence_metadata={"suite": "order"},
            )
        )
        uow.commit()
    session.close()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agora_admin",
            "export-project",
            "--database-url",
            database_url,
            "--project-slug",
            "order-dev-platform",
            "--output-dir",
            str(export_dir),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert "Project export written" in result.stdout
    manifest = json.loads((export_dir / "manifest.json").read_text())
    assert manifest["project"]["slug"] == "order-dev-platform"
    assert manifest["schema_revision"] == "20260902_0013"
    assert manifest["files"]["projects.jsonl"] == 1
    assert manifest["files"]["work_items.jsonl"] == 1
    assert manifest["files"]["quality_evidence.jsonl"] == 1
    project_records = [json.loads(line) for line in (export_dir / "projects.jsonl").read_text().splitlines()]
    quality_records = [json.loads(line) for line in (export_dir / "quality_evidence.jsonl").read_text().splitlines()]
    assert project_records[0]["slug"] == "order-dev-platform"
    assert quality_records[0]["conclusion"] == "订单取消补偿回归测试通过。"


def test_admin_cli_project_summary_reports_governance_and_delivery_state(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    summary_path = tmp_path / "summary.json"
    engine = create_app_engine(database_url)
    session = sessionmaker(bind=engine)()
    with SqlAlchemyUnitOfWork(session) as uow:
        project = ProjectRepository(session).create(
            org_id="org_1",
            name="研发协作中台",
            slug="rd-collaboration-platform",
            git_remotes=["git@example.com:rd-collaboration-platform.git"],
        )
        work_item = WorkRepository(session).create_work_item(
            org_id="org_1",
            project_id=project.id,
            external_key="AG-9201",
            title="项目上下文自动更新",
            source="jira",
        )
        session.add_all(
            [
                AssetModel(
                    org_id="org_1",
                    project_id=project.id,
                    type="code_file",
                    source="local_scan",
                    source_uri="src/context/sync.py",
                    title="sync.py",
                    content="context sync",
                ),
                AssetModel(
                    org_id="org_1",
                    project_id=project.id,
                    type="doc",
                    source="local_scan",
                    source_uri="docs/context.md",
                    title="context.md",
                    content="context doc",
                ),
            ]
        )
        stream = ContextStreamModel(
            id="stream-main",
            org_id="org_1",
            project_id=project.id,
            name="main",
            branch="main",
            repository_identity={"remote": "git@example.com:rd-collaboration-platform.git"},
        )
        session.add(stream)
        session.add(
            ContextRevisionModel(
                id="rev-main-1",
                org_id="org_1",
                project_id=project.id,
                stream_id=stream.id,
                commit_sha="a1b2c3",
                content={"summary": "项目主干上下文。"},
                created_by_user_id="user_reviewer",
            )
        )
        proposal = ContextProposalModel(
            id="proposal-context-refresh",
            org_id="org_1",
            project_id=project.id,
            stream_id=stream.id,
            work_item_id=work_item.id,
            type="context_update",
            status="submitted",
            title="补充上下文自动更新策略",
            summary="AI 工具扫描本地代码后提交上下文更新。",
            target_branch="main",
            created_by_user_id="user_developer",
        )
        session.add(proposal)
        session.add(
            ApprovalDecisionModel(
                org_id="org_1",
                project_id=project.id,
                proposal_id=proposal.id,
                decision="approve",
                decided_by_user_id="user_reviewer",
            )
        )
        session.add(
            QualityEvidenceModel(
                org_id="org_1",
                project_id=project.id,
                work_item_id=work_item.id,
                session_id=None,
                evidence_type="test",
                source="pytest",
                status="passed",
                conclusion="上下文同步回归通过。",
            )
        )
        session.add(
            SkillModel(
                id="skill-risk-review",
                org_id="org_1",
                project_id=project.id,
                slug="risk-review",
                name="风险评审",
                status="approved",
                definition={"summary": "检查变更风险。"},
            )
        )
        session.add(
            SkillVersionModel(
                org_id="org_1",
                project_id=project.id,
                skill_id="skill-risk-review",
                version="1.0.0",
                status="approved",
                definition={"steps": ["分析", "评审"]},
            )
        )
        session.add(
            SecurityAuditEventModel(
                org_id="org_1",
                project_id=project.id,
                actor_user_id="user_reviewer",
                actor_credential_kind="human",
                action="approve_context_proposal",
                target_type="context_proposal",
                target_id=proposal.id,
                decision="allow",
            )
        )
        session.add(
            RepositoryRevisionSignalModel(
                org_id="org_1",
                project_id=project.id,
                work_item_id=work_item.id,
                provider="gitlab",
                repository_identity="git@example.com:rd-collaboration-platform.git",
                branch="main",
                observed_head_sha="d4e5f6",
                previous_head_sha="a1b2c3",
                signal_type="push",
                status="context_outdated",
            )
        )
        session.add(
            PullRequestSignalModel(
                org_id="org_1",
                project_id=project.id,
                work_item_id=work_item.id,
                provider="gitlab",
                repository_identity="git@example.com:rd-collaboration-platform.git",
                pull_request_id="9201",
                title="项目上下文自动更新",
                action="merge",
                target_branch="main",
                status="merged",
            )
        )
        uow.commit()
    session.close()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agora_admin",
            "project-summary",
            "--database-url",
            database_url,
            "--project-slug",
            "rd-collaboration-platform",
            "--output",
            str(summary_path),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    summary = json.loads(result.stdout)
    assert summary["format"] == "agora-project-summary/v1"
    assert summary["project"]["slug"] == "rd-collaboration-platform"
    assert summary["assets"]["total"] == 2
    assert summary["assets"]["by_type"] == {"code_file": 1, "doc": 1}
    assert summary["work_items"]["total"] == 1
    assert summary["work_items"]["by_stage"] == {"backlog": 1}
    assert summary["context"]["streams"] == 1
    assert summary["context"]["revisions"] == 1
    assert summary["context"]["proposals_by_status"] == {"submitted": 1}
    assert summary["quality"]["evidence_by_status"] == {"passed": 1}
    assert summary["skills"]["skills_by_status"] == {"approved": 1}
    assert summary["skills"]["versions_by_status"] == {"approved": 1}
    assert summary["approvals"]["decisions"] == {"approve": 1}
    assert summary["security"]["decisions"] == {"allow": 1}
    assert summary["repository_signals"]["by_status"] == {"context_outdated": 1}
    assert summary["pull_request_signals"]["by_status"] == {"merged": 1}
    assert json.loads(summary_path.read_text())["project"]["slug"] == "rd-collaboration-platform"


def test_admin_cli_outbox_summary_reports_backlog_and_dead_events(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    output_path = tmp_path / "outbox-summary.json"
    engine = create_app_engine(database_url)
    session = sessionmaker(bind=engine)()
    with SqlAlchemyUnitOfWork(session) as uow:
        session.add_all(
            [
                OutboxEventModel(
                    org_id="org_1",
                    aggregate_type="context_stream",
                    aggregate_id="stream-main",
                    type="context_head_changed",
                    payload={"project_id": "project-1"},
                    status="pending",
                    attempts=0,
                    idempotency_key="context_head_changed:stream-main:rev-1",
                ),
                OutboxEventModel(
                    org_id="org_1",
                    aggregate_type="context_stream",
                    aggregate_id="stream-main",
                    type="context_head_changed",
                    payload={"project_id": "project-1"},
                    status="failed",
                    attempts=2,
                    last_error="projection temporarily unavailable",
                    idempotency_key="context_head_changed:stream-main:rev-2",
                ),
                OutboxEventModel(
                    org_id="org_1",
                    aggregate_type="context_stream",
                    aggregate_id="stream-main",
                    type="context_head_changed",
                    payload={"project_id": "project-1"},
                    status="dead",
                    attempts=3,
                    last_error="projection schema mismatch",
                    idempotency_key="context_head_changed:stream-main:rev-3",
                ),
            ]
        )
        uow.commit()
    session.close()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agora_admin",
            "outbox-summary",
            "--database-url",
            database_url,
            "--max-attempts",
            "3",
            "--output",
            str(output_path),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    summary = json.loads(result.stdout)
    assert summary["format"] == "agora-outbox-summary/v1"
    assert summary["total"] == 3
    assert summary["by_status"] == {"dead": 1, "failed": 1, "pending": 1}
    assert summary["by_type"] == {"context_head_changed": 3}
    assert summary["retryable"] == 2
    assert summary["dead_events"][0]["idempotency_key"] == "context_head_changed:stream-main:rev-3"
    assert summary["dead_events"][0]["last_error"] == "projection schema mismatch"
    assert json.loads(output_path.read_text())["by_status"]["dead"] == 1


def test_admin_cli_retention_summary_reports_export_and_outbox_cleanup_candidates(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    exports_dir = tmp_path / "exports"
    old_export = exports_dir / "old-project"
    recent_export = exports_dir / "recent-project"
    old_export.mkdir(parents=True)
    recent_export.mkdir(parents=True)
    (old_export / "manifest.json").write_text('{"project":{"slug":"old-project"}}', encoding="utf-8")
    (recent_export / "manifest.json").write_text('{"project":{"slug":"recent-project"}}', encoding="utf-8")
    old_mtime = (datetime.now(timezone.utc) - timedelta(days=45)).timestamp()
    os.utime(old_export, (old_mtime, old_mtime))
    os.utime(old_export / "manifest.json", (old_mtime, old_mtime))
    engine = create_app_engine(database_url)
    session = sessionmaker(bind=engine)()
    old_time = datetime.now(timezone.utc) - timedelta(days=20)
    with SqlAlchemyUnitOfWork(session) as uow:
        session.add_all(
            [
                OutboxEventModel(
                    org_id="org_1",
                    aggregate_type="context_stream",
                    aggregate_id="stream-main",
                    type="context_head_changed",
                    payload={"project_id": "project-1"},
                    status="completed",
                    attempts=1,
                    idempotency_key="context_head_changed:stream-main:completed-old",
                    created_at=old_time,
                    updated_at=old_time,
                ),
                OutboxEventModel(
                    org_id="org_1",
                    aggregate_type="context_stream",
                    aggregate_id="stream-main",
                    type="context_head_changed",
                    payload={"project_id": "project-1"},
                    status="dead",
                    attempts=3,
                    last_error="projection schema mismatch",
                    idempotency_key="context_head_changed:stream-main:dead-old",
                    created_at=old_time,
                    updated_at=old_time,
                ),
                OutboxEventModel(
                    org_id="org_1",
                    aggregate_type="context_stream",
                    aggregate_id="stream-main",
                    type="context_head_changed",
                    payload={"project_id": "project-1"},
                    status="failed",
                    attempts=1,
                    idempotency_key="context_head_changed:stream-main:failed-retryable",
                ),
            ]
        )
        uow.commit()
    session.close()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agora_admin",
            "retention-summary",
            "--database-url",
            database_url,
            "--export-dir",
            str(exports_dir),
            "--export-retention-days",
            "30",
            "--outbox-retention-days",
            "14",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    summary = json.loads(result.stdout)
    assert summary["format"] == "agora-retention-summary/v1"
    assert summary["exports"]["candidates"] == 1
    assert summary["exports"]["candidate_paths"] == [str(old_export.resolve())]
    assert summary["outbox"]["candidates_by_status"] == {"completed": 1, "dead": 1}
    assert summary["outbox"]["candidate_total"] == 2
    assert old_export.exists()
    assert recent_export.exists()


def test_admin_cli_cleanup_retention_requires_confirmation_and_prunes_terminal_records(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    exports_dir = tmp_path / "exports"
    old_export = exports_dir / "old-project"
    recent_export = exports_dir / "recent-project"
    old_export.mkdir(parents=True)
    recent_export.mkdir(parents=True)
    (old_export / "manifest.json").write_text("{}", encoding="utf-8")
    (recent_export / "manifest.json").write_text("{}", encoding="utf-8")
    old_mtime = (datetime.now(timezone.utc) - timedelta(days=45)).timestamp()
    os.utime(old_export, (old_mtime, old_mtime))
    os.utime(old_export / "manifest.json", (old_mtime, old_mtime))
    engine = create_app_engine(database_url)
    session = sessionmaker(bind=engine)()
    old_time = datetime.now(timezone.utc) - timedelta(days=20)
    with SqlAlchemyUnitOfWork(session) as uow:
        session.add_all(
            [
                OutboxEventModel(
                    org_id="org_1",
                    aggregate_type="context_stream",
                    aggregate_id="stream-main",
                    type="context_head_changed",
                    payload={"project_id": "project-1"},
                    status="completed",
                    attempts=1,
                    idempotency_key="context_head_changed:stream-main:completed-cleanup",
                    created_at=old_time,
                    updated_at=old_time,
                ),
                OutboxEventModel(
                    org_id="org_1",
                    aggregate_type="context_stream",
                    aggregate_id="stream-main",
                    type="context_head_changed",
                    payload={"project_id": "project-1"},
                    status="failed",
                    attempts=1,
                    idempotency_key="context_head_changed:stream-main:failed-kept",
                ),
            ]
        )
        uow.commit()
    session.close()

    refused = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agora_admin",
            "cleanup-retention",
            "--database-url",
            database_url,
            "--export-dir",
            str(exports_dir),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    cleaned = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agora_admin",
            "cleanup-retention",
            "--database-url",
            database_url,
            "--export-dir",
            str(exports_dir),
            "--export-retention-days",
            "30",
            "--outbox-retention-days",
            "14",
            "--yes",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert refused.returncode != 0
    assert "without --yes" in refused.stderr
    assert cleaned.returncode == 0
    summary = json.loads(cleaned.stdout)
    assert summary["exports"]["deleted"] == 1
    assert summary["outbox"]["deleted"] == 1
    assert not old_export.exists()
    assert recent_export.exists()
    with sessionmaker(bind=create_engine(database_url))() as restored_session:
        statuses = [event.status for event in restored_session.query(OutboxEventModel).all()]
    assert statuses == ["failed"]


def test_admin_cli_compatibility_check_reports_protocol_manifest(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    output_path = tmp_path / "compatibility.json"
    create_app_engine(database_url)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agora_admin",
            "compatibility-check",
            "--database-url",
            database_url,
            "--output",
            str(output_path),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["format"] == "agora-compatibility-check/v1"
    assert report["compatible"] is True
    assert report["schema_revision"] == "20260902_0013"
    assert report["protocol_manifest"]["harness_protocol"]["current"] == "1.1"
    assert report["protocol_manifest"]["harness_protocol"]["supported"] == ["1.0", "1.1"]
    assert report["protocol_manifest"]["compatibility"]["minimum_local_connector_version"] == "0.1.0"
    assert report["checks"]["minimum_local_connector_version"] == "ok"
    assert "agora_get_protocol_manifest" in report["protocol_manifest"]["tools"]["canonical"]
    assert report["protocol_manifest"]["tools"]["deprecated"]["agora_plan_context"]["canonical_tool"] == "agora_prepare_context"
    assert json.loads(output_path.read_text())["compatible"] is True


def test_admin_cli_p9_blackbox_suite_lists_complete_role_and_operations_checks(tmp_path):
    output_path = tmp_path / "p9-suite.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.agora_admin",
            "p9-blackbox-suite",
            "--output",
            str(output_path),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    suite = json.loads(result.stdout)
    assert suite["format"] == "agora-p9-blackbox-suite/v1"
    assert suite["guide"] == "docs/development/p9-operations-readiness-blackbox.zh-CN.md"
    assert suite["roles"] == ["Developer", "Reviewer", "Project Manager", "Quality", "Operations"]
    assert len(suite["checks"]) >= 11
    check_ids = {check["id"] for check in suite["checks"]}
    assert {
        "service-probes",
        "developer-ai-tool",
        "reviewer-governance",
        "project-manager-status",
        "quality-evidence",
        "sqlite-recovery",
        "postgres-recovery",
        "project-export",
        "operations-summary",
        "outbox-diagnostics",
        "retention-cleanup",
        "compatibility-check",
        "context-concurrency",
    }.issubset(check_ids)
    assert json.loads(output_path.read_text())["format"] == "agora-p9-blackbox-suite/v1"


def test_admin_cli_smoke_checks_api_readiness_metrics_and_web(tmp_path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/ready":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    b'{"status":"ready","checks":{"database":{"status":"ok"},"schema":{"revision":"20260902_0013"}}}'
                )
                return
            if self.path == "/metrics":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"agora_ready 1\nagora_projects_total 1\n")
                return
            if self.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html>Agora</html>")
                return
            self.send_response(404)
            self.end_headers()

        def log_message(self, format, *args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.agora_admin",
                "smoke",
                "--api-base-url",
                base_url,
                "--web-base-url",
                base_url,
            ],
            check=False,
            text=True,
            capture_output=True,
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    assert result.returncode == 0
    assert "API readiness: ready" in result.stdout
    assert "Metrics: ok" in result.stdout
    assert "Web: ok" in result.stdout
