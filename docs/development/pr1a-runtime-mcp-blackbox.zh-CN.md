# PR1A Runtime and MCP Hardening 黑盒验证步骤

目标：通过 AI 工具和 Web UI（不直接调用 HTTP API）验证 Agora 已具备诚实的协议 1.1 传输、服务端不再接受本地仓库路径、以及工作流步骤只能以摘要方式完成的安全边界。

> **重要**：PR1A 仅适用于本地开发、演示和受控试点。它**不是**生产或敏感数据部署版本：未打类型的 Artifact 上传和人工审批在 PR1B/PR1C 实现前保持阻塞。

## 验证边界

- AI 工具（Codex / Cursor / Claude Code 等）通过 Agora MCP 调用 Harness。
- MCP 工具清单包含 `agora_complete_workflow_step` 和 `agora_close_work`，协议协商为 `1.1`。
- `agora_complete_workflow_step` 只接受 `idempotency_key`、`session_id`、`step_key` 和 `summary`；不暴露 artifacts 或 human_confirmation。
- 服务端不再接受 `repo_path`/`base_ref`/`head_ref`：协议 1.1 直接拒绝，生产环境拒绝旧路径关闭。
- `start-work -> complete-workflow-step -> close-work` 在单个会话中可用 AI 工具完整推进。
- Web 项目页不提供任何服务端本地仓库路径或重试控件。
- Artifact 上传返回 `PR1_UPLOAD_POLICY_REQUIRED`，人工审批返回 `PR1_APPROVAL_POLICY_REQUIRED`（PR1B/PR1C 前保持阻塞）。

## 前置条件

1. 准备环境变量（development 环境演练即可，production 环境必须用 PostgreSQL）：

```bash
export AGORA_ENV=development
export AGORA_DATABASE_URL=sqlite+pysqlite:///.agora/pr1a-blackbox/agora.db
export AGORA_BOOTSTRAP_ORG_ID=local-org
export AGORA_BOOTSTRAP_HUMAN_TOKEN=pr1a-human-token
export AGORA_BOOTSTRAP_AGENT_TOKEN=pr1a-agent-token
export AGORA_BOOTSTRAP_CI_TOKEN=pr1a-ci-token
export AGORA_WEB_HUMAN_TOKEN=pr1a-human-token
```

2. 启动 API：

```bash
.venv/bin/uvicorn apps.api.main:app --host 127.0.0.1 --port 18140
```

3. 在 Web 目录启动管理界面：

```bash
cd apps/web
AGORA_API_URL=http://127.0.0.1:18140 AGORA_WEB_HUMAN_TOKEN=pr1a-human-token npm run dev -- --hostname 127.0.0.1 --port 13140
```

4. AI 工具配置 Agora MCP stdio server，使用 `AGORA_AGENT_TOKEN=pr1a-agent-token`，并在本地 Git 工作区运行（`AGORA_WORKSPACE_ROOT` 指向该仓库）。

## 步骤 1：AI 工具查看协议与工具清单

在 AI 工具中调用 `agora_get_protocol_manifest`。

期望：

- `harness_protocol.current = "1.1"`，`supported = ["1.0", "1.1"]`。
- `tools.canonical` 包含 `agora_complete_workflow_step` 和 `agora_close_work`。
- `tools.deprecated` 包含 `agora_plan_context` 等旧工具及其 `canonical_tool`。
- 工具清单中 `agora_complete_workflow_step` 只要求 `session_id`、`step_key`、`summary` 和 `idempotency_key`。

## 步骤 2：AI 工具开始工作（start -> complete -> close）

1. 调用 `agora_start_work`（提供 `user_message` 和 `idempotency_key`）。
2. 调用 `agora_prepare_context`（提供 `session_id` 和 `idempotency_key`）。
3. 完成当前工作流步骤：调用 `agora_complete_workflow_step`（提供 `session_id`、`step_key=analysis`、`summary` 和 `idempotency_key`）。
4. 关闭会话：调用 `agora_close_work`（提供 `session_id`、`idempotency_key`，可选 `agent_summary`/`test_result`）。

期望：

- 每次调用都返回 `protocol_version = "1.1"`。
- 每次写操作都要求且接受 `idempotency_key`；相同 key + 相同 payload 重放返回原结果，不同 payload 返回冲突。
- `complete-workflow-step` 只接受摘要：AI 工具无法传入 artifacts 或 human_confirmation。
- `close-work` 不要求也不接受服务端仓库路径；变更捕获由本地 Connector 生成并只上传相对路径与统计计数。

## 步骤 3：Web 查看会话状态且无路径控件

打开 `http://127.0.0.1:13140/projects` 进入对应项目：

- 项目首页**不包含**"Initialize from local repository"、"Repository path"或 Retry 控件。
- Sessions 页面可以看到刚才关闭的会话，状态为 `closed`。
- 会话详情包含 Workflow audit（步骤完成状态）和（如有摘要时）development update 草稿。
- Work items 页面可以看到工作项阶段推进。

## 步骤 4：确认未打类型内容仍被阻塞

在 development 或 production 环境中，通过 API 边界（AI 工具无法从 1.1 schema 传入）确认：

- 带 artifacts 的完成请求返回 `PR1_UPLOAD_POLICY_REQUIRED`。
- 带 human_confirmation 的完成请求返回 `PR1_APPROVAL_POLICY_REQUIRED`。
- 仅摘要的完成请求正常推进工作流。

这些临时错误由 PR1B/PR1C 的 typed upload/approval policy 取代，在此之前不得绕过检查。

## 验证记录

在 `docs/superpowers/plans/2026-08-28-agora-pr1a-runtime-mcp-hardening.md` 的 Task 10 执行记录中登记：

- 用户是否通过 AI 工具完成 start -> complete -> close，且未手动调用 HTTP API。
- 使用的 MCP server 版本、Connector 版本和协议版本。
- Web 页面展示的会话状态截图或文字记录。
- 是否验证了 artifact/confirmation 被阻塞。
- 测试计数与构建结果（`pytest`、`npm run build` 等）。

只有以上全部通过且记录在案，PR1A 的 `black-box passed` 才可标记；PR1 整体 exit gate 仍要求 PR1B/PR1C。
