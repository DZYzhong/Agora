# Agora 技术架构设计

> 文档状态：当前技术架构单一事实源
>
> 更新时间：2026-08-14
>
> 产品依据：`docs/superpowers/specs/2026-08-14-agora-product-functional-design.zh-CN.md`
>
> 实施顺序：`docs/superpowers/plans/2026-08-13-agora-p1-p9-roadmap.md`

## 1. 架构结论

Agora 采用“本地执行平面 + 服务端控制平面”的模块化单体架构。

- AI 工具和 Local Connector 在客户本地或 CI runner 访问源码、Git 和模型。
- Agora 服务端不依赖客户源码访问权，负责 Harness 编排、团队状态、版本治理、审批、审计和分发。
- Harness Coordinator 是 AI 工具接入 Agora 的稳定任务级门面，也是产品技术核心。
- Postgres 是事实源；对象存储保存大型内容；搜索和向量索引是可重建投影。
- Accepted ContextRevision、WorkflowVersion 和 SkillVersion 不可变。
- 多人并发通过 branch-scoped head、expected revision 和乐观锁处理。
- Web UI 访问治理领域，不承担本地源码扫描和 AI 分析职责。

首个可用版本保持模块化单体，不提前拆分微服务，不强制引入 OpenSearch、Qdrant、Neo4j、Temporal 或中心化 LLM Gateway。

## 2. 架构目标

- 支持不同 AI 工具自动接入同一个项目 Harness。
- 在不上传完整源码的情况下共享可追溯项目上下文。
- 让 Harness 返回任务相关、受 token budget 控制的 ContextBundle。
- 支持多人、多 Session、并发分支和上下文更新。
- 支持项目流程、人工确认、任务产物和质量证据。
- 支持项目经理、技术负责人和质量人员查询可信状态。
- 支持 Context、Skill、Workflow 的审批、版本和回滚。
- 支持网络失败、客户端重试和异步索引失败，不产生重复或静默覆盖。
- 支持本地开发、团队私有部署和后续托管部署。

## 3. 非目标

- Agora 服务端默认不克隆或分析客户仓库。
- Harness 不直接调用客户 AI 模型替代本地 AI 工具完成项目分析。
- 不把 Session Event 当作完整项目管理模型。
- 不使用向量数据库作为项目上下文事实源。
- 不在 P2 就拆成多个独立部署服务。
- 不要求所有 AI 工具具备完全相同的高级能力。
- 不把普通数据库 AuditEvent 描述成密码学意义的不可抵赖日志。

## 4. 架构原则

### 4.1 Locality by default

源码、未提交变更和本地绝对路径默认停留在本地执行平面。上传内容必须经过项目策略、客户端清理和必要的人审。

### 4.2 Harness as facade, domains as authority

Harness 编排用户工作生命周期，但项目身份、上下文版本、工作流状态、Skill 生命周期和审批规则分别由领域模块维护。Harness 不复制领域规则，也不直接操作搜索基础设施。

### 4.3 Immutable versions

Accepted ContextRevision、WorkflowVersion 和 SkillVersion 创建后不可变。逻辑对象通过 head 或 active version 指针引用当前版本。

### 4.4 Explicit provenance

AI 生成内容必须携带 schema version、生成工具、模型信息、来源锚点和输入基线。事实、推断和未验证结论要能够区分。

### 4.5 Idempotent commands

所有创建、完成、提交和关闭命令都接受 idempotency key。客户端重试返回原结果，不重复写入。

### 4.6 Database as source of truth

Postgres 保存治理状态和版本关系。对象存储和搜索索引通过 outbox 异步更新，可以从数据库和对象存储重建。

### 4.7 Progressive context

Harness 先返回 L0/L1 ContextBundle，再通过 source ref 获取 L2 内容。协议不能把全部团队记忆一次性塞给 AI 工具。

### 4.8 Graceful degradation

Agora 不可用时允许用户继续本地工作，但客户端必须标记上下文未验证并保存待同步队列，不能伪造已同步状态。

## 5. 运行时拓扑

