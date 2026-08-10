# Agora 团队级 AI 项目 Harness 设计

## 摘要

Agora 是一个团队级 AI 项目 Harness。它把已有项目资产转化为共享的项目认知，把这些认知暴露给 AI Agent，编排可复用的团队 Skill，记录 AI 工作会话，并把有价值的结果回写到项目知识库。

Agora 的核心不是 Web 知识库、聊天产品，也不是单独的 MCP Server。Agora 的核心产品是 AI Agent 背后的 Harness 编排层。

主要使用体验是：

```text
研发 / 测试 / 产品 / 项目经理在自己的 AI Agent 对话框中工作
-> Agent 自动调用 Agora
-> Agora 识别项目和任务
-> Agora 返回最小必要 ContextPack
-> Agora 编排相关 Skill
-> Agent 完成工作
-> Agora 记录过程并回写可复用知识
```

Minimal Web 只用于项目初始化、连接器配置、分析结果查看、Skill 审核、Session 查看和 Writeback 审核。

## 目标

- 让不同角色、不同 AI 工具共享同一份项目理解。
- 让 AI Agent 获取准确的项目上下文，而不是让用户反复解释项目。
- 通过分层、任务相关的 ContextPack 减少 token 浪费。
- 把团队重复工作流沉淀为可复用、可版本化、可审核的 Skill。
- 把 AI 工作结果沉淀为持久项目知识，包括总结、风险、决策和测试建议。
- 从第一天支持多项目 SaaS 和私有化部署。
- 优先复用成熟基础设施组件，不重复开发 RAG、向量检索、图存储、工作流引擎或 MCP 协议。

## 非目标

- P0 不做完整项目管理系统。
- P0 不做复杂 Web 驾驶舱或在线 IDE。
- P0 不要求研发把 CLI 作为主工作流。
- P0 不实现细粒度权限 UI。
- P0 不深度集成所有外部工具，例如 Figma、Slack、飞书、Teams、CI、监控或测试平台。

## 产品原则

研发不应该需要说“使用 Agora”，也不应该需要执行终端命令。研发的正常入口只有 AI Agent 对话框。

Agora 应该成为 Agent 背后的默认项目记忆层和工作流 Harness。

## 用户角色

### 研发

主入口：AI Agent 对话框。

示例：

```text
帮我实现 AG-128。
```

Agora 应自动识别当前项目，推断或解析任务，生成相关上下文，在合适时运行影响分析、风险检查、测试建议等 Skill，并在 Agent 完成后准备回写内容。

### 测试

主入口：AI Agent 对话框。

示例：

```text
帮我为 AG-128 生成测试点和回归范围。
```

Agora 结合需求上下文、接口上下文、代码变更、历史 Bug 和风险规则，生成结构化测试建议。

### 产品经理

主入口：AI Agent 对话框。

示例：

```text
帮我检查这个需求有没有歧义、冲突和缺失的验收标准。
```

Agora 检索历史需求、决策、接口和模块上下文，输出澄清问题和验收标准建议。

### 项目经理

主入口：AI Agent 对话框。

示例：

```text
生成本周项目进度、风险和阻塞摘要。
```

Agora 汇总任务、PR、Session、Writeback、风险和阻塞。

### 新人

主入口：AI Agent 对话框。

示例：

```text
我是新加入的后端研发，帮我理解这个项目，并规划前三天入门路径。
```

Agora 基于项目、模块、文档、代码规范和当前迭代知识生成新人导览。

### 管理员

主入口：Minimal Web。

管理员创建项目、配置连接器、查看同步状态、审核初始化分析结果。

### Skill 负责人

主入口：Minimal Web。

Skill 负责人审核 AI 生成的候选 Skill，编辑触发条件和输入输出结构，发布 Skill，并查看 Skill 运行情况。

## 系统架构

```text
AI Agent 对话框
Codex / Cursor / Claude Code / Kimi / ChatGPT / 内部 Agent
        |
Agent Adapter Layer
MCP / Plugin / API / Project Rules / PR Bot
        |
Agora Harness
Project Resolver / Task Resolver / Context Planner
Skill Orchestrator / Policy Engine / Session Recorder / Memory Writeback
        |
Runtime Layer
LangGraph / Temporal
        |
Knowledge Layer
LlamaIndex / PostgreSQL / Qdrant / OpenSearch / Neo4j / Redis
        |
Asset Connectors
Git / Docs / Task System / OpenAPI / PR / Commit
```

