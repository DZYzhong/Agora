# Agora 技术架构设计

## 1. 架构目标

Agora 的技术架构要服务真实团队工作流：

- 开发者通过 AI 工具工作，而不是直接操作 Agora。
- 客户代码和文档默认留在开发者本地或 CI runner，不由 Agora 主动拉取。
- AI 工具负责本地扫描、项目分析、上下文生成、任务执行辅助。
- Agora 负责项目身份、上下文版本、流程模板、技能包、任务过程、团队资产、审批治理和审计。
- Agora Web UI 面向项目经理、技术负责人、质量人员和管理员。

## 2. 总体架构

```text
开发者本地项目
  ├─ 源码 / 文档 / Git
  └─ AI 工具插件 / MCP Client
        │
        │ resolve project / fetch memory / upload artifacts
        ▼
Agora API / MCP Gateway
        │
        ├─ Project Service
        ├─ Context Service
        ├─ Workflow Service
        ├─ Skill Service
        ├─ Task Session Service
        ├─ Quality Service
        ├─ Approval Service
        └─ Audit Service
        │
        ├─ Relational DB
        ├─ Object/Artifact Store
        ├─ Search / Vector Index
        └─ Event Log
        │
        ▼
Agora Web UI
  ├─ 项目驾驶舱
  ├─ 上下文治理
  ├─ 任务流程审计
  ├─ Skill 审批
  ├─ 质量视图
  └─ 团队和权限
```

## 3. 组件边界

## 3.1 AI 工具侧组件

AI 工具侧是日常工作主入口。

组件：

- Local Project Detector。
- Agora Connector。
- Context Generator。
- Workflow Runner。
- Artifact Syncer。
- Skill Candidate Generator。
- User Review Prompt。

职责：

- 读取本地 Git 状态。
- 检测项目路径和仓库身份。
- 调用 Agora 解析项目。
- 判断上下文是否 fresh。
- 在 missing/stale 时扫描本地代码和文档。
- 调用 AI 模型生成 ContextPack 或 ContextUpdate。
- 按 WorkflowTemplate 引导任务。
- 保存文档到项目本地。
- 上传任务产物到 Agora。
- 让开发者在 AI 工具中确认关键节点。

不应该做：

- 绕过 Agora 审批直接覆盖 accepted ContextPack。
- 在 dirty workspace 情况下自动更新团队全局上下文。
- 上传未经用户确认的敏感内容。

## 3.2 Agora API / MCP Gateway

AI 工具通过 API 或 MCP 调用 Agora。

职责：

- 提供项目解析。
- 提供上下文 freshness check。
- 提供团队记忆读取。
- 接收上下文、任务产物、候选 skill 上传。
- 提供任务 session 记录。
- 提供项目和质量状态查询。

接口形式：

- HTTP API：适合 Web UI、CI、后台集成。
- MCP Tools：适合 AI 工具直接调用。

## 3.3 Agora Web UI

Web UI 是治理和审计入口。

职责：

- 展示项目上下文版本。
- 审核 ContextUpdate。
- 审核 skill candidate。
- 管理项目流程模板。
- 查看任务流程产物。
- 查看项目质量状态。
- 管理团队、权限和审计。

不作为：

- 开发者日常主入口。
- 项目源码扫描入口。
- 真实 AI 上下文生成入口。

## 4. 核心服务设计

## 4.1 Project Service

负责项目身份和项目配置。

能力：

- 创建项目。
- 解析本地项目身份。
- 管理 repo remote / fingerprint。
- 管理项目成员和角色。
- 管理默认 WorkflowTemplate。
- 管理当前 accepted ContextPack。

关键 API：

```text
POST /projects/resolve-local
GET /projects/{project_id}
PATCH /projects/{project_id}
GET /projects/{project_id}/status
```

`resolve-local` 输入：

```json
{
  "org_id": "org_1",
  "local_path_hint": "/workspace/member-center",
  "git_remote": "git@example.com:team/member-center.git",
  "branch": "main",
  "commit_sha": "8f34c2a",
  "dirty_workspace": false,
  "detected_project_name": "member-center"
}
```

输出：

```json
{
  "project_id": "project_1",
  "project_name": "会员中心研发协作平台",
  "context_status": "fresh",
  "current_context_version": "ctx_v12",
  "workflow_template_id": "workflow_default",
  "available_skill_ids": ["skill_payment_callback_checklist"]
}
```

## 4.2 Context Service

负责 ContextPack、ContextUpdate、版本、freshness 和合并。

能力：