```text
客户本地 / CI Runner
┌──────────────────────────────────────────────────────────┐
│ AI Tool                                                   │
│  ├─ 本地文件、文档、Git 和模型能力                        │
│  └─ Agora Local Connector / Agent Adapter                  │
│      ├─ Project Detector / Git Observer                    │
│      ├─ Policy Guard / Redaction                           │
│      ├─ Context Schema Helper / Source Anchor Builder      │
│      └─ Sync Queue / MCP Client                            │
└───────────────────────┬──────────────────────────────────┘
                        │ HTTPS / MCP over authenticated API
                        ▼
Agora 控制平面
┌──────────────────────────────────────────────────────────┐
│ API / MCP Gateway                                         │
│  └─ AuthN / AuthZ / Rate Limit / Protocol Validation       │
│                         │                                  │
│                         ▼                                  │
│ Harness Coordinator                                       │
│  ├─ Project Resolver / Work Resolver                       │
│  ├─ Context Planner / Workflow Orchestrator                │
│  ├─ Skill Orchestrator / Policy Engine                     │
│  └─ Session Recorder / Memory Writeback                    │
│                         │                                  │
│  ┌──────────────────────┴───────────────────────────────┐  │
│  │ Project │ Work │ Workflow │ Context │ Skill │ Quality │  │
│  │ Artifact │ Approval │ Audit │ Integration Signal      │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                  │
│  Postgres │ Object Store │ Outbox Workers │ Search Views   │
└──────────────────────────────────────────────────────────┘
                        ▲
                        │ Git webhook / CI RevisionSignal
                        │
                 Git / CI / Task Systems

Agora Web UI -> API Gateway -> Domain Query / Approval Commands
```

## 6. 本地执行平面

## 6.1 AI Tool

AI Tool 提供：

- 本地文件和 Git 访问。
- 用户已经配置的模型能力。
- 人工交互界面。
- 执行命令、修改代码和运行测试的能力。

Agora 不假设所有工具都能自动执行命令。接入时通过 capability 声明最小能力集。

## 6.2 Local Connector / Agent Adapter

Local Connector 是轻量适配层，可以表现为 MCP stdio server、AI 工具 Plugin、Project Rule Adapter 或内部 Agent SDK。

职责：

- 读取本地 repository、branch、commit 和 workspace 状态。
- 规范化 Git remote，移除用户名、密码和 token。
- 生成不暴露本地路径的 workspace fingerprint。
- 调用 Agora Harness。
- 将 Context schema、source anchor 要求和 workflow 指令交给 AI Tool。
- 在上传前执行 ignore、secret scan、大小限制和内容策略。
- 保存 idempotency key 和离线待同步队列。
- 将服务端错误转成 AI 工具可执行的下一步。

Local Connector 不负责：

- 决定团队 accepted context。
- 绕过 Agora 审批。
- 将任意本地目录路径上传服务端。
- 把未提交工作区自动发布成团队知识。

## 6.3 客户端能力协商

客户端在握手时声明：

```json
{
  "protocol_version": "1.0",
  "agent_type": "codex",
  "agent_version": "...",
  "capabilities": {
    "read_files": true,
    "read_git": true,
    "run_commands": true,
    "human_prompt": true,
    "offline_queue": true
  }
}
```

Harness 根据能力调整 next actions，不要求不具备命令执行能力的工具伪造测试结果。

## 7. API / MCP Gateway

Gateway 负责：

- 用户和 AI 工具认证。
- 从 principal 推导 org、user 和授权项目，拒绝客户端自报租户身份。
- scoped token 和 project scope 校验。
- schema、协议版本、payload 大小和内容类型校验。
- rate limit、request ID、trace ID 和幂等键透传。
- 将 AI 工具调用路由到 Harness。
- 将 Web UI 命令路由到对应领域模块。

MCP 是 AI 工具协议适配器，不是业务逻辑层。HTTP API 是唯一内部传输要求；MCP、Plugin 和 SDK 共享相同应用命令。

## 8. Harness Coordinator

## 8.1 定位

Harness 是 Agora 面向 AI 工具的稳定任务级控制层。

它回答：

- 当前用户在哪个项目和哪个 WorkItem 工作？
- 本次 WorkSession 应固定哪些 Context、Workflow 和 Skill 版本？
- 当前步骤是什么，需要哪些上下文和人工确认？
- AI 工具应该执行哪个 next action？
- 工作结束后哪些内容应成为 ContextProposal、SkillCandidate 或 QualityEvidence？

## 8.2 内部组件

- `ProjectResolver`：用规范化 RepositoryIdentity 解析 Project。
- `WorkResolver`：匹配外部任务、已有 WorkItem 或创建候选 WorkItem。
- `ContextPlanner`：按任务、角色、阶段和 token budget 生成 ContextBundle。
- `WorkflowOrchestrator`：推进 WorkflowExecution 和步骤状态。
- `SkillOrchestrator`：选择已批准 SkillVersion 并记录 SkillRun。
- `PolicyEngine`：计算上传、人工确认、审批和风险策略。
- `SessionRecorder`：记录 WorkSession、调用和状态事件。
- `MemoryWriteback`：把任务收尾材料组织为 ContextProposal 或 SkillCandidate。
- `StatusQuery`：为 AI 工具聚合项目、WorkItem 和质量状态。

## 8.3 职责上限

Harness 只调用领域 command/query interface：

- 不直接更新 ContextStream head。
- 不直接发布 SkillVersion。
- 不直接修改 WorkflowVersion。
- 不直接访问客户源码。
- 不依赖具体向量数据库协议。
- 不将 AI 摘要直接标记为已验证质量事实。