## 成熟组件复用策略

Agora 默认优先复用成熟组件。

| 关注点 | 组件 |
| --- | --- |
| RAG、接入、切分、检索 pipeline | LlamaIndex |
| Agent/Harness 状态机 | LangGraph |
| 可靠后台工作流 | Temporal |
| 主业务数据 | PostgreSQL |
| 向量检索 | Qdrant |
| 关键词和混合检索 | OpenSearch |
| 项目知识图谱 | Neo4j |
| 缓存和短期状态 | Redis |
| MCP 协议支持 | 官方 MCP SDK |
| 模型路由和治理 | LLM Gateway |

Agora 自研重点：

- Harness 生命周期。
- ContextPack 策略。
- Skill Registry 和 Skill Runner 语义。
- 项目资产语义模型。
- TaskSession 记录。
- Memory Writeback。
- Agent 接入协议。

## 核心服务

### Agent Adapter Service

职责：

- 暴露 MCP tools。
- 暴露 Agent-facing API。
- 适配 Plugin 或 Project Rule 集成。
- 校验 Agent 的 scoped access。
- 把 Agent 请求转换为 Harness 调用。

该服务不实现核心业务逻辑，也不直接查询数据库。

### Harness Service

Agora 的核心产品层。

职责：

- 识别项目。
- 识别任务。
- 规划上下文。
- 编排 Skill。
- 执行工作流策略。
- 记录 Session 事件。
- 准备和关闭 Writeback。

Harness 工作流可以用 LangGraph 表达。

### Core API Service

职责：

- 管理 Organization、Project、ConnectorConfig、Asset、AssetRelation、ContextPack、Skill、SkillRun、TaskSession、Writeback 和 AuditLog。
- 服务 Minimal Web 和内部服务。

### Ingestion Worker

职责：

- 同步 Git、文档、任务系统、OpenAPI、PR 和 commit。
- 把外部数据统一归一化为 Asset。

长流程同步使用 Temporal。

### Knowledge Worker

职责：

- Asset 切分。
- 生成摘要和 embedding。
- 写入 Qdrant 和 OpenSearch。
- 构建 Neo4j 图关系。
- 生成或刷新 ContextPack。

### Skill Worker

职责：

- 运行 Skill。
- 校验结构化输出。
- 记录 SkillRun。
- 从重复项目流程和资产中提炼候选 Skill。

### Minimal Web

职责：

- 项目设置。
- 连接器配置。
- 初始化报告。
- 资产浏览。
- Skill 审核和管理。
- Session 查看。
- Writeback 审核。

## Harness 生命周期

Agent 调用高层 Harness 工具，不直接调用底层知识库。

```text
start_work
-> resolve_project / resolve_task
-> plan_context
-> fetch_context_ref
-> run_skill
-> record_event
-> prepare_writeback
-> close_work
```

### MCP Tools

P0 暴露以下 MCP tools：

- `agora_start_work`
- `agora_plan_context`
- `agora_fetch_context_ref`
- `agora_run_skill`
- `agora_record_event`
- `agora_prepare_writeback`
- `agora_close_work`
- `agora_search_knowledge`

`agora_search_knowledge` 是兜底探索工具。主流程应由 Harness 引导。

### Agent 默认规则

每个接入 Agora 的 Agent 应配置默认规则：

```text
当用户提出项目相关分析、开发、测试、Review、总结或风险判断任务时：
1. 除非用户明确要求不要使用 Agora，否则先调用 agora_start_work。
2. 在给出实现方案前调用 agora_plan_context。
3. 运行 Agora 返回的 required skills。
4. 当涉及核心模块、接口或测试影响时，运行相关影响分析、风险检查或测试建议 Skill。
5. 在完成前调用 agora_prepare_writeback。
6. 用户确认后，或任务阻塞时，关闭 session。
```

## ContextPack 策略

ContextPack 是针对当前任务的最小必要项目认知包，不是原始搜索结果列表。

要求：

- 少。
- 准。
- 新。
- 可追溯。
- 可分层。
- 受 token budget 控制。

