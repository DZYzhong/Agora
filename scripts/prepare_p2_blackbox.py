from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


PROJECT_NAME = "Payments Core"
PROJECT_SLUG = "payments-core"
PROJECT_DESCRIPTION = "支付核心服务，用于验证 P2 真实 AI 工具接入流程。"
GIT_REMOTE = "git@example.com:agora/payments-core.git"
ISSUE_KEY = "PAY-241"


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def _write_if_changed(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def _run_git(repo_path: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo_path, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _ensure_git_repo(repo_path: Path) -> None:
    if not (repo_path / ".git").exists():
        _run_git(repo_path, "init")
    _run_git(repo_path, "config", "user.name", "Agora Blackbox")
    _run_git(repo_path, "config", "user.email", "agora-blackbox@example.com")
    remotes = subprocess.run(
        ["git", "remote"],
        cwd=repo_path,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.splitlines()
    if "origin" in remotes:
        _run_git(repo_path, "remote", "set-url", "origin", GIT_REMOTE)
    else:
        _run_git(repo_path, "remote", "add", "origin", GIT_REMOTE)
    _run_git(repo_path, "add", ".")
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo_path)
    if diff.returncode != 0:
        _run_git(repo_path, "commit", "-m", "seed payments core blackbox repository")


def _write_repository(repo_path: Path) -> None:
    _write_if_changed(
        repo_path / "README.md",
        """# Payments Core

支付核心服务负责订单支付状态流转、退款幂等和运营审计。

本仓库用于 Agora P2 真实 AI 工具黑盒验证。AI 工具应从本地仓库读取代码和文档，
再通过 Agora MCP 上传本次任务的上下文；Agora 服务端不应从 start-work 请求读取本地源码。
""",
    )
    _write_if_changed(
        repo_path / "docs/issues/PAY-241.md",
        """# PAY-241 支付状态流转审计

## 背景

研发团队需要补齐支付状态机的审计能力。现有状态包括 `created`、`authorized`、
`captured`、`refund_pending`、`refunded` 和 `failed`。

## 验收标准

- 状态流转必须可追踪触发来源、操作者和请求号。
- 重复请求不能生成重复审计事件。
- AI 工具需要输出分析、设计、自测和上传记录。
""",
    )
    _write_if_changed(
        repo_path / "docs/architecture.md",
        """# 支付服务架构

`PaymentStateMachine` 负责合法状态流转；`AuditSink` 负责落库前的事件结构化；
`PaymentApplicationService` 编排请求校验、幂等键和状态更新。
""",
    )
    _write_if_changed(
        repo_path / "src/payments/state_machine.py",
        '''class PaymentStateMachine:
    transitions = {
        "created": {"authorized", "failed"},
        "authorized": {"captured", "failed"},
        "captured": {"refund_pending"},
        "refund_pending": {"refunded", "failed"},
    }

    def can_transition(self, current: str, target: str) -> bool:
        return target in self.transitions.get(current, set())
''',
    )
    _write_if_changed(
        repo_path / "src/payments/audit.py",
        '''from dataclasses import dataclass


@dataclass(frozen=True)
class PaymentAuditEvent:
    order_id: str
    from_state: str
    to_state: str
    request_id: str
    operator: str
''',
    )
    _write_if_changed(
        repo_path / "src/payments/service.py",
        '''from .audit import PaymentAuditEvent
from .state_machine import PaymentStateMachine


class PaymentApplicationService:
    def __init__(self, state_machine: PaymentStateMachine):
        self.state_machine = state_machine

    def build_audit_event(self, order_id: str, current: str, target: str, request_id: str, operator: str):
        if not self.state_machine.can_transition(current, target):
            raise ValueError("invalid payment transition")
        return PaymentAuditEvent(order_id, current, target, request_id, operator)
''',
    )
    _write_if_changed(
        repo_path / "tests/test_payment_state_machine.py",
        '''from src.payments.state_machine import PaymentStateMachine


def test_created_can_authorize():
    assert PaymentStateMachine().can_transition("created", "authorized")


def test_refunded_is_terminal():
    assert not PaymentStateMachine().can_transition("refunded", "captured")
''',
    )
    _write_if_changed(repo_path / "pyproject.toml", "[tool.pytest.ini_options]\npythonpath = [\".\"]\n")
    _ensure_git_repo(repo_path)


def _client() -> Any:
    from fastapi.testclient import TestClient

    from apps.api.main import app

    return TestClient(app)


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _raise_for_status(response: Any) -> None:
    if 200 <= response.status_code < 300:
        return
    raise SystemExit(f"API request failed: {response.status_code} {response.text}")


def _ensure_project(client: Any, human_token: str) -> dict:
    list_response = client.get("/projects", headers=_headers(human_token))
    _raise_for_status(list_response)
    for project in list_response.json():
        if project["slug"] == PROJECT_SLUG:
            return project
    create_response = client.post(
        "/projects",
        headers=_headers(human_token),
        json={
            "org_id": os.environ["AGORA_BOOTSTRAP_ORG_ID"],
            "name": PROJECT_NAME,
            "slug": PROJECT_SLUG,
            "description": PROJECT_DESCRIPTION,
            "git_remotes": [GIT_REMOTE],
        },
    )
    _raise_for_status(create_response)
    return create_response.json()


def _ensure_initialized(client: Any, *, project_id: str, repo_path: Path, human_token: str) -> dict:
    jobs_response = client.get(f"/projects/{project_id}/initialization-jobs", headers=_headers(human_token))
    _raise_for_status(jobs_response)
    for job in jobs_response.json():
        if job["status"] == "completed" and job["asset_count"] > 0:
            return job
    init_response = client.post(
        f"/projects/{project_id}/initialize-local",
        headers=_headers(human_token),
        json={"repo_path": str(repo_path)},
    )
    _raise_for_status(init_response)
    return init_response.json()


def prepare(root: Path, database_url: str) -> dict:
    root = root.expanduser().resolve()
    human_token = _require_env("AGORA_BOOTSTRAP_HUMAN_TOKEN")
    _require_env("AGORA_BOOTSTRAP_AGENT_TOKEN")
    os.environ["AGORA_ENV"] = "development"
    os.environ.pop("AGORA_TEST_AUTH_BYPASS", None)
    os.environ["AGORA_LOCAL_INIT_ROOT"] = str(root)
    os.environ.setdefault("AGORA_BOOTSTRAP_ORG_ID", "local-org")
    os.environ["AGORA_DATABASE_URL"] = database_url

    root.mkdir(parents=True, exist_ok=True)
    repo_path = root / "payments-core"
    _write_repository(repo_path)
    env_file = root / "p2-blackbox.env"
    _write_if_changed(
        env_file,
        "\n".join(
            [
                f"AGORA_DATABASE_URL={database_url}",
                "AGORA_ENV=development",
                f"AGORA_LOCAL_INIT_ROOT={root}",
                f"AGORA_BOOTSTRAP_ORG_ID={os.environ['AGORA_BOOTSTRAP_ORG_ID']}",
                f"AGORA_BOOTSTRAP_HUMAN_TOKEN={human_token}",
                f"AGORA_BOOTSTRAP_AGENT_TOKEN={os.environ['AGORA_BOOTSTRAP_AGENT_TOKEN']}",
                f"AGORA_WEB_HUMAN_TOKEN={human_token}",
                f"AGORA_AGENT_TOKEN={os.environ['AGORA_BOOTSTRAP_AGENT_TOKEN']}",
                "NEXT_PUBLIC_AGORA_API_URL=http://127.0.0.1:8011",
                "",
            ]
        ),
    )

    with _client() as client:
        project = _ensure_project(client, human_token)
        job = _ensure_initialized(client, project_id=project["id"], repo_path=repo_path, human_token=human_token)

    return {
        "project_id": project["id"],
        "project_slug": project["slug"],
        "repo_path": str(repo_path),
        "git_remote": GIT_REMOTE,
        "issue_key": ISSUE_KEY,
        "env_file": str(env_file),
        "database_url": database_url,
        "initialization_status": job["status"],
        "asset_count": job["asset_count"],
        "human_token_env": "AGORA_BOOTSTRAP_HUMAN_TOKEN",
        "agent_token_env": "AGORA_BOOTSTRAP_AGENT_TOKEN",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare a P2 real AI-tool black-box workspace")
    parser.add_argument("--root", type=Path, default=Path(".agora/p2-blackbox"))
    parser.add_argument("--database-url", default=os.environ.get("AGORA_DATABASE_URL", "sqlite+pysqlite:///.agora/p2-blackbox/agora.db"))
    parser.add_argument("--json", action="store_true", help="Print machine-readable setup details")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = prepare(args.root.expanduser().resolve(), args.database_url)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(f"Prepared project: {result['project_slug']} ({result['project_id']})")
        print(f"Repository: {result['repo_path']}")
        print(f"Environment: {result['env_file']}")
        print(f"Assets: {result['asset_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
