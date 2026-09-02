# P3 Context Governance 黑盒验证步骤

适用范围：验证真实 AI 工具通过 Agora Harness/MCP 上传项目上下文提案，人工在 Agora Web 审查批准，其他 AI 工具复用 accepted ContextRevision，并验证 feature branch 不会提前覆盖 main 上下文。

## 1. 启动服务

由开发者启动以下服务，并确认 Web 可访问：

```bash
export AGORA_DATABASE_URL=sqlite+pysqlite:////Users/daniel/Documents/Agora/.worktrees/agora-p0/.agora/p3-blackbox.db
export AGORA_BOOTSTRAP_HUMAN_TOKEN=p3-human-token
export AGORA_BOOTSTRAP_AGENT_TOKEN=p3-agent-token
export AGORA_BOOTSTRAP_ORG_ID=local-org
export AGORA_WEB_HUMAN_TOKEN=p3-human-token
export AGORA_API_URL=http://127.0.0.1:18100

.venv/bin/uvicorn apps.api.main:app --host 127.0.0.1 --port 18100
cd apps/web && AGORA_API_URL=http://127.0.0.1:18100 AGORA_WEB_HUMAN_TOKEN=p3-human-token npm run dev -- --hostname 127.0.0.1 --port 13100
```

Worker 可按需单次运行：

```bash
AGORA_DATABASE_URL=sqlite+pysqlite:////Users/daniel/Documents/Agora/.worktrees/agora-p0/.agora/p3-blackbox.db .venv/bin/python -m apps.workers.main outbox-once --limit 20
```

## 2. AI 工具验证：上传初始项目上下文

在 AI 工具中接入 Agora MCP，使用 agent token `p3-agent-token`。

操作：

1. 让 AI 工具对本地真实项目执行 `agora_start_work`。
2. 让 AI 工具扫描本地代码和文档。
3. 让 AI 工具调用 `agora_submit_context_proposal`，提交 `initial` 或 `task_update` 类型 proposal。

预期：

- AI 工具返回 `operation=submit_context_proposal`。
- 返回 `next_actions[0].type=human_review_context_proposal`。
- 返回的 proposal 状态是 `submitted`。
- Agora Web 的项目 Context 页面可以看到 Context proposals。

## 3. Web 验证：人工审查并批准

打开：

```text
http://127.0.0.1:13100/projects
```

操作：

1. 进入目标项目。
2. 打开 `Context`。
3. 在 `Context proposals` 中点击 `View proposal`。
4. 检查 proposal 的 summary、content、source anchors、provenance。
5. 在 `Human review` 中确认：
   - `Expected head`
   - `Observed head SHA`
   - `Contains target commit`
   - 必要时填写 `Merge target branch` 并勾选 `Merged to target branch`
6. 点击 `Approve proposal`。

预期：

- 页面回到 proposal 详情。
- proposal 状态变为 `approved`。
- `Accepted revision` 不再是 `Not accepted`。
- 审批表单消失。
- Context streams 中对应 branch 的 `head_revision_id` 更新。

## 4. AI 工具验证：复用 accepted context

操作：

1. 用另一个 AI 工具或新的 AI 会话调用 `agora_start_work`。
2. 调用 `agora_prepare_context`。

预期：

- 返回 `provisional=false`。
- `freshness.context_coverage=fresh`。
- `freshness.accepted_revision_id` 有值。
- `capability_pins.context_revision_id` 等于 accepted revision。
- AI 工具不需要重新完整分析整个项目。

## 5. Feature branch 保护验证

操作 A：功能分支 proposal。

1. AI 工具提交 proposal，`target_branch=feature/PAY-318-refund-audit`。
2. Web 审批时 `Revision signal.target_branch` 保持同一 feature branch。

预期：

- feature branch ContextStream 的 head 更新。
- main ContextStream 的 head 不变化。

操作 B：未合并前尝试更新 main。

1. AI 工具提交 proposal，`target_branch=main`，但 provenance 中包含 `source_branch=feature/...`。
2. Web 审批时不勾选 `Merged to target branch`。

预期：

- 审批失败。
- 页面显示错误。
- main ContextStream 不被更新。

操作 C：已合并后更新 main。

1. 重复操作 B。
2. Web 审批时填写 `Merge target branch=main` 并勾选 `Merged to target branch`。

预期：

- 审批成功。
- main ContextStream 更新到新的 accepted revision。

## 6. Outbox worker 验证

审批成功后运行：

```bash
AGORA_DATABASE_URL=sqlite+pysqlite:////Users/daniel/Documents/Agora/.worktrees/agora-p0/.agora/p3-blackbox.db .venv/bin/python -m apps.workers.main outbox-once --limit 20
```

预期：

- 输出包含 `completed=1` 或在无待处理事件时 `processed=0`。
- 重复运行不会重复处理已 completed 事件。
- 如果事件 payload 与当前 stream head 不一致，事件会进入 retry/dead 诊断路径，不会静默成功。