## 8.4 生命周期

```text
start_work
-> resolve project and WorkItem
-> create/resume WorkSession
-> pin context/workflow/skill versions
-> prepare_context
-> execute and complete workflow steps
-> record artifacts/evidence/human confirmations
-> submit context/skill proposals
-> close_work
```

## 9. 领域模块

## 9.1 Identity and Access

管理 Organization、User、Membership、ProjectMembership、credential 和 role policy。

首期角色：

- admin。
- project_manager。
- tech_lead / context_steward。
- developer。
- quality。
- product。
- viewer。

权限最终由 principal、organization membership、project membership 和 ApprovalPolicy 共同决定。

P2 先实现最小可信边界：本地/私有部署用户、ProjectMembership、个人 AI-tool credential 与 human Web credential 分离，agent credential 可以工作和提交候选但不能审批。P7 再增加 SSO、生命周期、细粒度策略、轮换和企业审计硬化。

## 9.2 Project and Repository

管理 Project、RepositoryIdentity、默认分支、上传策略、集成和上下文通道。

RepositoryIdentity 使用 provider、host、namespace、repository 组成稳定身份。SSH、HTTPS 和带用户名 remote 规范化为同一 canonical identity。

## 9.3 Work Management

管理 WorkItem 和 WorkSession。

WorkItem 是项目状态聚合单位；WorkSession 是一次 AI 工具执行。多个用户和多个 Session 可以关联同一个 WorkItem。

WorkItem 可以关联外部任务 ID、branch、commit、PR、负责人、参与者和风险等级。

一个 WorkItem 只有一个 authoritative WorkflowExecution。WorkItem 的 stage/status 由该 execution、阻塞和审批状态事务性派生。WorkSession 只能贡献 step attempt、artifact、evidence 和 confirmation，不能独立覆盖 WorkItem stage。

## 9.4 Workflow

管理 WorkflowDefinition、WorkflowVersion、WorkflowExecution 和 WorkflowStepRun。

规则：

- WorkflowVersion 不可变。
- WorkItem 开始执行时固定一个 WorkflowVersion。
- 一个 WorkItem-level WorkflowExecution 是流程进度唯一事实源。
- WorkSession 的 step attempt 必须关联该 execution；并发 Session 通过 execution version 做乐观并发。
- Step 完成是带前置条件的命令，不是任意状态 PATCH。
- 默认标准 WorkflowVersion 的每个步骤都包含 AI 工具内的人工确认；轻量版本必须由有权限的角色发布。
- skip、waive、reopen 和 retry 必须记录原因、操作者和策略结果。
- 人工确认作为独立记录，不仅保存布尔值。

## 9.5 Context Governance

管理 ContextStream、ContextRevision、ContextProposal、ContextBundle 和 SourceAnchor。

职责：

- 维护 branch-scoped accepted head。
- 计算 freshness 状态。
- 接收并校验 AI 生成 Proposal。
- 生成差异和审批材料。
- 使用 expected head 乐观合并。
- 提供 task-aware ContextBundle。
- 管理版本血缘、回滚和 deprecated revision。

## 9.6 Skill Governance

管理 Skill、SkillVersion、SkillCandidate 和 SkillRun。

Skill 是逻辑身份，SkillVersion 是不可变内容。WorkSession 记录实际使用的版本，避免 Skill 修改后无法解释历史行为。

## 9.7 Artifact and Quality

管理 WorkArtifact、ArtifactBlob 和 QualityEvidence。

质量证据至少记录：

- 类型和来源。
- 关联 commit/PR。
- 命令或 CI run reference。
- 结果、时间和生成者。
- 原始证据位置和 hash。
- 是否经过人工确认。

Quality Service 聚合证据和风险，不把 AI 推断转成测试已通过。

## 9.8 Approval

管理 ApprovalPolicy、ApprovalRequest 和 ApprovalDecision。

支持：

- 单人或多人审批。
- 指定角色或 code owner。
- approve、reject、request changes。
- 低风险自动接受策略。
- ContextProposal、SkillCandidate、WorkflowVersion 和高风险产物审批。

## 9.9 Audit

记录关键命令、审批和状态变化：

- actor principal 和 actor tool。
- organization、project、WorkItem 和 WorkSession。
- request ID、trace ID、idempotency key。
- event type、target、before/after reference。
- payload hash 和 timestamp。

默认实现为 append-only application audit。企业防篡改要求可以增加 hash chain 或外部 WORM sink。

## 9.10 Integration Signal

接收 Git webhook、CI、任务系统和 PR 事件，规范化为：

- RevisionSignal。
- TaskSignal。
- PullRequestSignal。
- QualitySignal。

Signal 只更新 Agora 可证明的状态，不在无源码情况下生成 ContextRevision。

## 10. 核心数据模型