- 检查上下文 freshness。
- 获取 accepted ContextPack。
- 上传新 ContextPack。
- 上传 ContextUpdate。
- 评审和合并 ContextUpdate。
- 管理版本血缘。
- 管理 source_refs。

关键 API：

```text
POST /projects/{project_id}/context/freshness-check
GET /projects/{project_id}/context/current
GET /projects/{project_id}/context/versions
POST /projects/{project_id}/context/packs
POST /projects/{project_id}/context/updates
POST /projects/{project_id}/context/updates/{update_id}/accept
POST /projects/{project_id}/context/updates/{update_id}/reject
```

freshness 状态：

- `fresh`：当前 accepted ContextPack 覆盖本地 commit。
- `missing`：项目没有 accepted ContextPack。
- `stale`：本地 commit 晚于 accepted ContextPack。
- `ahead`：accepted ContextPack 对应 commit 晚于本地 commit。
- `dirty_workspace`：本地有未提交变更。
- `conflict`：存在多个候选更新或分支上下文冲突。

## 4.3 Workflow Service

负责项目流程模板和任务流程执行状态。

能力：

- 定义 WorkflowTemplate。
- 定义步骤。
- 定义必填产物。
- 定义人工确认节点。
- 记录每个 TaskSession 的步骤状态。

关键 API：

```text
GET /projects/{project_id}/workflows/current
POST /projects/{project_id}/workflows
PATCH /workflows/{workflow_id}
POST /sessions/{session_id}/workflow-steps/{step_id}/complete
```

步骤模型：

```json
{
  "id": "analysis",
  "name": "分析",
  "required_artifacts": ["analysis_doc"],
  "requires_human_review": true,
  "completion_rules": ["artifact_uploaded", "human_confirmed"]
}
```

## 4.4 Task Session Service

负责一次任务从开始到结束的全过程。

能力：

- 创建任务 session。
- 识别或补充任务名称。
- 记录 AI 工具调用。
- 记录使用的 ContextPack 和 skill。
- 记录 workflow step 产物。
- 记录人工确认。
- 关联 ContextUpdate 和 skill candidate。

关键 API：

```text
POST /sessions/start
GET /projects/{project_id}/sessions
GET /projects/{project_id}/sessions/{session_id}
POST /sessions/{session_id}/events
POST /sessions/{session_id}/artifacts
POST /sessions/{session_id}/close
```

## 4.5 Artifact Service

负责任务文档和团队资产。

能力：

- 保存分析、设计、评审、开发、自测、上传文档。
- 保存本地文件路径引用。
- 保存上传内容。
- 关联任务、项目、ContextUpdate。
- 支持审计和查询。

存储策略：

- 小型 markdown/json 内容可存数据库。
- 大文件或附件进入对象存储。
- 保存 hash、source path、generated_by、review status。

## 4.6 Skill Service

负责 skill 生命周期。

能力：

- 创建 candidate skill。
- 审批为 approved。
- 编辑和版本化。
- 废弃。
- 按项目、组织、任务意图检索。
- 记录 skill run。

关键 API：

```text
GET /projects/{project_id}/skills
POST /projects/{project_id}/skills/candidates
POST /skills/{skill_id}/approve
POST /skills/{skill_id}/deprecate
POST /skills/{skill_id}/runs
```

## 4.7 Quality Service

负责质量状态聚合。

数据来源：

- 任务自测报告。
- 评审产物。
- ContextUpdate 风险。
- Skill 检查结果。
- CI 测试结果。
- 质量人员上传的结论。

能力：

- 项目质量摘要。
- 任务质量摘要。
- 风险清单。
- 测试覆盖建议。
- 质量趋势。

关键 API：

```text
GET /projects/{project_id}/quality
GET /projects/{project_id}/sessions/{session_id}/quality
POST /projects/{project_id}/quality/reports
```

## 4.8 Approval Service

负责上下文、skill、流程模板等治理审批。

审批对象：

- ContextPack。
- ContextUpdate。
- Skill。
- WorkflowTemplate。
- 高风险任务产物。

能力：

- 创建审批请求。
- 分配 reviewer。
- approve / reject / request changes。
- 记录审批意见。
- 生成审计事件。

## 4.9 Audit Service

负责所有关键行为的审计。

审计事件：

- AI 工具解析项目。
- freshness check。
- ContextPack 上传。
- ContextUpdate 审批。
- Skill 审批。
- Workflow step 完成。
- 人工确认。
- 质量报告生成。

## 5. 数据模型

## 5.1 Organization

```text
id
name
created_at
```

