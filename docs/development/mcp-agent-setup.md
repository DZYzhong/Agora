# MCP Agent Setup

P0 exposes a stdio MCP server in `apps/mcp/server.py`.

Start Agora API first:

```bash
cd /Users/daniel/Documents/Agora/.worktrees/agora-p0
.venv/bin/uvicorn apps.api.main:app --reload --port 8000
```

MCP server command:

```bash
cd /Users/daniel/Documents/Agora/.worktrees/agora-p0
AGORA_API_URL=http://127.0.0.1:8000 .venv/bin/python -m apps.mcp.server
```

MCP client configuration:

```json
{
  "name": "agora",
  "command": "/Users/daniel/Documents/Agora/.worktrees/agora-p0/.venv/bin/python",
  "args": ["-m", "apps.mcp.server"],
  "env": {
    "AGORA_API_URL": "http://127.0.0.1:8000"
  }
}
```

Harness-oriented tools:

- `agora_start_work`
- `agora_plan_context`
- `agora_record_event`
- `agora_prepare_writeback`
- `agora_close_work`
- `agora_search_knowledge`

Recommended agent rule:

```text
When the user asks for project analysis, implementation, testing, review, summary, or risk work:
1. Call agora_start_work unless the user explicitly asks not to use Agora.
2. Call agora_plan_context before proposing implementation.
3. Run required skills returned by Agora.
4. Prepare writeback before finishing.
5. Close the work session when completed or blocked.
```

Example user prompt:

```text
帮我分析退款失败重试怎么做
```

Expected tool flow:

```text
agora_start_work
-> agora_plan_context
-> agora_prepare_writeback
-> agora_close_work
```