以下为逻辑模型，具体表字段在阶段实施计划中细化。

## 10.1 租户和项目

```text
Organization
User
Membership
Project
ProjectMembership
RepositoryIdentity
ProjectPolicy
```

约束：

- Project slug 在 organization 内唯一。
- RepositoryIdentity canonical key 在授权范围内唯一。
- 所有领域查询必须包含 tenant boundary。
- org_id 从认证 principal 推导，不接受客户端任意指定。

## 10.2 工作管理

```text
WorkItem
  id, project_id, external_ref, title, description
  status, derived_stage, risk_level, owner_id
  workflow_version_id, branch, created_at, updated_at

WorkSession
  id, work_item_id, user_id, agent_type, agent_version
  pinned_context_revision_id, pinned_workflow_version_id
  status, active_step_run_id, started_at, closed_at

SessionEvent
HumanConfirmation
```

## 10.3 工作流

```text
WorkflowDefinition
WorkflowVersion
  id, definition_id, version, schema_version, steps, status

WorkflowExecution
  id, work_item_id, workflow_version_id, status

WorkflowStepRun
  id, execution_id, step_key, attempt, status
  started_at, completed_at, waiver_id
```

## 10.4 上下文

```text
ContextStream
  id, project_id, repository_id, branch, head_revision_id

ContextRevision
  id, stream_id, version, parent_revision_id
  base_commit_sha, schema_version, content_ref
  provenance, status, accepted_at

ContextProposal
  id, stream_id, work_item_id, session_id
  type, target_branch, expected_head_revision_id
  source_branch, from_commit_sha, to_commit_sha
  content_ref, source_anchors, provenance
  status, created_at

ContextBundle
  id, session_id, revision_id, query, intent
  token_budget, level, content, source_refs, created_at

SourceAnchor
  repository_id, commit_sha, path
  start_line, end_line, content_hash
  optional_excerpt_ref
```

ContextProposal 状态：

```text
draft -> pending_review -> accepted
                      ├-> request_changes
                      ├-> rejected
                      └-> needs_rebase
```

## 10.5 Skill

```text
Skill
SkillVersion
SkillCandidate
SkillRun
```

SkillVersion 包含 schema version、trigger、instructions、input/output schema、来源和审批信息。

## 10.6 产物、质量和治理

```text
WorkArtifact
ArtifactBlob
QualityEvidence
ApprovalPolicy
ApprovalRequest
ApprovalDecision
AuditEvent
OutboxEvent
IdempotencyRecord
RevisionObservation
```

## 11. Freshness 架构

## 11.1 输入信号

Local Connector 上报 `RevisionObservation`：

```json
{
  "repository_key": "gitlab.example.com/team/member-center",
  "branch": "main",
  "commit_sha": "9a01d44",
  "workspace_state": "clean",
  "relationship_to_context_base": "descendant",
  "changed_paths_digest": "...",
  "observed_at": "..."
}
```

Git/CI 上报 `RevisionSignal`：

```json
{
  "repository_key": "gitlab.example.com/team/member-center",
  "branch": "main",
  "new_head_sha": "9a01d44",
  "previous_head_sha": "8f34c2a",
  "event": "push"
}
```

## 11.2 多维结果

Freshness 不使用单个互斥字符串，返回：

```json
{
  "repository_relation": "descendant",
  "workspace_state": "clean",
  "context_coverage": "stale",
  "proposal_state": "none",
  "accepted_revision_id": "ctx_r12",
  "observed_commit_sha": "9a01d44",
  "recommended_action": "generate_refresh_proposal"
}
```

维度：

- `repository_relation`：exact、descendant、ancestor、diverged、unknown。
- `workspace_state`：clean、dirty、unknown。
- `context_coverage`：missing、fresh、potentially_stale、stale、unknown。
- `proposal_state`：none、pending、needs_rebase、conflict。

## 11.3 判断规则

- 没有 accepted head：context missing。
- observation commit 等于 accepted base commit：fresh。
- Git/CI 宣布新 branch head，但尚无本地 diff 证据：potentially_stale。
- 本地工具证明 observation commit 是 accepted base 的 descendant：stale。
- 本地 commit 是 accepted base 的 ancestor：本地代码 behind，Context 可能 ahead。
- repository diverged：要求用户或工具处理 branch，不能自动覆盖。
- dirty workspace 是独立维度，只限制团队知识提交，不阻止 session-local 分析。
- 同一 expected head 存在重叠 Proposal 时标记潜在冲突，但只有合并时做最终 CAS 判断。

## 11.4 自动更新边界

Agora 可以自动检测过期、触发生成请求、管理审批和分发新版本；只有具备代码访问能力的 Local Connector 或 CI Agent 才能生成真实 ContextProposal。

低风险、策略允许且有可信 CI Agent 的 refresh Proposal 可以自动接受。默认仍进入审批。

