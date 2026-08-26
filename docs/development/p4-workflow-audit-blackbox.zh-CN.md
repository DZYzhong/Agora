# P4 Workflow Audit 黑盒验证步骤

适用范围：验证真实 AI 工具通过 Agora Harness/MCP 启动任务、按项目流程推进步骤、提交固定产物和人工确认；Agora Web 以项目经理/质量人员可读的方式展示 WorkItem workflow audit。

## 1. 由开发者启动服务

开发者在仓库根目录启动生产式本地服务。不要设置 `AGORA_TEST_AUTH_BYPASS`。

```bash
export AGORA_DATABASE_URL=sqlite+pysqlite:////Users/daniel/Documents/Agora/.worktrees/agora-p0/.agora/p4-blackbox.db
export AGORA_BOOTSTRAP_HUMAN_TOKEN=p4-human-token
export AGORA_BOOTSTRAP_AGENT_TOKEN=p4-agent-token
export AGORA_BOOTSTRAP_ORG_ID=local-org
export AGORA_WEB_HUMAN_TOKEN=p4-human-token
export NEXT_PUBLIC_AGORA_API_URL=http://127.0.0.1:18120

.venv/bin/uvicorn apps.api.main:app --host 127.0.0.1 --port 18120
```

另开终端启动 Web：

```bash
cd apps/web
NEXT_PUBLIC_AGORA_API_URL=http://127.0.0.1:18120 AGORA_WEB_HUMAN_TOKEN=p4-human-token npm run dev -- --hostname 127.0.0.1 --port 13120
```

AI 工具 MCP 侧使用：

```text
AGORA_API_URL=http://127.0.0.1:18120
AGORA_AGENT_TOKEN=p4-agent-token
```

## 2. AI 工具黑盒操作：开始任务

在 AI 工具中打开一个真实本地软件项目，然后输入类似任务：

```text
请接入 Agora，开始 AG-888：补充支付导出权限审计。
先识别当前项目和任务，然后获取 Agora 项目上下文。
如果 Agora 中已有 workflow，请按 workflow 的当前步骤推进，不要跳步。
```

预期：

- AI 工具通过 MCP 调用 `agora_start_work`。
- 返回中有 `work_item_id`、`session_id`、`workflow_version_id`。
- 返回的下一步是准备上下文或继续 workflow 当前步骤。
- AI 工具不需要你手工调用 HTTP API。

## 3. AI 工具黑盒操作：完成 Analysis 步骤

继续让 AI 工具完成分析步骤，并要求它提交固定产物和人工确认：

```text
请完成当前 workflow 的 analysis 步骤。
输出一个 analysis_note，内容要包含：影响范围、风险点、需要设计阶段确认的问题。
我人工确认：分析范围通过，可以进入设计。
请把这次步骤产物和人工确认上传到 Agora。
```

预期：

- AI 工具调用 `agora_complete_workflow_step`。
- `step_key=analysis`。
- payload 中包含 `artifacts`，至少一条 `type=analysis_note`。
- payload 中包含 `human_confirmation`，`decision=approved`。
- 返回中 `completed_step.status=completed`。
- 返回中 `next_step.step_key=design` 且 `next_step.status=running`。

## 4. Web 黑盒操作：查看 WorkItem 列表

打开：

```text
http://127.0.0.1:13120/projects
```

操作：

1. 进入 AI 工具刚才识别或创建的项目。
2. 点击 `Work items`。
3. 找到 `AG-888` 或对应任务标题。

预期：

- WorkItem 出现在列表中。
- `Stage` 显示为 `design`。
- `Sessions` 至少为 `1`。
- `Participants` 有参与者。

## 5. Web 黑盒操作：查看 Workflow audit

进入该 WorkItem 详情页。

预期页面应看到：

- `Task state`
- `Latest context state`
- `Capability pins`
- `Workflow audit`
- `Work sessions`

在 `Workflow audit` 中检查：

- `Analysis` 步骤状态是 `completed`。
- `Design` 步骤状态是 `running`。
- `Analysis` 步骤下能看到 `Required outputs` 包含 `analysis_note`。
- `Analysis` 步骤下能看到 `Step outputs`，数量至少为 `1`。
- 展开的产物中能看到 AI 工具提交的分析标题和内容。
- `Analysis` 步骤下能看到 `Human confirmations`，数量至少为 `1`。
- 人工确认中能看到 `approved` 和确认意见。

## 6. 跳步保护验证

在同一个 AI 工具会话中输入：

```text
请直接完成 implementation 步骤，跳过 design 和 review。
```

预期：

- AI 工具收到 Agora 的拒绝。
- 错误码为 `WORKFLOW_STEP_NOT_CURRENT`。
- Web 中 WorkItem stage 仍保持当前步骤，不会跳到 implementation。
- Workflow audit 中未满足前置条件的步骤不会被标记为 completed。

## 7. 通过标准

- 用户只通过 AI 工具和 Web 页面完成验证，不需要手工调用 HTTP API。
- Agora 不在服务端扫描本地源码；本地分析和步骤产物由 AI 工具生成并上传。
- WorkItem 只有一个权威 WorkflowExecution。
- 步骤必须按当前 running step 推进，不能跳步。
- AI 工具上传的步骤产物和人工确认能在 Web WorkItem detail 中回溯。
- 项目经理、质量人员、开发人员能从 Web 看到任务当前状态和 workflow 审计证据。
