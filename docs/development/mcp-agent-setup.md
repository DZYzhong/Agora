# MCP Agent Setup

P0 exposes a stdio MCP server in `apps/mcp/server.py`.

Start Agora API first:

```bash
cd /Users/daniel/Documents/Agora/.worktrees/agora-p0
.venv/bin/uvicorn apps.api.main:app --reload --port 8011
```

MCP server command:

```bash
cd /Users/daniel/Documents/Agora/.worktrees/agora-p0
AGORA_API_URL=http://127.0.0.1:8011 .venv/bin/python -m apps.mcp.server
```

MCP client configuration:

```json
{
  "name": "agora",
  "command": "/Users/daniel/Documents/Agora/.worktrees/agora-p0/.venv/bin/python",
  "args": ["-m", "apps.mcp.server"],
  "env": {
    "AGORA_API_URL": "http://127.0.0.1:8011"
  }
}
```

The local API persists data in `.agora/agora.db` by default. Override it with `AGORA_DATABASE_URL` when needed.

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
2. Pass the original user message to agora_start_work. If available, also pass git remote get-url origin as repo_remote.
3. Call agora_plan_context before proposing implementation. If source_refs are returned, use them as the primary project context.
4. Run required skills returned by Agora.
5. Prepare writeback before finishing.
6. Close the work session when completed or blocked.
```

Example user prompt:

```text
基于 Agora 分析 df-new-bigdata 项目的核心模块、主要业务流程和潜在风险。
```

Expected tool flow:

```text
agora_start_work
-> agora_plan_context
-> agora_prepare_writeback
-> agora_close_work
```
