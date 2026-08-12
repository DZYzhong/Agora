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
5. For implementation work, do not finish the user response until agora_close_work has been called with repo_path, agent_summary, and test_result.
6. If work is blocked, call agora_close_work with status="blocked" and agent_summary explaining the blocker.
7. If more curated knowledge is needed beyond the automatic development update, call agora_prepare_writeback explicitly before finishing.
```

Example user prompt:

```text
基于 Agora 分析 df-new-bigdata 项目的核心模块、主要业务流程和潜在风险。
```

Expected tool flow:

```text
agora_start_work
-> agora_plan_context
-> agora_close_work
```

Development memory capture:

```text
agora_close_work(
  session_id="<session id>",
  status="closed",
  repo_path="<local git repository path>",
  base_ref="HEAD",
  agent_summary="Implemented the new feature and updated related tests.",
  test_result="pytest -v passed"
)
```

When `repo_path`, `agent_summary`, or `test_result` is provided, Agora creates a `development_update` writeback draft. The draft must still be reviewed in the Web UI and accepted before it becomes reusable project knowledge.

The generated `development_update` draft is structured for review:

- `功能变更`: the agent's task summary.
- `影响范围`: changed files grouped as source, tests, config, docs, or other.
- `Git Diff 摘要`: repository path, comparison range, changed files, and diff stats.
- `测试结果`: checks reported by the agent, or a warning that tests were not supplied.
- `风险与注意事项`: deterministic risk hints such as config changes or source changes without test changes.

Review loop:

```text
agora_close_work creates draft
-> reviewer opens /projects/<project_id>/writebacks
-> reviewer accepts or rejects
-> accepted draft becomes a writeback asset
-> later agora_plan_context can retrieve that development update as project knowledge
```
