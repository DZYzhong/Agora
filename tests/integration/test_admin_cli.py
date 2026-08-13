import subprocess
import sys

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from apps.api.dependencies import create_app_engine
from packages.core.database import Base
import packages.core.models  # noqa: F401
from packages.core.repositories.assets import AssetRepository
from packages.core.repositories.projects import ProjectRepository


def test_admin_cli_rebuild_indexes_reports_persisted_asset_count(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    engine = create_app_engine(database_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
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
    ProjectRepository(session).create(
        org_id="org_1",
        name="需求交付平台",
        slug="delivery-platform",
        git_remotes=[],
    )
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