## 5.2 User

```text
id
display_name
email
status
created_at
```

## 5.3 Membership

```text
id
org_id
user_id
role
```

角色：

- admin。
- project_manager。
- tech_lead。
- developer。
- quality。
- viewer。

## 5.4 Project

```text
id
org_id
name
slug
repo_remotes
repo_fingerprint
default_branch
current_context_pack_id
current_workflow_template_id
status
created_at
updated_at
```

## 5.5 ContextPack

```text
id
org_id
project_id
version
branch
base_commit_sha
status
summary
module_map
business_flows
risks
test_strategy
source_refs
generated_by_tool
generated_by_user_id
generated_at
accepted_by_user_id
accepted_at
parent_context_pack_id
```

## 5.6 ContextUpdate

```text
id
org_id
project_id
session_id
base_context_pack_id
branch
from_commit_sha
to_commit_sha
status
summary
changed_modules
new_facts
risks
test_notes
source_refs
generated_by_tool
generated_by_user_id
created_at
reviewed_by_user_id
reviewed_at
review_comment
```

## 5.7 WorkflowTemplate

```text
id
org_id
project_id
name
status
version
steps
created_by_user_id
created_at
```

## 5.8 TaskSession

```text
id
org_id
project_id
task_name
task_source
agent_tool
user_id
context_pack_id
status
current_step
started_at
closed_at
```

## 5.9 WorkflowStepRun

```text
id
session_id
step_id
status
artifact_ids
requires_human_review
human_review_status
reviewed_by_user_id
completed_at
```

## 5.10 WorkArtifact

```text
id
org_id
project_id
session_id
step_id
type
title
content
local_path
content_hash
status
generated_by_tool
confirmed_by_user_id
created_at
```

## 5.11 Skill

```text
id
org_id
project_id
name
slug
status
version
trigger
instructions
input_schema
output_schema
source_session_id
source_artifact_ids
approved_by_user_id
created_at
```

## 5.12 AuditEvent

```text
id
org_id
project_id
actor_type
actor_id
event_type
target_type
target_id
payload
created_at
```

## 6. MCP / AI 工具协议

## 6.1 工具清单

AI 工具侧至少需要以下 MCP tools：

```text
agora_resolve_project
agora_check_context_freshness
agora_get_team_memory
agora_start_task
agora_record_workflow_step
agora_upload_artifact
agora_upload_context_pack
agora_upload_context_update
agora_upload_skill_candidate
agora_close_task
agora_get_project_status
agora_get_quality_status
```

## 6.2 agora_resolve_project

输入：

```json
{
  "local_path": "/workspace/member-center",
  "git_remote": "git@example.com:team/member-center.git",
  "branch": "main",
  "commit_sha": "8f34c2a",
  "dirty_workspace": false,
  "detected_project_name": "member-center"
}
```

输出：

```json
{
  "project_id": "project_1",
  "project_name": "会员中心研发协作平台",
  "task_name_required": true,
  "context_status": "fresh",
  "workflow_template_id": "workflow_1"
}
```

## 6.3 agora_get_team_memory

返回：

```json
{
  "context_pack": {},
  "workflow_template": {},
  "skills": [],
  "recent_writebacks": [],
  "quality_notes": []
}
```

AI 工具用这些内容减少 token 消耗和规范工作流程。

## 6.4 agora_upload_context_update

输入：

```json
{
  "project_id": "project_1",
  "session_id": "session_1",
  "base_context_pack_id": "ctx_v12",
  "branch": "main",
  "from_commit_sha": "8f34c2a",
  "to_commit_sha": "9a01d44",
  "summary": "修复优惠券支付后状态刷新问题",
  "changed_modules": [],
  "new_facts": [],
  "risks": [],
  "test_notes": [],
  "source_refs": []
}
```

输出：

```json
{
  "context_update_id": "ctx_update_1",
  "status": "pending_review"
}
```

## 7. Freshness 判断

Freshness 由 Agora 根据 AI 工具传入的本地 Git 状态和已 accepted ContextPack 判断。

## 7.1 判断输入

```text
project_id
branch
commit_sha
dirty_workspace
repo_remote
```

## 7.2 判断输出

```text
fresh
missing
stale
ahead
dirty_workspace
conflict
unknown
```

## 7.3 基础规则

- 没有 accepted ContextPack：missing。
- 本地 dirty：dirty_workspace。
- accepted ContextPack 的 base_commit_sha 等于本地 commit：fresh。
- accepted ContextPack 基线早于本地 commit：stale。
- accepted ContextPack 基线晚于本地 commit：ahead。
- 多个待合并更新覆盖相同模块：conflict。

