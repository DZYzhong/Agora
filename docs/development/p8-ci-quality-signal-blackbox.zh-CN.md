# P8 CI QualitySignal 黑盒验证步骤

目标：验证 Agora 能接收真实 CI 流水线的质量信号和仓库 RevisionSignal，自动写入项目 WorkItem 的质量证据，并在代码分支更新时创建待审 ContextProposal，让 AI 工具和 Web 同步看到最新质量与上下文状态。

## 验证边界

- 用户不需要手动调用 HTTP API。
- CI 信号由 CI 脚本或 AI 工具准备的 CI-like 命令发送。
- CI 使用 `AGORA_BOOTSTRAP_CI_TOKEN` 对应的 service credential。
- human token 和 agent token 不能上报 CI 质量信号，错误码应为 `CI_CREDENTIAL_REQUIRED`。
- Web UI 只负责查看结果：`Project status` 会显示 CI evidence、quality dimensions、delivery readiness 和 blockers；`Context` 会显示自动创建的 ContextProposal。

## 前置条件

1. Agora API 和 Web 已启动。
2. 启动 API 时配置：

```bash
export AGORA_BOOTSTRAP_HUMAN_TOKEN=p8-human-token
export AGORA_BOOTSTRAP_AGENT_TOKEN=p8-agent-token
export AGORA_BOOTSTRAP_CI_TOKEN=p8-ci-token
export AGORA_BOOTSTRAP_ORG_ID=local-org
```

3. AI 工具已接入 Agora MCP，使用 agent token。
4. 本地项目已有或新建一个 Agora project。

## 步骤 1：AI 工具开始真实任务

在 AI 工具中输入：

```text
请通过 Agora 开始任务：AG-1201 支付回调重试幂等修复。
请准备上下文，并说明这个任务后续会由 CI 自动回传测试结果。
```

期望：

- AI 工具调用 `agora_start_work`。
- AI 工具调用 `agora_prepare_context`。
- Agora 识别或创建 WorkItem `AG-1201`。

## 步骤 2：用 CI-like 脚本上报质量信号

让 AI 工具在本地项目中准备或执行一段 CI-like 脚本。脚本可以放在临时文件里，由 AI 工具执行，不需要用户手动调用 HTTP API。

脚本行为：

- 使用 `AGORA_BOOTSTRAP_CI_TOKEN` 对应 token。
- 调用 `/integrations/ci/quality-signal`。
- 传入：
  - `project_id`
  - `work_item_key = AG-1201`
  - `status = passed` 或 `failed`
  - `conclusion`
  - `command`
  - `output_summary`
  - `provider`
  - `run_id`
  - `commit_sha`
  - `branch`

期望：

- 返回 `operation = ingest_ci_quality_signal`。
- 返回 `evidence.source = ci`。
- 返回 `evidence.evidence_type = ci`。
- 返回的 `project_status.quality_dimensions.ci` 包含本次 passed/failed 数量。

## 步骤 3：用 CI-like 脚本上报仓库 RevisionSignal

让 AI 工具准备或执行另一段 CI-like 脚本，模拟真实仓库 push/merge 后的自动化上报。

脚本行为：

- 使用 CI service token。
- 调用 `/integrations/repository/revision-signal`。
- 传入：
  - `project_id`
  - `provider`
  - `repository_identity`
  - `branch`
  - `observed_head_sha`
  - `previous_head_sha`
  - `signal_type = push`
  - `work_item_key`
  - `raw_ref`

期望：

- 返回 `operation = ingest_repository_revision_signal`。
- 如果 accepted ContextRevision 的 commit 与 `observed_head_sha` 不一致，返回 `context_freshness.state = stale`。
- 返回 `signal.status = stale_context`。
- 自动创建 `ContextProposal`，`type = refresh`、`status = submitted`。
- `ContextProposal.from_commit_sha` 是旧上下文 commit，`to_commit_sha` 是新仓库 head commit。

## 步骤 4：AI 工具查询项目状态

在 AI 工具中输入：

```text
请通过 Agora 查询当前项目状态，重点看 AG-1201 的 CI 质量证据、交付就绪状态和阻塞项。
```

期望：

- AI 工具调用 `agora_get_project_status`。
- 如果 CI 上报 failed，项目 `delivery_readiness.state = blocked`。
- 如果 CI 上报 failed，`blockers` 中有 `FAILING_QUALITY_EVIDENCE`。
- `Latest evidence` 对应数据能追溯到 CI command/run id/commit。

## 步骤 5：Web 查看 Project status 和 Context

打开 Web：

```text
http://127.0.0.1:3000/projects
```

操作：

1. 进入项目。
2. 点击 `Project status`。
3. 查看 `Quality dimensions` 和 `Latest evidence`。
4. 再进入 `Context`，查看自动创建的 refresh ContextProposal。

期望：

- `Quality dimensions` 里出现 `ci`。
- `Latest evidence` 能看到 CI 测试命令、状态和结论。
- Web 状态与 AI 工具查询一致。
- `ContextProposal` 列表里能看到仓库 RevisionSignal 创建的 refresh proposal。

## 步骤 6：验证错误凭证不能上报 CI

让 AI 工具或 CI-like 脚本分别尝试使用 human token 和 agent token 上报同一信号。

期望：

- 两次都返回 403。
- 错误码都是 `CI_CREDENTIAL_REQUIRED`。

## 通过标准

- CI service credential 可以上报质量信号。
- human/agent credential 不能上报 CI 质量信号。
- CI 信号能自动创建或定位 WorkItem。
- CI 信号被保存为 `QualityEvidence`，并进入项目状态聚合。
- 仓库 RevisionSignal 能在上下文落后时自动创建待审 `ContextProposal`。
- Web `Project status` 和 AI 工具查询看到一致的 CI 证据。
- 用户不需要手动调用 HTTP API。
