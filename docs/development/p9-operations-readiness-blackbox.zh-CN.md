# P9 Production and Operations Readiness 黑盒验证步骤

目标：验证 Agora 在生产-like 环境中具备基本部署、可观测、备份恢复和角色流程冒烟能力。用户仍通过 AI 工具和 Web UI 验证产品行为；运维探针用于部署系统、CI 或值班人员确认服务状态。

## 验证边界

- API 提供 `/health`、`/ready` 和 `/metrics`。
- `/ready` 必须检查数据库连通性、Alembic schema revision 和关键配置。
- `/metrics` 输出 Prometheus 风格文本，至少包含 ready、schema revision、项目数量和待审上下文数量。
- SQLite 可用于本地演练；生产-like 验证应优先使用 PostgreSQL。
- 备份和恢复由运维命令或数据库工具完成，恢复后仍以 AI 工具和 Web 完成业务冒烟。

## 前置条件

1. 准备环境变量：

```bash
export AGORA_ENV=production-like
export AGORA_DATABASE_URL=postgresql+psycopg://agora:agora@localhost:5432/agora
export AGORA_BOOTSTRAP_ORG_ID=local-org
export AGORA_BOOTSTRAP_HUMAN_TOKEN=p9-human-token
export AGORA_BOOTSTRAP_AGENT_TOKEN=p9-agent-token
export AGORA_BOOTSTRAP_CI_TOKEN=p9-ci-token
export AGORA_WEB_HUMAN_TOKEN=p9-human-token
```

2. 启动 PostgreSQL、API 和 Web。
3. AI 工具已配置 Agora MCP，并使用 agent token。

## 步骤 1：验证服务探针

打开运维终端或部署健康检查：

```text
GET http://127.0.0.1:8000/health
GET http://127.0.0.1:8000/ready
GET http://127.0.0.1:8000/metrics
```

期望：

- `/health` 返回 `status = ok`。
- `/ready` 返回 `status = ready`。
- `/ready.checks.database.status = ok`。
- `/ready.checks.schema.revision` 是当前 Alembic head。
- `/ready.checks.configuration.missing_required = []`。
- `/metrics` 包含 `agora_ready`、`agora_schema_revision_info`、`agora_projects_total`、`agora_pending_context_proposals_total`。

## 步骤 2：Developer 冒烟

在 AI 工具中输入：

```text
请通过 Agora 开始任务 AG-9001：完善登录失败提示。准备上下文，并按项目流程生成分析与设计产物。
```

期望：

- AI 工具调用 `agora_start_work` 和 `agora_prepare_context`。
- Agora 创建或复用 WorkItem `AG-9001`。
- Web 的 WorkItem 页面能看到 Workflow audit。

## 步骤 3：Reviewer 冒烟

让 AI 工具提交一个 ContextProposal 或 SkillCandidate，然后用 Web 进入项目的 Context 或 Skills 审批页面。

期望：

- Reviewer 可以审批。
- agent token 不能审批。
- Security audit 能看到 allow/deny 决策。

## 步骤 4：Project Manager 冒烟

在 AI 工具中输入：

```text
请通过 Agora 查询当前项目状态，重点看任务阶段、待审项、质量状态和阻塞项。
```

期望：

- AI 工具调用 `agora_get_project_status`。
- 返回 WorkItems、Delivery readiness、Pending approvals、Blockers。
- Web `Project status` 与 AI 工具看到一致的数据。

## 步骤 5：Quality 冒烟

让 AI 工具记录一条失败质量证据，再查询项目状态。

期望：

- AI 工具调用 `agora_record_evidence`。
- `Quality` 视角能看到 failed evidence。
- `delivery_readiness.state = blocked`。
- Web `Latest evidence` 能追溯命令、结论和来源。

## 步骤 6：备份与恢复演练

对 PostgreSQL 执行一次备份，再恢复到一个新的数据库实例或新的 database name。

期望：

- 恢复后的 API `/ready` 仍为 ready。
- Web 能打开项目列表和项目详情。
- AI 工具能继续查询 `agora_get_project_status`。
- 已审批的 ContextRevision、SkillVersion、WorkItem、QualityEvidence 和 SecurityAuditEvent 没有丢失。

## 通过标准

- 生产-like 环境能启动 API 和 Web。
- `/ready` 能发现数据库、schema 和配置问题。
- `/metrics` 能被监控系统抓取。
- Developer、Reviewer、Project Manager、Quality 四类角色的核心路径都能通过 AI 工具和 Web 完成。
- 备份恢复后，治理状态和项目资产仍可查询。