## 7.4 Git 关系判断

Agora 默认不访问客户代码，因此不能直接运行 git 命令。Git 关系可以由 AI 工具侧上传：

```json
{
  "local_commit": "9a01d44",
  "known_base_commit": "8f34c2a",
  "relationship": "descendant",
  "changed_files": []
}
```

如果 AI 工具无法判断，Agora 返回 `unknown`，由 AI 工具提示用户或执行本地检查。

## 8. 上下文生成和合并

## 8.1 首次生成

1. AI 工具发现 missing。
2. AI 工具本地扫描项目。
3. AI 工具调用模型生成 ContextPack。
4. 上传 Agora，状态为 pending_review。
5. 项目经理审核。
6. accept 后成为 current_context_pack。

## 8.2 增量更新

1. AI 工具发现 stale。
2. AI 工具本地分析 changed files 和相关上下文。
3. 生成 ContextUpdate。
4. 上传 Agora。
5. 项目经理审核。
6. Agora 合并到新的 ContextPack version。

## 8.3 合并策略

第一阶段可以由 AI 工具生成候选合并结果，项目经理人工确认。

后续可以支持：

- 模块级合并。
- 风险级合并。
- source_ref 去重。
- 过期事实废弃。
- 版本差异对比。

## 9. 项目流程执行

## 9.1 流程模板

项目流程模板定义任务必须经过哪些步骤。典型流程：

```text
analysis -> design -> review -> implementation -> self_test -> upload
```

每步包含：

- prompt guidance。
- required artifacts。
- human review required。
- acceptance criteria。
- upload policy。

## 9.2 AI 工具执行

AI 工具读取 WorkflowTemplate 后：

1. 展示当前步骤。
2. 调用模型生成步骤产物。
3. 让用户审查。
4. 保存到本地。
5. 上传 Agora。
6. 记录 step complete。

## 9.3 阻断规则

可配置：

- 未完成分析不得进入设计。
- 未完成设计评审不得开发。
- 自测失败不得上传。
- 高风险任务必须技术负责人确认。

## 10. 审批和权限

## 10.1 角色权限

开发人员：

- start task。
- upload artifacts。
- upload ContextUpdate。
- upload skill candidate。

项目经理 / 技术负责人：

- approve ContextUpdate。
- approve Skill。
- manage workflow。
- view all sessions。

质量人员：

- view quality。
- upload quality report。
- request changes on quality issues。

管理员：

- manage org。
- manage members。
- manage integrations。

## 10.2 审批对象

- ContextPack。
- ContextUpdate。
- Skill。
- WorkflowTemplate。
- 高风险任务产物。

## 11. 存储架构

## 11.1 关系数据库

存储：

- 用户、组织、权限。
- 项目。
- ContextPack metadata。
- ContextUpdate。
- WorkflowTemplate。
- TaskSession。
- WorkArtifact metadata。
- Skill。
- Approval。
- AuditEvent。

推荐：

- 本地开发：SQLite。
- 团队部署：Postgres。

## 11.2 对象存储

存储：

- 大型任务文档。
- 附件。
- 导出的报告。
- 长 ContextPack 内容。

本地开发可先用文件目录，生产使用 S3 兼容对象存储。

## 11.3 搜索和向量索引

用途：

- 搜索团队资产。
- 检索上下文片段。
- 查找相似任务。
- 查找可复用 skill。

注意：

- 源码全文不一定进入 Agora。
- source_refs 和 AI 生成的摘要可以入索引。
- 是否上传源码片段由组织策略控制。

## 12. 安全和隐私

原则：

- 客户本地代码默认不由 Agora 拉取。
- AI 工具上传内容前应有人确认或遵循组织策略。
- dirty workspace 不自动进入团队全局上下文。
- 支持敏感路径 ignore。
- 支持 source_ref 只存路径/hash，不存源码内容。
- 审计所有上传、审批、合并行为。

策略：

- 项目级上传策略。
- 敏感目录规则。
- 最大文件大小。
- 是否允许源码片段入库。
- 是否允许 CI 自动更新主干上下文。

## 13. 部署架构

## 13.1 本地开发

```text
FastAPI
Next.js
SQLite
Fake search indexes
Local file artifact store
```

## 13.2 团队试用

```text
API service
Web UI
Postgres
Object storage
Search / vector index
MCP gateway
Background worker
```

## 13.3 企业部署