### 分层

| 层级 | 用途 | 典型大小 |
| --- | --- | --- |
| L0 Session Brief | 项目/任务/意图摘要和约束 | 1k-2k tokens |
| L1 Working Context | 需求、模块、接口、风险、决策、相关代码路径 | 4k-8k tokens |
| L2 Deep Context | 完整引用片段或展开资产 | 按需 |

### 检索 Pipeline

```text
OpenSearch 关键词检索
+ Qdrant 语义检索
+ Neo4j 图关系遍历
+ LlamaIndex rerank/summarize
-> Harness 根据意图和 token budget 压缩
-> 生成可追溯 ContextPack
```

ContextPack 中的每个关键事实都应引用来源，例如 task、doc、file、API、PR 或 writeback。

## Skill 体系

Skill 是可复用、可执行、可版本化、可审核的团队工作流能力包。

### 范围

- System Skill。
- Organization Skill。
- Project Skill。

### 生命周期

```text
candidate -> draft -> approved -> deprecated
```

AI 可以生成 candidate skill，但不能在无人审核的情况下发布为 approved skill。

### 初始 Skill

P0 system skills：

- `task-context-summary`
- `impact-analysis`
- `test-case-generation`
- `risk-check`
- `knowledge-writeback`

后续 system skills：

- `requirement-clarification`
- `pr-review`
- `newcomer-onboarding`
- `weekly-report`

Skill 输出必须结构化，方便用于 PR 评论、报告、Writeback、后续 Skill 和驾驶舱。

## 数据模型

核心对象：

- Organization。
- Project。
- ConnectorConfig。
- Asset。
- AssetRelation。
- ContextPack。
- Skill。
- SkillRun。
- TaskSession。
- Writeback。
- AuditLog。

核心闭环：

```text
Git / Docs / Task / OpenAPI -> Asset
Asset -> Index / Graph
Index / Graph -> ContextPack
ContextPack + Skill -> Agent Work
Agent Work -> Writeback
Accepted Writeback -> Asset
```

### Asset

Asset 统一归一化所有项目来源。

示例：

- `code_file`
- `doc`
- `module`
- `task`
- `api_spec`
- `commit`
- `pull_request`
- `decision`
- `meeting_note`
- `writeback`

### TaskSession

每次 Agent 工作会话记录：

- Project。
- Task 或 free-form intent。
- Agent type。
- 使用过的 ContextPack。
- 运行过的 Skill。
- 重要事件。
- 输出结果。
- Writeback。
- 状态。

### Writeback

Writeback 类型：

- `development_summary`
- `test_suggestion`
- `risk_note`
- `decision_record`
- `module_note`
- `api_change_note`
- `task_update`
- `pr_summary`
- `skill_candidate`

除非策略允许自动接受，否则 Writeback 默认是 draft。Accepted Writeback 会转成 Asset 并重新索引。

## 项目初始化流程

管理员在 Minimal Web 创建项目，并至少配置 Git。

工作流：

```text
validate_connectors
-> sync_git_repository
-> sync_docs
-> sync_tasks
-> sync_openapi
-> parse_assets
-> build_indexes
-> build_asset_graph
-> generate_project_context
-> extract_skill_candidates
-> generate_initial_report
```

P0 必须支持 Git。Docs、任务系统和 OpenAPI 可以先作为可选或 mock 集成。

初始化应产出：

- 项目摘要。
- 技术栈。
- 模块地图。
- 核心目录。
- 测试结构。
- 主要文档。
- 初始 ContextPack。
- 可用时生成候选 Skill。

## Minimal Web 范围

页面：

- Projects。
- 创建项目和连接器。
- 初始化报告。
- Assets。
- Skills。
- Sessions。
- Writebacks。
- Settings。

Minimal Web 不能成为研发日常工作入口。

## PR Bot 兜底

PR Bot 不是主入口，而是安全兜底。

触发：

- PR created。
- PR updated。
- PR marked ready for review。

工作流：

```text
识别项目和任务
-> 读取 diff 和 changed files
-> 规划上下文
-> 运行 impact-analysis / test-case-generation / risk-check
-> 评论 PR
-> 创建 Writeback draft
-> 尽可能关联已有 TaskSession
```