## 12. Context 架构

## 12.1 ContextRevision schema

ContextRevision 内容采用版本化 JSON schema，至少包含：

- project overview。
- domains and modules。
- business and technical flows。
- constraints and decisions。
- risks。
- test strategy。
- source anchors。
- provenance。

Provenance 至少包含：

- generating tool 和 version。
- model/provider 标识或组织允许的匿名标识。
- schema version。
- input ContextRevision。
- repository commit。
- generation timestamp。
- project workflow/skill versions。

## 12.2 ContextBundle 规划

输入：

```text
principal role
project and WorkItem
session intent and workflow step
pinned ContextRevision
approved SkillVersions
query and token budget
```

输出：

```text
L0 brief
L1 selected facts, constraints, risks and skills
L2 source refs for optional expansion
quality and workflow requirements
```

ContextPlanner 必须：

- 对完整序列化 L0/L1 payload 遵守 token budget。预算包含 envelope、facts、constraints、risks、workflow requirements、Skill 摘要和 source-ref metadata；不包含传输协议 header 和尚未获取的 L2 内容。
- 优先 accepted ContextRevision 和 approved SkillVersion。
- 标记 session-local、pending 和 unverified 内容。
- 为关键事实保留 source ref。
- 记录本次 Bundle 使用了哪些版本和检索信号。

预算计算使用带版本号的 tokenizer/estimator，并返回 `budget_limit`、`estimated_tokens` 和 `estimator_version`。超出预算时按确定性顺序裁剪：先移除低相关历史和可选 Skill，再减少低相关事实及 source-ref metadata；项目安全约束、当前 workflow gate 和 L0 identity 不得被裁掉。source refs 有数量和 metadata 大小上限。

每次 L2 `fetch_context_ref` 使用独立 `max_tokens`，不借用或扩大 L0/L1 预算。测试对最终序列化 payload 计数，而不是只检查 summary 字符数。

## 12.3 ContextProposal 合并

审批接受时执行单事务命令：

1. 锁定 ContextStream。
2. 校验 Proposal 的 repository 和 `target_branch` 与目标 ContextStream 一致。
3. 使用受信任 RevisionObservation、CI 或 provider signal 证明 `to_commit_sha` 可达目标 branch head。
4. feature branch 未合并时只能更新对应 branch stream 或保持 session-local，不能直接更新默认 branch stream。
5. 比较 `expected_head_revision_id` 与当前 head。
6. 不相等则 Proposal -> needs_rebase。
7. 相等则创建新的 immutable ContextRevision。
8. 更新 ContextStream head。
9. 保存 ApprovalDecision 和 AuditEvent。
10. 写入 OutboxEvent。

禁止原地修改 accepted ContextRevision。

## 13. Workflow 架构

WorkflowVersion 的 step schema：

```json
{
  "key": "self_test",
  "name": "自测",
  "required_artifact_types": ["self_test_report"],
  "required_evidence_types": ["test_run"],
  "human_gate": {
    "required": true,
    "roles": ["developer"]
  },
  "completion_rules": ["artifacts_present", "evidence_passed"],
  "skip_policy": "tech_lead_approval"
}
```

状态转换由命令完成：

```text
not_started -> in_progress -> awaiting_human -> completed
                         ├-> failed
                         ├-> blocked
                         └-> waived
```

Harness 返回 next actions，AI 工具负责执行本地工作。服务端只校验已声明产物、证据、确认和权限，不声称验证无法访问的本地事实。

## 14. AI 工具协议

## 14.1 协议原则

- MCP tools 主要映射到 Harness。
- 普通 AI 工作流使用少量高层工具。
- 调试和 Web 治理 API 不进入默认 MCP tool list。
- 所有写命令接受 `idempotency_key`。
- 所有响应包含 `protocol_version`、`request_id` 和可执行 `next_actions`。
- 错误使用稳定 code，不依赖自然语言解析。

## 14.2 默认 MCP tools

```text
agora_start_work
agora_prepare_context
agora_fetch_context_ref
agora_complete_workflow_step
agora_record_evidence
agora_submit_context_proposal
agora_submit_skill_candidate
agora_close_work
agora_get_project_status
agora_get_quality_status
```

项目解析和 freshness check 是 `agora_start_work` / `agora_prepare_context` 的内部步骤，不要求开发者或 AI 工具手工串联多个底层调用。

P2 当前广告的 MCP 子集只包含：

```text
agora_start_work
agora_prepare_context
agora_fetch_context_ref
agora_close_work
```

兼容映射：

