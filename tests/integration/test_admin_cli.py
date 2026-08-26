import subprocess
import sys
import json

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import create_app_engine
from packages.core.database import Base
import packages.core.models  # noqa: F401
from packages.core.models import QualityEvidenceModel
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
    assert manifest["schema_revision"] == "20260826_0012"
    assert manifest["files"]["projects.jsonl"] == 1
    assert manifest["files"]["work_items.jsonl"] == 1
    assert manifest["files"]["quality_evidence.jsonl"] == 1
    project_records = [json.loads(line) for line in (export_dir / "projects.jsonl").read_text().splitlines()]
    quality_records = [json.loads(line) for line in (export_dir / "quality_evidence.jsonl").read_text().splitlines()]
    assert project_records[0]["slug"] == "order-dev-platform"
    assert quality_records[0]["conclusion"] == "订单取消补偿回归测试通过。"
