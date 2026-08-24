import json
import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, text


def _run_prepare(root: Path, database_url: str) -> dict:
    env = {
        **os.environ,
        "AGORA_BOOTSTRAP_HUMAN_TOKEN": "p2-human-token",
        "AGORA_BOOTSTRAP_AGENT_TOKEN": "p2-agent-token",
        "AGORA_BOOTSTRAP_ORG_ID": "local-org",
        "AGORA_DATABASE_URL": database_url,
    }
    result = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_p2_blackbox.py",
            "--root",
            str(root),
            "--database-url",
            database_url,
            "--json",
        ],
        check=True,
        env=env,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def test_prepare_p2_blackbox_is_idempotent_and_does_not_precompute_ai_context(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'agora.db'}"
    root = tmp_path / "blackbox"

    first = _run_prepare(root, database_url)
    second = _run_prepare(root, database_url)

    assert first["project_id"] == second["project_id"]
    assert first["repo_path"] == second["repo_path"]
    assert first["git_remote"] == "git@example.com:agora/payments-core.git"
    assert first["issue_key"] == "PAY-241"
    assert first["human_token_env"] == "AGORA_BOOTSTRAP_HUMAN_TOKEN"
    assert first["agent_token_env"] == "AGORA_BOOTSTRAP_AGENT_TOKEN"

    repo_path = Path(first["repo_path"])
    assert (repo_path / "README.md").read_text(encoding="utf-8").startswith("# Payments Core")
    assert "PAY-241" in (repo_path / "docs/issues/PAY-241.md").read_text(encoding="utf-8")
    assert "PaymentStateMachine" in (repo_path / "src/payments/state_machine.py").read_text(encoding="utf-8")

    env_file = Path(first["env_file"])
    assert env_file.exists()
    assert "AGORA_BOOTSTRAP_HUMAN_TOKEN=p2-human-token" in env_file.read_text(encoding="utf-8")
    assert "AGORA_BOOTSTRAP_AGENT_TOKEN=p2-agent-token" in env_file.read_text(encoding="utf-8")

    engine = create_engine(database_url)
    with engine.connect() as connection:
        project_count = connection.scalar(text("SELECT count(*) FROM projects WHERE slug = 'payments-core'"))
        asset_count = connection.scalar(text("SELECT count(*) FROM assets WHERE project_id = :project_id"), first)
        job_count = connection.scalar(text("SELECT count(*) FROM project_initialization_jobs WHERE project_id = :project_id"), first)
        context_count = connection.scalar(text("SELECT count(*) FROM context_packs WHERE project_id = :project_id"), first)
        work_session_count = connection.scalar(
            text(
                """
                SELECT count(*)
                FROM work_sessions
                JOIN work_items ON work_items.id = work_sessions.work_item_id
                WHERE work_items.project_id = :project_id
                """
            ),
            first,
        )
        session_event_count = connection.scalar(text("SELECT count(*) FROM session_events"))
        project_remote = connection.scalar(text("SELECT git_remotes FROM projects WHERE id = :project_id"), first)

    assert project_count == 1
    assert asset_count >= 6
    assert job_count == 1
    assert context_count == 0
    assert work_session_count == 0
    assert session_event_count == 0
    assert str(repo_path) not in project_remote
    assert first["git_remote"] in project_remote