| Legacy tool / endpoint | P2 canonical target | Error mapping | Deprecation marker | Removal target |
| --- | --- | --- | --- | --- |
| `agora_plan_context` / `/harness/plan-context` | `agora_prepare_context` / `/harness/prepare-context` | `TOKEN_BUDGET_TOO_SMALL` | `deprecation.legacy_tool`, `deprecation.legacy_endpoint` | after P2 |
| `agora_record_event` | not advertised; use workflow/evidence tools in P4 | stable Harness `error.code` when rejected | `deprecation.legacy_tool` | after P2 |
| `agora_prepare_writeback` | not advertised; proposal submission in P3/P5 | stable Harness `error.code` when rejected | `deprecation.legacy_tool` | after P2 |
| `agora_search_knowledge` | `agora_prepare_context` | `TOKEN_BUDGET_TOO_SMALL` | `deprecation.legacy_tool` | after P2 |

## 14.3 start_work

输入不包含服务端可用的本地绝对路径：

```json
{
  "protocol_version": "1.0",
  "user_message": "修复 BUG-128：优惠券支付后状态未刷新",
  "repository": {
    "canonical_key": "gitlab.example.com/team/member-center",
    "branch": "main",
    "commit_sha": "8f34c2a",
    "workspace_state": "clean",
    "workspace_fingerprint": "ws_..."
  },
  "agent": {
    "type": "codex",
    "version": "..."
  },
  "idempotency_key": "..."
}
```

输出：

```json
{
  "project_id": "project_1",
  "work_item_id": "work_128",
  "session_id": "session_1",
  "pinned": {
    "context_revision_id": null,
    "workflow_version_id": null,
    "skill_version_ids": []
  },
  "capabilities": {
    "context_revision": false,
    "workflow_version": false,
    "skill_version": false
  },
  "context_state": {},
  "current_step": "analysis",
  "next_actions": ["prepare_context"]
}
```

版本 ID 在分阶段迁移期间允许为空，并通过 capability 明确声明。P2 只能把旧上下文作为 provisional ContextBundle 材料返回；ContextRevision、WorkflowVersion 和 SkillVersion 分别在 P3、P4 和 P5 落地后才能成为正式 pin。

## 14.4 prepare_context

输入 query、intent、workflow step 和 token budget，返回受控 ContextBundle。ContextBundle 不自动成为团队 ContextRevision。

## 14.5 complete_workflow_step

提交 artifact refs、evidence refs、human confirmation 和 attempt。服务端校验 WorkflowVersion 规则后原子推进状态。

## 14.6 close_work

关闭 WorkSession 前返回缺失步骤和建议提交内容。成功关闭不等于自动接受 ContextProposal 或 SkillCandidate。

## 14.7 错误模型

核心错误 code：

- `PROJECT_UNRESOLVED`。
- `WORK_ITEM_CLARIFICATION_REQUIRED`。
- `CONTEXT_MISSING`。
- `CONTEXT_NEEDS_REBASE`。
- `WORKFLOW_PRECONDITION_FAILED`。
- `HUMAN_CONFIRMATION_REQUIRED`。
- `UPLOAD_POLICY_DENIED`。
- `UNAUTHORIZED_PROJECT`。
- `PROTOCOL_VERSION_UNSUPPORTED`。
- `TEMPORARILY_UNAVAILABLE`。

## 15. 一致性和并发

### 15.1 事务边界

以下操作必须单事务：

- WorkSession 创建和 pinned versions 记录。
- workflow step 状态推进和 confirmation 关联。
- Proposal 接受、新 revision 创建和 ContextStream head 更新。
- SkillCandidate 接受和 SkillVersion 发布。
- 领域状态变化和 OutboxEvent 写入。

Application command handler 通过 Unit of Work 拥有事务。Repository 方法只 add/flush entity，不独立 commit；这是当前 repository 模式必须完成的迁移。

### 15.2 幂等

`IdempotencyRecord` 使用 principal、command type 和 idempotency key 唯一约束，保存请求 hash、响应和有效期。

相同 key 不同 payload 返回冲突，避免误复用。

### 15.3 乐观并发

- ContextProposal 使用 expected head revision。
- Workflow command 使用 execution version。
- Web 编辑使用 resource version / ETag。
- mutable 聚合保存 revision number。

### 15.4 Outbox

领域事务只写 Postgres 和 OutboxEvent。Worker 负责：

- 更新搜索和向量投影。
- 刷新质量摘要。
- 发送 stale 和审批通知。
- 同步外部任务状态。

Worker 使用 event id 幂等消费，失败可重试和死信审计。

## 16. 存储架构

## 16.1 Postgres

事实源数据：

- identity、membership、project 和 policy。
- WorkItem、WorkSession 和 workflow execution。
- Context metadata、head、proposal 和 provenance。
- Skill metadata 和 versions。
- artifact metadata、QualityEvidence 和 approvals。
- AuditEvent、OutboxEvent 和 IdempotencyRecord。

本地开发可以使用 SQLite，但团队黑盒和生产路径必须验证 Postgres 语义，尤其是事务、锁和并发。