```text
API service replicas
Web service
Postgres HA
Object storage
OpenSearch / Qdrant
Background workers
Audit log sink
SSO / RBAC
Private network access
```

## 14. 后台任务

后台任务包括：

- ContextUpdate 合并候选生成。
- 搜索索引重建。
- 质量摘要刷新。
- stale context 提醒。
- skill candidate 聚类。
- 审计归档。

## 15. 与现有代码的关系

当前代码已经具备：

- FastAPI API。
- SQLAlchemy 模型。
- SQLite 持久化。
- 项目创建和初始化。
- ContextPack 基础模型。
- Session audit。
- Skill lifecycle 初步能力。
- Writeback 审批。
- Next.js Web UI。
- MCP adapter 雏形。

需要调整：

- server-side repo 初始化不再作为客户主流程，只保留为本地开发/导入辅助路径。
- fake ContextEngine 只能用于测试和早期 fallback，不作为真实黑盒验收。
- 增加 AI 工具上传 ContextPack / ContextUpdate 的主路径。
- 增加 WorkflowTemplate 和 WorkArtifact。
- 增加 ContextUpdate 审核合并。
- 增加项目经理和质量人员视图。

## 16. 分阶段实现建议

## 16.1 P2 重排：AI 工具接入和项目解析

- 新增 resolve-local API/MCP。
- 新增 freshness-check API/MCP。
- 新增 get-team-memory API/MCP。
- 让 AI 工具主流程可识别项目、任务和上下文状态。

## 16.2 P3 重排：ContextPack 上传和版本治理

- 新增 ContextPack upload。
- 新增 ContextUpdate upload。
- 新增 ContextPack version model。
- 新增 ContextUpdate review queue。
- Web UI 支持审核合并。

## 16.3 P4 重排：项目流程模板和任务产物

- 新增 WorkflowTemplate。
- 新增 WorkflowStepRun。
- 新增 WorkArtifact。
- AI 工具按流程上传产物。
- Web UI 审计任务流程。

## 16.4 P5 重排：Skill 和团队经验治理

- 完善 candidate skill。
- 支持从任务产物和 writeback 生成 skill candidate。
- Web UI 审批、版本、废弃、使用历史。

## 16.5 P6 重排：质量和项目管理视图

- 项目任务状态。
- 质量状态。
- 风险视图。
- AI 工具查询项目状态和质量状态。

## 17. 黑盒测试架构

真实黑盒测试必须至少包含：

1. 准备一个本地软件研发项目。
2. 通过 AI 工具调用 Agora resolve_project。
3. Agora 返回 missing 或 stale。
4. AI 工具本地分析项目并生成 ContextPack。
5. AI 工具上传 ContextPack 到 Agora。
6. 项目经理在 Web UI 审批。
7. AI 工具再次进入项目，获取 fresh ContextPack、workflow、skill。
8. AI 工具按流程执行一个真实任务。
9. 每步产物上传 Agora。
10. 任务结束上传 ContextUpdate 和 skill candidate。
11. 项目经理在 Web UI 审核合并。
12. 质量人员或项目经理通过 AI 工具查询状态。

## 18. 技术风险

## 18.1 AI 工具能力差异

不同 AI 工具支持的文件访问、MCP、命令执行能力不同。

应对：

- 抽象 MCP/API 协议。
- 定义最小能力集。
- 提供 CLI uploader fallback。

## 18.2 上下文质量不可控

AI 生成上下文可能错误。

应对：

- source_refs 必填。
- pending_review 默认。
- 项目经理审批。
- 版本回滚。
- 质量评分和审计。

## 18.3 隐私风险

AI 工具可能上传敏感源码或配置。

应对：

- 上传策略。
- ignore 规则。
- 用户确认。
- 敏感内容扫描。
- 只存摘要和 source_ref 的模式。

## 18.4 自动化过度打扰

如果每次 stale 都打断用户，会降低体验。

应对：

- 后台更新。
- 只在高风险场景提示。
- 状态明确但不强制中断。

## 19. 验收指标

产品指标：

- 开发者无需打开 Web UI 即可获取项目上下文。
- 新成员能通过 AI 工具快速按项目流程完成任务。
- 多人使用同一项目上下文。
- ContextUpdate 可审批和合并。
- Skill candidate 可审批入库。
- 项目经理能查看任务状态。
- 质量人员能查看质量状态。

技术指标：

- API/MCP 覆盖核心 AI 工具路径。
- ContextPack 有版本和 source_refs。
- 任务每步产物可审计。
- 审批事件完整。
- 权限边界清晰。
- fake 流程不作为黑盒验收依据。