Bot 应避免反复刷屏。后续分析尽量更新或折叠已有评论。

## 治理最低要求

即使 P0 不展示复杂权限 UI，后端也必须具备治理基础：

- 所有记录带 `org_id` 和 `project_id`。
- Qdrant、OpenSearch、Neo4j 中的记录都带租户和项目 metadata。
- 连接器凭证加密。
- Agent token scoped。
- Writeback 支持审核。
- 敏感信息和 PII 在索引前扫描。
- AuditLog 记录项目创建、连接器配置、Agent 访问、ContextPack 生成、SkillRun、Writeback 和 Skill 发布。
- LLM 调用统一经过 LLM Gateway。

建议接入的敏感信息扫描工具：

- gitleaks。
- trufflehog。
- detect-secrets。

## 部署

Agora 应支持：

- SaaS 多租户部署。
- 私有化单租户部署。
- Docker Compose 本地开发。

生产基线：

- API service。
- Agent Adapter/MCP service。
- Worker service。
- Minimal Web。
- PostgreSQL。
- Qdrant。
- OpenSearch。
- Neo4j。
- Redis。
- Temporal。
- Object storage。
- Vault/KMS。
- LLM Gateway。

可观测性：

- OpenTelemetry。
- Prometheus/Grafana。
- Sentry 或同类错误追踪。
- Worker 和 sync run 日志。
- LLM 成本和 token 指标。

## 推荐技术栈

- Backend：Python + FastAPI。
- Agent workflow：LangGraph。
- Durable workflow：Temporal。
- RAG/indexing：LlamaIndex。
- Main DB：PostgreSQL。
- Vector DB：Qdrant。
- Search：OpenSearch。
- Graph DB：Neo4j。
- Cache：Redis。
- MCP：官方 MCP SDK。
- Web：Next.js + TypeScript。
- Infra：Docker Compose + Helm。

## 仓库结构

```text
agora/
  apps/
    api/
    mcp/
    web/
    workers/
  packages/
    domain/
    core/
    harness/
    knowledge/
    integrations/
    llm/
    storage/
    observability/
  infra/
  docs/
  tests/
```

早期运行进程：

- `api`
- `mcp`
- `worker`
- `web`

代码可以保持 monorepo，同时保留清晰的服务和 package 边界。

## P0 范围

P0 证明核心闭环：

```text
已有 Git 项目
-> 自动分析
-> Agent 默认获取项目上下文
-> Skill 运行
-> 工作结果回写
-> 新知识后续可复用
```

### P0 必须包含

- 项目创建。
- Git connector。
- Git 初始化分析。
- Asset 模型和存储。
- Qdrant 和 OpenSearch 索引。
- 基础 Neo4j graph。
- L0/L1 ContextPack。
- Harness API。
- MCP Adapter。
- TaskSession。
- 内置 Skill Runner。
- Writeback draft、accept 和 re-index。
- Minimal Web 核心页面。

### P0 可以暂缓

- 真实任务系统深度集成。
- OpenAPI 深度影响分析。
- PR Bot。
- Skill 自动提炼。
- PM 周报。
- 完整新人导览。
- IDE 专用插件。
- 复杂权限 UI。

## P0 验收场景

1. 管理员在 Minimal Web 中通过 Git 仓库创建项目。
2. Agora 同步并分析项目。
3. Web 展示项目摘要、模块和资产。
4. 研发在 AI Agent 中说：“分析如何实现退款失败重试。”
5. Agent 自动通过 MCP 调用 Agora。
6. Agora 返回 ContextPack。
7. Agent 运行影响分析和测试建议 Skill。
8. Agent 输出实现建议。
9. Agent 准备开发总结和测试建议 Writeback。
10. Web 审核人接受 Writeback。
11. Accepted Writeback 成为 Asset 并重新索引。
12. 后续相似问题可以检索到这次 Writeback。

## P0 用户故事

### 管理员创建项目

作为管理员，我可以通过 Git 仓库创建 Agora 项目，让 Agora 分析已有代码库。

验收标准：

- 管理员可以输入项目名称、Git remote、credential reference 和默认分支。
- Agora 在初始化前校验连接器。
- Agora 记录同步状态和可见错误。
- 初始化后，Minimal Web 展示项目摘要、模块摘要和资产数量。

