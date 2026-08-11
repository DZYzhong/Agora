# MCP Agent Setup

P0 exposes a Python-level MCP adapter boundary in `apps/mcp/tools.py`.

Harness-oriented tools:

- `agora_start_work`
- `agora_plan_context`
- `agora_fetch_context_ref`
- `agora_run_skill`
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
-> agora_run_skill
-> agora_prepare_writeback
-> agora_close_work
```
