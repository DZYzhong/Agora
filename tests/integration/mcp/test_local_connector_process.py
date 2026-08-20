import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


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
                    "PYTHONPATH": "/Users/daniel/Documents/Agora/.worktrees/agora-p0",
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