## 16.2 Object Store

保存：

- 大型 ContextRevision 内容。
- WorkArtifact 和附件。
- 可选源码 excerpt。
- 质量报告和导出文件。

对象使用 content hash 寻址或去重，metadata 保存在 Postgres。生产使用 S3 兼容存储和服务端加密。

## 16.3 Search Projection

P2-P6 首选 Postgres JSONB、全文检索和可选 pgvector，降低部署复杂度。

当数据规模和检索评估证明需要时，再启用 OpenSearch/Qdrant adapter。Neo4j 继续延后，除非真实场景证明图查询有不可替代价值。

搜索索引不是事实源，必须支持全量和增量重建。

## 17. 安全和隐私

## 17.1 认证

- Web 用户使用组织认证或本地账号。
- AI 工具使用用户授权的 scoped token；后续支持 OAuth device flow。
- CI 使用独立 service account。
- webhook 使用签名验证和 replay protection。

## 17.2 授权

- org 和 user 从 principal 推导。
- 每个请求校验 ProjectMembership。
- token scope 限制 read context、write session、submit proposal 或 administer。
- 审批要求真实用户身份，不允许普通 agent token 代替审批人。

## 17.3 本地数据保护

- 不上传本地绝对路径。
- remote 去除 credential 和用户名。
- 支持 `.agoraignore`、组织 ignore policy 和敏感路径规则。
- 上传前执行 secret scan、文件大小和内容类型检查。
- source anchor 可以只存 commit、path、line 和 hash，不保存源码 excerpt。

## 17.4 服务端保护

- 传输加密和静态加密。
- 对象存储使用短期签名 URL。
- 审计高风险读取、上传、审批和导出。
- 支持数据保留、删除和导出策略。
- 日志禁止记录 token、原始 secret 和完整敏感 payload。

## 18. 后台任务

首期使用数据库 outbox + worker，不强制 Temporal。

任务包括：

- SearchProjection 更新和重建。
- ContextProposal 差异材料生成。
- QualitySummary 聚合。
- RevisionSignal freshness 标记。
- stale / approval 通知。
- SkillCandidate 聚类和重复检测。
- 审计归档和对象清理。

只有当长流程、跨系统补偿和运行规模证明需要时，再引入 Temporal 或其他 durable workflow engine。

## 19. 部署架构

## 19.1 本地开发

```text
Local Connector / MCP stdio
FastAPI modular monolith
Next.js Web UI
SQLite or local Postgres
Local artifact directory
In-memory/fake search for automated tests only
```

## 19.2 团队试用

```text
Local Connector on each developer machine
API + Harness modular monolith
Web UI
Worker
Postgres
S3-compatible object storage
Optional Postgres FTS / pgvector
Git/CI webhook receiver
```

## 19.3 企业部署

```text
API/Web replicas behind ingress
Postgres HA
Object storage
Worker pool
SSO / scoped AI credentials
Audit sink
Private network / data residency policy
Optional OpenSearch / Qdrant projections
```

## 20. 失败和恢复

### 20.1 Agora 不可用

Local Connector 保存带 idempotency key 的本地待同步队列。AI 工具可以继续工作，但 UI 明确显示：

- team context unverified。
- artifacts pending sync。
- approvals unavailable。

### 20.2 Context merge conflict

不自动覆盖 head。Proposal 进入 needs_rebase，AI 工具获取新 head 和冲突摘要后在本地重新生成候选。

### 20.3 Workflow command retry

重复命令返回原结果；前置条件变化返回稳定 conflict code 和当前状态。

### 20.4 Object upload interrupted

使用预签名分片上传或内容 hash 重试。metadata 只在对象完成后进入可用状态。

### 20.5 Search unavailable

Harness 回退到 pinned ContextRevision、结构化数据库查询和明确的 degraded 标记，不返回空结果冒充无上下文。

## 21. 可观测性

技术指标：

- Harness command latency、error rate 和 retry rate。
- Project / WorkItem resolve success rate。
- ContextBundle token size 和 source expansion rate。
- freshness 状态分布和 stale duration。
- Proposal review time、needs_rebase rate 和 conflict rate。
- workflow completion / waiver / failure rate。
- offline queue sync lag。
- outbox lag 和 search projection freshness。

产品指标：

- AI 工具自动使用 Agora 的 WorkSession 比例。
- 开发者无需打开 Web UI 的正常任务比例。
- ContextRevision 和 SkillVersion 复用率。
- WorkItem 状态完整度和 QualityEvidence 完整度。

## 22. 与现有代码的关系

## 22.1 保留并升级

