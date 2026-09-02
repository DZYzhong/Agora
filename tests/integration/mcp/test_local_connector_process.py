import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


@pytest.mark.anyio
async def test_stdio_start_work_sends_sanitized_local_observation_to_api(tmp_path):
    repo = tmp_path / "repo-with-private-source"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "dev@example.com")
    _git(repo, "config", "user.name", "Dev")
    _git(repo, "remote", "add", "origin", "https://dev:top-secret@git.example.cn/platform/api.git")
    (repo / "app.py").write_text("TRACKED_SOURCE_SECRET = 'private'\n")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-m", "initial")
    (repo / "app.py").write_text("TRACKED_SOURCE_SECRET = 'changed'\n")
    (repo / "scratch.md").write_text("UNTRACKED_SOURCE_SECRET\n")

    captured = {}

    class Recorder(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            captured["path"] = self.path
            captured["body"] = self.rfile.read(length).decode("utf-8")
            response = {
                "protocol_version": "1.0",
                "request_id": "req_1",
                "capabilities": {"local_repository_observation": True},
                "session_id": "sess_1",
                "next_action": "plan_context",
                "next_actions": [{"type": "plan_context"}],
            }
            encoded = json.dumps(response).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, *_args):
            return

    server = HTTPServer(("127.0.0.1", 0), Recorder)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    stderr_path = tmp_path / "mcp-stderr.log"
    try:
        with stderr_path.open("w+", encoding="utf-8") as errlog:
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "apps.mcp.server"],
                cwd=repo,
                env={
                    **dict(os.environ),
                    "PYTHONPATH": str(REPOSITORY_ROOT),
                    "AGORA_API_URL": f"http://127.0.0.1:{server.server_port}",
                    "AGORA_AGENT_TOKEN": "agent-token",
                },
            )
            async with stdio_client(params, errlog=errlog) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        "agora_start_work",
                        {"user_message": "实现 AG-128", "agent_type": "codex"},
                    )
    finally:
        server.shutdown()

    result_text = json.dumps(result.model_dump(), ensure_ascii=False)
    stderr_text = stderr_path.read_text(encoding="utf-8")
    combined = captured["body"] + result_text + stderr_text
    assert captured["path"] == "/harness/start-work"
    assert "git.example.cn/platform/api" in captured["body"]
    assert str(repo) not in combined
    assert "dev:" not in combined
    assert "top-secret" not in combined
    assert "TRACKED_SOURCE_SECRET" not in combined
    assert "UNTRACKED_SOURCE_SECRET" not in combined
    assert stderr_text == ""


@pytest.mark.anyio
async def test_stdio_process_completes_stateful_protocol_1_1_workflow(tmp_path):
    repo = tmp_path / "stateful-repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "dev@example.com")
    _git(repo, "config", "user.name", "Dev")
    _git(repo, "remote", "add", "origin", "https://dev:top-secret@git.example.cn/platform/api.git")
    (repo / "app.py").write_text("TRACKED_SOURCE_SECRET = 'private'\n")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-m", "initial")
    (repo / "app.py").write_text("TRACKED_SOURCE_SECRET = 'changed'\n")

    requests = []

    class Recorder(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            body = self.rfile.read(length).decode("utf-8")
            requests.append(
                {
                    "path": self.path,
                    "headers": dict(self.headers),
                    "body": body,
                }
            )
            if self.path == "/harness/start-work":
                response = {
                    "protocol_version": "1.1",
                    "request_id": "req_1",
                    "session_id": "sess_1",
                    "work_item_id": "wi_1",
                    "next_action": "plan_context",
                    "next_actions": [{"type": "prepare_context"}],
                }
            elif self.path == "/harness/complete-workflow-step":
                response = {
                    "protocol_version": "1.1",
                    "session_id": "sess_1",
                    "workflow_execution": {"id": "wf_1", "current_step_key": "design"},
                    "completed_step": {"step_key": "analysis", "status": "completed"},
                    "next_step": {"step_key": "design", "status": "running"},
                    "artifacts": [],
                    "human_confirmation": None,
                    "next_actions": [],
                }
            elif self.path == "/harness/close-work":
                response = {
                    "protocol_version": "1.1",
                    "session_id": "sess_1",
                    "status": "closed",
                }
            else:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            encoded = json.dumps(response).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, *_args):
            return

    server = HTTPServer(("127.0.0.1", 0), Recorder)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    stderr_path = tmp_path / "mcp-stderr.log"
    try:
        with stderr_path.open("w+", encoding="utf-8") as errlog:
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "apps.mcp.server"],
                cwd=repo,
                env={
                    **dict(os.environ),
                    "PYTHONPATH": str(REPOSITORY_ROOT),
                    "AGORA_API_URL": f"http://127.0.0.1:{server.server_port}",
                    "AGORA_AGENT_TOKEN": "agent-token",
                },
            )
            async with stdio_client(params, errlog=errlog) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    listed = await session.list_tools()
                    tool_names = {tool.name for tool in listed.tools}
                    assert "agora_start_work" in tool_names
                    assert "agora_complete_workflow_step" in tool_names
                    assert "agora_close_work" in tool_names
                    assert "agora_get_protocol_manifest" in tool_names

                    started = await session.call_tool(
                        "agora_start_work",
                        {
                            "user_message": "实现 AG-128",
                            "agent_type": "codex",
                            "idempotency_key": "process-key-start",
                        },
                    )
                    started_text = json.dumps(started.model_dump(), ensure_ascii=False)
                    assert "sess_1" in started_text

                    completed = await session.call_tool(
                        "agora_complete_workflow_step",
                        {
                            "session_id": "sess_1",
                            "step_key": "analysis",
                            "summary": "分析完成，人工已确认。",
                            "idempotency_key": "process-key-complete",
                        },
                    )
                    completed_text = json.dumps(completed.model_dump(), ensure_ascii=False)
                    assert '"step_key": "analysis"' in completed_text
                    assert '"status": "completed"' in completed_text

                    closed = await session.call_tool(
                        "agora_close_work",
                        {
                            "session_id": "sess_1",
                            "status": "closed",
                            "agent_summary": "完成发布风险检查并关闭会话。",
                            "idempotency_key": "process-key-close",
                        },
                    )
                    closed_text = json.dumps(closed.model_dump(), ensure_ascii=False)
                    assert '"status": "closed"' in closed_text
    finally:
        server.shutdown()

    assert [request["path"] for request in requests] == [
        "/harness/start-work",
        "/harness/complete-workflow-step",
        "/harness/close-work",
    ]
    for request in requests:
        headers = request["headers"]
        assert headers.get("Authorization") == "Bearer agent-token"
        assert headers.get("Agora-Protocol-Version") == "1.1"
        assert headers.get("Agora-Connector-Version") == "0.1.0"
        assert headers.get("Idempotency-Key"), request["path"]

    combined = "".join(request["body"] for request in requests)
    combined += stderr_path.read_text(encoding="utf-8")
    assert str(repo) not in combined
    assert "top-secret" not in combined
    assert "dev:" not in combined
    assert "TRACKED_SOURCE_SECRET" not in combined
    assert stderr_path.read_text(encoding="utf-8") == ""