### Agent 自动识别项目

作为研发，我可以让 AI Agent 在当前仓库工作，而不需要说“使用 Agora”。

验收标准：

- Agent 可以带 repo metadata 调用 `agora_start_work`。
- Harness 根据 Git remote 识别当前项目。
- 如果无法识别项目，Harness 返回澄清请求，而不是猜测。
- 创建 TaskSession。

### Agent 获取任务上下文

作为 AI Agent，我可以请求当前工作的 context plan，获得有用项目上下文，而不是加载整个项目。

验收标准：

- `agora_plan_context` 返回 L0 或 L1 ContextPack。
- ContextPack 包含 summary、key facts、relevant modules、relevant code paths、risks、suggested skills 和 source refs。
- ContextPack 遵守 token budget。
- 至少一个 source reference 可以通过 `agora_fetch_context_ref` 展开。

### Agent 运行 Skill

作为 AI Agent，我可以运行标准项目 Skill，让团队重复流程产生结构化输出。

验收标准：

- `impact-analysis`、`test-case-generation`、`risk-check` 和 `knowledge-writeback` 可以通过 `agora_run_skill` 运行。
- Skill 输出按 output schema 校验。
- SkillRun 记录包含 session、inputs、context used、outputs、status 和 warnings。

### 知识被回写

作为团队，我们可以把有用的 AI 工作输出变成持久项目知识。

验收标准：

- `agora_prepare_writeback` 创建 draft Writeback。
- Minimal Web 可以列出并查看 draft writebacks。
- 审核人可以接受 Writeback。
- Accepted Writeback 成为 Asset。
- Accepted Writeback 被索引，并能被后续 ContextPack 或搜索检索到。

## 关键取舍和风险

### Harness 优先，而不是暴露底层工具

决策：Agent 调用 Harness 层工具，而不是直接调用 Qdrant、OpenSearch、Neo4j 或 Asset CRUD API。

原因：保持 Agent 行为稳定，减少 token 浪费，集中执行策略，并让 Writeback 可审计。

风险：高级探索可能需要更底层能力。缓解：保留 `agora_search_knowledge` 作为兜底，同时在 Agent 主路径之外提供 admin/debug API。

### P0 直接引入较完整基础设施

决策：从一开始使用 PostgreSQL、Qdrant、OpenSearch、Neo4j、Redis、Temporal、LlamaIndex 和 LangGraph。

原因：Agora 天然是基础设施型产品，后期替换存储、搜索和工作流底座代价高。

风险：本地部署和运维更重。缓解：提供 Docker Compose 做本地/demo，Helm 做生产部署，并保持 P0 的图关系和搜索能力最小可用。

### Agent-first 使用体验

决策：研发把 AI Agent 对话框作为主入口。

原因：符合真实研发工作流，避免强迫团队学习新的日常工具。

风险：不同 Agent 的集成机制不同。缓解：Agent Adapter 独立，优先支持 MCP，同时为 Plugin、API 和 Project Rule Adapter 留扩展空间。

### Writeback 默认 draft

决策：Agent 生成的知识默认 draft，除非策略明确允许自动接受。

原因：Agora 不应把 AI 推断静默变成正式项目知识。

风险：审核可能成为瓶颈。缓解：后续允许低风险类型，如开发总结，通过项目策略自动接受。

### P0 Git-first

决策：P0 要求 Git，暂缓任务系统和 OpenAPI 深度集成。

原因：Git 是最普遍的项目资产来源，足以证明 Harness 核心闭环。

风险：缺少任务系统后，任务上下文较弱。缓解：支持 free-form task intent，并提前保留 ConnectorConfig/API 扩展点。

## 开放问题

- 首批支持哪些 AI Agent：Codex、Cursor、Claude Code、Kimi、ChatGPT，还是内部 Agent？
- 首批支持哪些 Git provider：GitHub、GitLab、Gitee、自托管 GitLab？
- LLM Gateway 首批支持哪些模型供应商？
- P0 是否必须从第一天启用 Neo4j，还是先保留 graph adapter 和最小关系集？
- Writeback 是否所有类型默认 draft，还是低风险 summary 可以自动 accepted？