- `packages/harness/`：保留 HarnessService 及 ProjectResolver、TaskResolver、ContextPlanner、SessionRecorder、MemoryWriteback 雏形。
- `apps/mcp/`：保留 stdio MCP adapter，升级为 Local Connector 协议入口。
- FastAPI、SQLAlchemy repository、Alembic 和 SQLite/Postgres 配置方向。
- TaskSession、SessionEvent、ContextPack、Skill、SkillRun 和 Writeback 的已有实现经验。
- Next.js Web UI 的项目、Session、Skill 和 Writeback 页面骨架。
- 当前自动化测试和 fake adapter 作为测试替身。

## 22.2 需要重构

- `TaskSession` 拆分/迁移为 WorkItem + WorkSession。
- 当前无版本 ContextPack 迁移到 ContextStream + ContextRevision + ContextProposal。
- Writeback 中有价值的类型迁移到 ContextProposal、SkillCandidate、WorkArtifact 或 QualityEvidence。
- mutable Skill 迁移到 Skill + SkillVersion。
- 现有 `plan_context` 保留 token budget 和 source refs，升级为 `prepare_context`。
- `start_work` 增加 LocalWorkspaceObservation、WorkItem 解析、pinned versions 和幂等。
- 当前 server-side project initialization 降级为显式授权导入和测试辅助路径。
- fake keyword/vector index 不作为黑盒产品路径。
- 当前 repository 内部 `commit()` 迁移到 command-level Unit of Work，保证领域状态和 OutboxEvent 原子写入。

## 22.3 不应继续扩大

- 不继续围绕服务端本地路径扫描扩展客户主流程。
- 不先实现更多 Web 辅助查询来代替 AI 工具黑盒链路。
- 不在没有数据规模证据时优先建设 OpenSearch、Qdrant、Neo4j 和 Temporal。
- 不让 Harness 直接承担所有领域持久化和审批规则。

## 23. 分阶段架构落地

- P2：真实 AI 工具接入、最小 human/agent 身份边界、Unit of Work、WorkItem/WorkSession、结构化 freshness 和 task-aware ContextBundle；版本 pin capability 可为空。
- P3：ContextStream/Revision/Proposal、分支和并发治理、RevisionSignal contract、最小可靠 outbox；真实 provider Push adapter 延后到 P8。
- P4：WorkflowVersion、步骤状态、WorkArtifact、HumanConfirmation 和任务收尾。
- P5：SkillVersion、SkillCandidate、SkillRun 和团队经验复用。
- P6：QualityEvidence、项目经理状态和质量查询。
- P7：SSO、身份生命周期、RBAC/scoped token 硬化、可配置审批策略和完整审计。
- P8：真实签名 Git/CI signal、任务系统、PR 和自动化集成。
- P9：生产部署、备份恢复、可观测性和按需真实搜索投影。

具体交付、测试和历史记录以 Roadmap 为准。

## 24. 黑盒架构验收

真实黑盒测试必须验证：

1. AI 工具通过 Local Connector 采集并清理本地 Git 信息。
2. `agora_start_work` 自动解析 Project、WorkItem 并创建 WorkSession。
3. Harness 返回 pinned versions、结构化 freshness 和 next actions。
4. `agora_prepare_context` 在 token budget 内返回可追溯 ContextBundle。
5. missing/stale 时由真实 AI 工具读取本地项目并提交 ContextProposal。
6. Web UI 审批使用 expected head 创建新 ContextRevision。
7. 第二个 AI 工具复用 accepted revision，不重复全量分析。
8. Workflow step、产物、人工确认和 QualityEvidence 可审计。
9. close_work 提交 task update 和 SkillCandidate，但不会自动发布。
10. Git/CI RevisionSignal 使 ContextStream 自动进入 potentially_stale。
11. 并发 Proposal 不会静默覆盖 accepted head。
12. 项目经理从 WorkItem 获取状态，质量人员从证据获取质量结论。
13. 网络重试不会产生重复 Session、Artifact 或 Proposal。

自动单元测试中的 fake model、fake index 和 fixture 可以保留，但不能代替以上黑盒链路。

## 25. 已确定的架构决策

| 决策 | 结果 |
| --- | --- |
| 主入口 | AI 工具，Web 用于治理 |
| 核心层 | Harness Coordinator |
| 源码位置 | 客户本地或 CI runner |
| 服务形态 | 模块化单体优先 |
| 项目任务模型 | WorkItem 与 WorkSession 分离 |
| 上下文模型 | ContextStream + immutable Revision + Proposal |
| Freshness | 多维状态，Pull + Push 信号 |
| 上下文返回 | task-aware ContextBundle + token budget |
| 版本并发 | expected head + 乐观锁 |
| 可靠投影 | Postgres transaction + outbox |
| 搜索 | Postgres-first，外部索引按需 |
| AI 分析 | 客户已有 AI 工具为主 |
| 人工控制 | Proposal/Skill/高风险步骤按策略审批 |
| 黑盒验收 | 真实 AI 工具 + 真实本地项目 + 真实服务 |
