# Agora 系统使用与技术手册

> 适用版本：P0-P9 当前代码基线 `1d5b356`
>
> 更新时间：2026-08-28
>
> 面向读者：第一次接触 AI 工具、MCP、后端服务和数据库的使用者，以及开发、评审、质量、项目经理和运维人员。
>
> 重要说明：本手册以当前代码真实能力为准。已发现但尚未修复的问题见 `docs/reviews/2026-08-28-agora-p0-p9-code-review.zh-CN.md`。当前版本适合本地开发、演示和受控试点，不应直接当作生产完成版部署。

## 1. 一句话理解 Agora

Agora 是软件研发团队的“AI 协作控制台和共享记忆库”。

开发人员仍然在 Codex、Claude Code、Cursor 或其他 AI 工具里工作。AI 工具通过 Agora 获取团队已经确认的项目上下文、开发流程和 Skill，再把本次任务的产物、测试证据和经验候选提交回 Agora。Web 页面主要用于查看、审批、审计和项目管理。

理想工作流：

```text
开发人员提出任务
  -> AI 工具自动找到 Agora 项目
  -> 获取团队上下文、流程和 Skill
  -> 人在 AI 工具中确认分析、设计、开发和测试
  -> AI 工具记录产物与质量证据
  -> 提交上下文和 Skill 候选
  -> Reviewer 在 Web 审批
  -> 团队下一次直接复用
```

## 2. Agora 解决什么问题

没有 Agora 时，不同开发人员和不同 AI 工具通常只知道当前聊天窗口的内容：

- A 告诉 AI 的约束，B 的 AI 不知道。
- 聊天记录删除后，设计和踩坑经验一起丢失。
- AI 容易跳过设计、评审或测试。
- 项目经理看不到 AI 正在执行到哪一步。
- 质量人员找不到“测试通过”的原始证据。
- 相同项目被多人重复完整分析，浪费 token 和时间。

Agora 把这些信息变成团队可共享、可版本化、可审批、可追溯的对象。

## 3. 系统组成

### 3.1 AI 工具

AI 工具是日常工作界面，负责读取本地代码和文档、修改代码、执行命令、运行测试、与人交互，并根据本地项目生成结构化 ContextProposal。

客户源码默认应留在 AI 工具所在机器，不由 Agora 服务端主动拉取和分析。

### 3.2 Local Connector / MCP Server

MCP 可以理解为“AI 工具调用外部能力的标准插座”。Agora MCP Server：

- 向 AI 工具公布 `agora_start_work`、`agora_prepare_context` 等工具。
- 观察当前 Git remote、branch、commit 和工作区状态。
- 清理 remote 中的用户名、密码或 token。
- 把 MCP 调用转换成 Agora HTTP API 请求。

### 3.3 Harness

Harness 是 Agora 的任务编排核心。它回答：当前项目和任务是什么、本次会话固定哪些 Context/Workflow/Skill 版本、当前流程步骤是什么、下一步做什么、结束时沉淀什么。

### 3.4 API、数据库和 Worker

FastAPI 是服务端入口，SQLAlchemy 把业务对象写入 SQLite 或 PostgreSQL。数据库是事实源，保存项目、任务、上下文、Skill、质量证据、审批和审计。

Outbox Worker 处理事务提交后的异步事件。当前 Worker 只支持手动执行一批，尚不是常驻服务。

### 3.5 Web

Web 用于管理和治理，不是日常写代码的地方。当前页面包括 Projects、Work items、Project status、Operations summary、Assets、Context、Skills、Sessions、Security audit 和 Writebacks。

## 4. 架构图

```text
开发人员电脑
┌──────────────────────────────────────────────┐
│ AI 工具                                       │
│  ├─ 读取本地源码、文档、Git                   │
│  ├─ 修改代码、运行测试                        │
│  └─ 调用 Agora MCP                            │
│            │                                  │
│            ▼                                  │
│ Local Connector / MCP                         │
│  ├─ Git 观察与敏感信息清理                    │
│  └─ MCP -> HTTP API                           │
└────────────┬─────────────────────────────────┘
             │ Bearer token + JSON
             ▼
Agora 服务端
┌──────────────────────────────────────────────┐
│ FastAPI -> Auth/RBAC/Request ID               │
│          -> Harness Coordinator               │
│          -> Context/Workflow/Skill/Quality    │
│          -> SQLAlchemy -> SQLite/PostgreSQL   │
│          -> Outbox Worker                     │
└────────────┬─────────────────────────────────┘
             ▼
Agora Web：查看、审批、审计、状态和运维
```

## 5. 核心术语

### Project

Agora 中的项目空间。Git remote 是自动识别项目的重要依据。

### WorkItem

真实项目任务，例如 `PAY-318 完善退款幂等处理`。一个 WorkItem 可以由多人和多个 AI 会话共同完成。

### WorkSession

某个开发人员使用某个 AI 工具处理 WorkItem 的一次会话。它记录本次使用的上下文、流程、Skill、产物和证据。

### Workflow

项目规定的开发流程，例如：

```text
分析 -> 设计 -> 评审 -> 开发 -> 自测 -> 交付
```

每一步可以要求固定 WorkArtifact 和 HumanConfirmation。

### ContextStream / ContextRevision / ContextProposal

- ContextStream：某项目、某分支的上下文版本通道。
- ContextRevision：已经人审、不可变的正式上下文版本。
- ContextProposal：AI 基于本地项目生成、等待 Reviewer 审批的候选。

Proposal 类型包括 `initial`、`refresh`、`task_update` 和 `correction`。

### ContextBundle

Harness 针对当前任务返回的最小必要上下文：

- L0：项目、任务、关键约束和下一步。
- L1：相关模块、风险、流程和 Skill。
- L2：按需展开的 source ref。

这样可以减少 token 使用量。

### Skill / SkillVersion

Skill 是团队可复用的 AI 工作方法；SkillVersion 是不可变版本。历史 WorkSession 固定实际使用的版本。

### QualityEvidence

可追溯的质量证据，例如本地测试、CI、代码评审和风险检查。Agora 不应把 AI 的一句“应该没问题”当作测试通过。

### Outbox

数据库事务成功后留下的异步事件。Worker 可重试处理，避免业务数据已提交但通知或投影静默丢失。

## 6. 当前版本限制

开始使用前必须了解：

- 当前适合本地开发、演示和受控试点。
- stdio MCP 缺少 `agora_complete_workflow_step`，完整流程推进需先修复。
- 当前只有一个 Local Bootstrap User，没有团队成员管理页面。
- Docker Compose 的 Web/Connector API 地址变量错误，不能按原样使用。
- Compose PostgreSQL 没有持久化卷。
- 项目首页的服务端本地仓库初始化是旧能力，共享部署不要使用。
- Outbox Worker 需要人工运行 `outbox-once`。
- 检索使用进程内 Fake 索引，不适合多 API 实例和大规模数据。
- P8 提供标准信号接口，但不是完整 GitHub/GitLab/Gitee provider adapter。
- SSO、token 生命周期和企业身份治理尚未完成。

## 7. 本地运行准备

### 7.1 软件要求

- Git。
- Python 3.10 或更高。
- Node.js 22 左右和 npm。
- 支持 MCP 的 AI 工具。

检查：

```bash
git --version
python3 --version
node --version
npm --version
```

### 7.2 安装后端

```bash
cd /Users/daniel/Documents/Agora/.worktrees/agora-p0
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
```

虚拟环境是本项目独立的一套 Python 依赖。

验证：

```bash
.venv/bin/python -c "import fastapi, sqlalchemy, mcp; print('Python dependencies OK')"
```

### 7.3 安装 Web

```bash
cd /Users/daniel/Documents/Agora/.worktrees/agora-p0/apps/web
npm ci
cd ../..
```

### 7.4 生成三类 token

```bash
openssl rand -hex 32
openssl rand -hex 32
openssl rand -hex 32
```

分别作为 human、agent 和 CI token。三者必须不同，不要提交进 Git。

## 8. 推荐的 SQLite 启动方式

### 8.1 终端 1：环境变量和数据库

```bash
cd /Users/daniel/Documents/Agora/.worktrees/agora-p0

export AGORA_ENV=development
export AGORA_DATABASE_URL='sqlite+pysqlite:///.agora/agora.db'
export AGORA_BOOTSTRAP_ORG_ID='local-org'
export AGORA_BOOTSTRAP_HUMAN_TOKEN='替换成人工token'
export AGORA_BOOTSTRAP_AGENT_TOKEN='替换成AI工具token'
export AGORA_BOOTSTRAP_CI_TOKEN='替换成CI-token'
```

先检查迁移：

```bash
.venv/bin/python -m scripts.agora_admin migrate \
  --database-url "$AGORA_DATABASE_URL" \
  --dry-run
```

再执行：

```bash
.venv/bin/python -m scripts.agora_admin migrate \
  --database-url "$AGORA_DATABASE_URL"
```

### 8.2 启动 API

```bash
.venv/bin/uvicorn apps.api.main:app \
  --host 127.0.0.1 \
  --port 8000
```

验证：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

期望 `/health.status=ok`、`/ready.status=ready`、schema revision 为 `20260826_0012`，并且 `missing_required` 为空。

### 8.3 终端 2：启动 Web

```bash
cd /Users/daniel/Documents/Agora/.worktrees/agora-p0/apps/web

export AGORA_API_URL='http://127.0.0.1:8000'
export AGORA_WEB_HUMAN_TOKEN='替换成人工token'

npm run dev -- --hostname 127.0.0.1 --port 3000
```

打开 `http://127.0.0.1:3000/projects`。

### 8.4 终端 3：运行冒烟

```bash
cd /Users/daniel/Documents/Agora/.worktrees/agora-p0

.venv/bin/python -m scripts.agora_admin smoke \
  --api-base-url http://127.0.0.1:8000 \
  --web-base-url http://127.0.0.1:3000
```

期望输出 API readiness、Metrics 和 Web 均为正常。

## 9. 连接 AI 工具

### 9.1 MCP 命令

```bash
cd /Users/daniel/Documents/Agora/.worktrees/agora-p0

AGORA_API_URL=http://127.0.0.1:8000 \
AGORA_AGENT_TOKEN='替换成AI工具token' \
.venv/bin/python -m apps.mcp.server
```

MCP 是 stdio 进程，不需要单独端口。

### 9.2 通用配置示例

```json
{
  "mcpServers": {
    "agora": {
      "command": "/Users/daniel/Documents/Agora/.worktrees/agora-p0/.venv/bin/python",
      "args": ["-m", "apps.mcp.server"],
      "cwd": "/Users/daniel/Documents/Agora/.worktrees/agora-p0",
      "env": {
        "AGORA_API_URL": "http://127.0.0.1:8000",
        "AGORA_AGENT_TOKEN": "替换成AI工具token",
        "AGORA_WORKSPACE_ROOT": "AI工具当前开发项目的本地目录"
      }
    }
  }
}
```

注意：

- Agent token 必须与 API 的 bootstrap agent token 相同。
- Workspace root 指向开发人员的项目，不是 Agora 仓库。
- MCP 不应直接访问 Agora 数据库。
- 不要把 human token 给 AI 工具。

### 9.3 推荐 AI 项目规则

```text
处理本项目的分析、设计、开发、测试、评审、总结和状态查询时，默认使用 Agora。
开始时调用 agora_start_work，再调用 agora_prepare_context。
优先使用 Agora 的已审批上下文、流程和 Skill。
如果上下文缺失或过期，读取本地代码和文档，生成 ContextProposal；不要让 Agora 服务端扫描本地绝对路径。
每个流程步骤都向我展示产物并等待人工确认。
测试后调用 agora_record_evidence，失败或未运行不得写成通过。
可复用经验通过 agora_submit_skill_candidate 提交，不能直接标记为已批准。
结束时调用 agora_close_work。
Agora 不可用时可以继续本地工作，但必须标记尚未同步。
```

当前已知问题：AI 工具暂时看不到 `agora_complete_workflow_step`，这需要先按审查报告修复。

## 10. 第一次创建项目和上下文

### 10.1 Web 创建项目

在 Projects 页面填写：

- Organization：本地试点用 `local-org`。
- Project name：例如 `支付服务`。
- Slug：例如 `payment-service`。
- Git remote：真实项目 remote。

Git remote 让 Local Connector 能根据当前仓库自动匹配 Agora Project。

### 10.2 不推荐的旧入口

项目首页的 `Initialize from local repository` 会让 API 服务端直接读取绝对路径。这只可用于 API 和源码都在同一台受信任开发机的兼容演示。共享服务器、容器或真实客户数据环境不要使用。

### 10.3 推荐的首次上下文提示

在真实项目目录打开 AI 工具，输入：

```text
请通过 Agora 开始当前项目的“建立初始上下文”任务。
如果没有已审批上下文，请扫描当前本地项目，整理项目概览、技术栈、模块、关键业务流程、约束、风险、测试策略和 source anchors，提交 initial ContextProposal，等待人工审批。不要上传完整源码或本地绝对路径。
```

期望调用顺序：

1. `agora_start_work`。
2. `agora_prepare_context`。
3. AI 本地分析代码和文档。
4. `agora_submit_context_proposal`。
5. Proposal 保持 submitted，等待人审。

### 10.4 Web 审批

进入 `Projects -> 项目 -> Context`，检查类型、目标分支、summary、模块、约束、风险、source anchors、provenance 和 commit 信息。确认没有臆测、秘密、完整源码或本地绝对路径后再审批。

审批会创建不可变 ContextRevision，并推进 ContextStream head。

## 11. 开发人员日常流程

### 11.1 开始任务

示例：

```text
请通过 Agora 开始任务 PAY-318：完善退款接口幂等处理。
先获取团队上下文和项目流程，然后分析需求。每个流程步骤都把产物展示给我确认。
```

`agora_start_work` 会尝试解析 Project 和 WorkItem，创建 WorkSession，固定可用的 ContextRevision、WorkflowVersion 和 SkillVersion，并返回下一步动作。

如果任务名称无法可靠识别，AI 应询问用户，而不是悄悄创建一个含糊任务。

### 11.2 获取上下文

`agora_prepare_context` 返回：

- 项目和任务摘要。
- context state 和 freshness。
- key facts 和 source refs。
- 当前 workflow step。
- 适用的已审批 SkillVersion。
- token budget 使用情况。
- next actions。

需要完整参考内容时再调用 `agora_fetch_context_ref`，不要一次加载全部项目资产。

### 11.3 分析、设计和人工确认

开发人员重点审查：

- AI 是否理解真实需求。
- 是否识别影响模块和边界。
- 是否考虑兼容性、迁移、并发、幂等和回滚。
- 是否给出测试策略。
- 是否与已审批上下文冲突。

每一步人工确认后才进入下一步。当前 MCP 流程推进工具缺失，修复前这里无法形成完整真实闭环。

### 11.4 开发和质量证据

AI 在本地修改代码并运行真实测试。QualityEvidence 至少应包含：

- `evidence_type`：如 `local_test`。
- `source`：如 `ai_tool`。
- `status`：`passed`、`failed`、`warning` 或 `unknown`。
- `conclusion`：人能读懂的结论。
- `command`：真实执行命令。
- `output_summary`：关键输出。
- `raw_ref`：CI URL 或安全的证据引用。

示例：

```text
完成开发后运行与本次变更相关的单元测试、集成测试和构建。通过 Agora 记录真实质量证据。任何失败都保留 failed，不要为了结束任务改写成 passed。
```

### 11.5 任务结束

如果本次任务改变了长期项目认知，例如新增模块、改变接口/模型/约束、发现稳定风险或新增测试策略，AI 提交 `task_update` ContextProposal。一次性实现细节不要污染主上下文。

可复用方法可以提交 SkillCandidate。最后调用 `agora_close_work`，保存实现摘要和测试结果。

## 12. Reviewer 操作

### 12.1 Context 审批

进入 Context 页面，检查 stream/head、expected head、branch、commit 证据、结构化内容、source anchors 和 provenance。

并发规则：A、B 同时基于 R1 提案，A 先获批形成 R2 后，B 不能覆盖 R2；B 应进入 `needs_rebase`，重新获取 R2 后再提交。

### 12.2 Skill 审批

Skills 页面中：

- Candidate：AI 提交、尚未批准。
- Approved：已发布正式 SkillVersion。
- Deprecated：不建议新任务使用。

Reviewer 可在发布前编辑名称、版本、摘要、触发条件、输入/输出 schema、instructions 和 risk constraints。审批后生成不可变 SkillVersion，历史版本不能被覆盖。

### 12.3 Security audit

检查 actor、credential kind、action、target、allow/deny、reason 和时间。Agent token 审批应失败并留下 deny；owner/admin/reviewer 的 human token 审批应留下 allow。

当前产品没有团队成员管理入口，因此独立 Reviewer 身份仍需 P7 补齐。

## 13. 项目经理操作

示例：

```text
请通过 Agora 查询 payment-service 当前项目状态。
按任务列出负责人、阶段、状态、阻塞、待审批、质量结论和最近证据。没有证据的项目明确标记未验证。
```

期望调用 `agora_get_project_status`。重点关注：

- WorkItem 数量和阶段分布。
- blocked 任务和原因。
- delivery readiness。
- 待审批 Context/Skill。
- failed 或缺失的 QualityEvidence。
- 外部任务、branch、commit 和 PR/MR 信号。

Web 的 Project status 和 Work items 应与 AI 工具查询使用同一数据口径。

## 14. 质量人员操作

示例：

```text
请通过 Agora 查询 PAY-318 的质量状态。列出本地测试、CI、评审和风险证据，说明状态、命令、结论和来源；缺失维度标记未验证。
```

期望使用 `agora_get_quality_status`，必要时再查询项目状态。

状态含义：

- `passed`：存在真实通过证据。
- `failed`：存在失败证据，不能被 AI 总结覆盖。
- `warning`：存在风险或部分通过。
- `unknown/unverified`：证据不足。

## 15. CI 和仓库信号

当前 P8 接收三类受 CI token 保护的信号：

- CI quality signal。
- repository revision signal。
- pull request signal。

它们可关联 Project/WorkItem、记录 CI evidence、建立外部任务链接、标记 context stale，并生成 refresh proposal 候选。

当前没有完整 provider adapter、webhook signature 和重放保护，因此不能认为已经直接接通 GitHub/GitLab/Gitee。它更像提供给集成系统调用的标准契约。

## 16. Web 页面地图

- **Projects**：创建、查看、归档项目。归档不会立即删除数据。
- **Project Home**：项目入口。旧 server-side initialization 只限本地兼容演示。
- **Work Items**：任务、阶段、WorkSessions、流程、产物、确认和证据。
- **Project Status**：任务、质量维度、阻塞、待审批和交付准备度。
- **Operations Summary**：资产、Context、Skill、Quality、Audit 和 signals 统计。
- **Context**：ContextStream、Revision、Proposal 和审批。
- **Skills**：Skill、版本、候选、审批、运行和废弃。
- **Sessions**：AI 会话、事件、development update 和关联 WorkItem。
- **Assets**：旧知识资产和 source refs，不是客户源码仓库替代品。
- **Security Audit**：敏感审批的 allow/deny 记录。
- **Writebacks**：P0/P1 遗留回写；新路径优先使用 ContextProposal 和 SkillCandidate。

## 17. 认证和权限

### 17.1 三类凭据

- human：Web、人工操作和审批。
- agent：AI 工具工作和提交候选，不能审批团队知识。
- ci：CI 和集成信号。

API 使用 `Authorization: Bearer <token>`。数据库保存 token 的 SHA-256 hash，不保存明文。

### 17.2 ProjectMembership

访问项目需要 ProjectMembership。审批 Context 和 Skill 还要求 human credential，并且角色是 owner、admin 或 reviewer。

### 17.3 当前限制

启动过程只创建一个 `Local Bootstrap User`，human、agent 和 CI credential 都属于它。角色检查骨架存在，但没有用户可操作的成员、邀请、角色、撤销、轮换或登录页面。

不要在重要环境设置 `AGORA_TEST_AUTH_BYPASS=1`。当前代码没有 production guard，误设后会得到全项目 owner 权限。

## 18. 数据库和迁移

### SQLite

优点是无需数据库服务、文件易备份，适合本地试用。缺点是不适合多实例和高并发。

### PostgreSQL

更适合团队共享和并发。示例：

```text
postgresql+psycopg://agora:强密码@数据库地址:5432/agora
```

本次审查中 PostgreSQL 测试因未配置 `AGORA_TEST_POSTGRES_URL` 而跳过。正式使用前必须补测。

### Alembic

Alembic 管理数据库版本。当前 head 是 `20260826_0012`。

升级顺序：备份 -> dry-run -> migrate -> `/ready` -> smoke -> 检查关键治理数据。

## 19. SQLite 备份和恢复

### 在线备份

```bash
.venv/bin/python -m scripts.agora_admin backup-sqlite \
  --database-url "$AGORA_DATABASE_URL" \
  --output .agora/backups/agora-backup.db
```

不要在数据库运行时只复制主文件，因为可能存在 WAL/SHM 状态。

### 恢复演练

```bash
.venv/bin/python -m scripts.agora_admin restore-sqlite \
  --backup .agora/backups/agora-backup.db \
  --database-url 'sqlite+pysqlite:///.agora/agora-restored.db' \
  --yes
```

先恢复到新文件验证，不要直接覆盖唯一副本。用恢复库启动一个不同端口的 API，再检查 `/ready`、项目、ContextRevision、SkillVersion、WorkItem、QualityEvidence 和 SecurityAuditEvent。

## 20. 项目治理导出

```bash
.venv/bin/python -m scripts.agora_admin export-project \
  --database-url "$AGORA_DATABASE_URL" \
  --project-slug payment-service \
  --output-dir .agora/exports/payment-service
```

目录包含 `manifest.json` 和多种 JSONL 文件。JSONL 是“一行一个 JSON 对象”的文本格式，适合审计和流式处理。

导出用于审计、迁移前比对和离线检查，不替代数据库备份。

## 21. 运维命令

### 项目摘要

```bash
.venv/bin/python -m scripts.agora_admin project-summary \
  --database-url "$AGORA_DATABASE_URL" \
  --project-slug payment-service \
  --output .agora/exports/payment-service-summary.json
```

### Outbox 诊断

```bash
.venv/bin/python -m scripts.agora_admin outbox-summary \
  --database-url "$AGORA_DATABASE_URL" \
  --max-attempts 3 \
  --dead-limit 10 \
  --output .agora/exports/outbox-summary.json
```

### 当前手动处理一批 Outbox

```bash
AGORA_DATABASE_URL="$AGORA_DATABASE_URL" \
.venv/bin/python -m apps.workers.main outbox-once \
  --limit 20 \
  --max-attempts 3
```

该命令只处理一批并退出。生产化需要常驻 Worker。

### Retention 预览

```bash
.venv/bin/python -m scripts.agora_admin retention-summary \
  --database-url "$AGORA_DATABASE_URL" \
  --export-dir .agora/exports \
  --export-retention-days 30 \
  --outbox-retention-days 14 \
  --output .agora/exports/retention-summary.json
```

### Retention 清理

检查预览并确认有备份后执行：

```bash
.venv/bin/python -m scripts.agora_admin cleanup-retention \
  --database-url "$AGORA_DATABASE_URL" \
  --export-dir .agora/exports \
  --export-retention-days 30 \
  --outbox-retention-days 14 \
  --yes
```

### 重建索引

```bash
.venv/bin/python -m scripts.agora_admin rebuild-indexes \
  --database-url "$AGORA_DATABASE_URL"
```

### 协议兼容检查

```bash
.venv/bin/python -m scripts.agora_admin compatibility-check \
  --database-url "$AGORA_DATABASE_URL" \
  --output .agora/exports/compatibility.json
```

当前 protocol manifest 错误地缺少 `agora_complete_workflow_step`。修复前不能仅凭 `compatible=true` 判定完整兼容。

## 22. 监控和 Request ID

- `/health`：只表示进程活着。
- `/ready`：检查数据库、schema 和必需配置。
- `/metrics`：Prometheus 风格指标，包括 ready、schema、projects、pending proposals 和 outbox。
- `X-Request-ID`：把 AI 工具、Web、CI 和服务日志串起来排查。

当前 `/ready` 即使 not_ready 仍返回 HTTP 200。因此编排器不能只使用 `curl -f`，还要检查 JSON 中的 `status`；代码后续应改为 HTTP 503。

## 23. Context 并发和 freshness 原理

### 为什么不会互相覆盖

```text
A、B 同时拿到 R1
A 提交 Proposal A
B 提交 Proposal B
Reviewer 先批准 A -> head 变成 R2
再批准 B -> B 的 expected head 仍是 R1
Agora 拒绝覆盖，B needs_rebase
```

这是乐观并发控制：平时不锁住所有人，合并时检查基线是否仍然最新。

### Freshness 怎么判断

- Accepted ContextRevision 记录覆盖的 branch/commit。
- Local Connector 或 CI 上报当前代码版本。
- 两者一致时可以是 current。
- 主分支已前进时是 stale，需要本地 AI 分析差异并提交 refresh proposal。
- Feature branch 未合并时不能直接更新 main stream。

服务端没有客户源码时，只能证明“版本变了”，不能凭空生成正确上下文。真正分析仍由客户 AI 工具完成。

## 24. Workflow 技术原理

核心对象：

- WorkflowDefinition：流程逻辑身份。
- WorkflowVersion：不可变流程版本。
- WorkflowExecution：一个 WorkItem 的权威流程执行。
- WorkflowStepRun：每个步骤的状态。
- WorkArtifact：步骤产物。
- HumanConfirmation：人工确认记录。

一个 WorkItem 只有一个权威 WorkflowExecution。多个 WorkSession 可以贡献材料，但不能各自把项目经理看到的阶段随意改成“已完成”。

## 25. Skill 技术原理

```text
Skill: release-risk-review
  -> SkillVersion 1.0.0 approved
  -> SkillVersion 1.1.0 approved
  -> 旧 WorkSession 仍固定 1.0.0
  -> 新 WorkSession 可以使用 1.1.0
```

ContextPlanner 只应选择 approved 且与任务匹配的 SkillVersion。Candidate 和 deprecated 版本不能自动进入新任务。

## 26. 质量状态技术原理

质量状态由证据聚合：

```text
存在 failed evidence -> failing / blocked
存在 warning -> warning
要求维度都有 passed evidence -> passing
缺少要求证据 -> unverified
```

AI 总结不能把 failed 或 missing evidence 改写成 passed。

## 27. 存储和检索原理

SQL 数据库是事实源。ContextRevision、SkillVersion、WorkItem 和审批关系都在数据库中。索引只是可重建投影。

当前实现：

- FakeKeywordIndex：内存关键词匹配。
- FakeVectorIndex：内存 token overlap，不是真实 embedding 向量检索。

Compose 虽然启动 Qdrant/OpenSearch，API 并未使用。多实例生产前应选择 PostgreSQL FTS/pgvector 或接入真实索引 adapter。

## 28. 常见故障排查

### Web 打不开

```bash
curl http://127.0.0.1:3000/projects
```

确认 `npm run dev` 仍运行，端口未被占用。

### Web 显示 API 请求失败

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

确认 Web 启动时设置了 `AGORA_API_URL` 和 `AGORA_WEB_HUMAN_TOKEN`。

### API 提示 token 缺失

必须同时设置 human 和 agent bootstrap token，且两者不同。

### AI 工具看不到 Agora tools

检查：

- command 是否指向 `.venv/bin/python`。
- args 是否为 `-m apps.mcp.server`。
- cwd 是否为 Agora 仓库。
- `AGORA_API_URL` 是否正确。
- AI 工具是否已重载 MCP。

### AI 调用返回 401

确认 MCP 的 `AGORA_AGENT_TOKEN` 与 API 的 `AGORA_BOOTSTRAP_AGENT_TOKEN` 相同。

### AI 找不到项目

在客户项目目录检查：

```bash
git remote get-url origin
git branch --show-current
git rev-parse HEAD
```

确认 Web 项目的 Git remote 与本地仓库一致。

### 没有 `agora_complete_workflow_step`

这是当前已确认代码缺陷，不是配置错误。先修复审查报告 HIGH-1。

### Proposal 是 needs_rebase

别人已经先更新 head。让 AI 重新 `agora_prepare_context`，基于最新 revision 生成 proposal。

### Outbox 一直 pending

运行一次 `apps.workers.main outbox-once`，然后用 `outbox-summary` 检查。长期方案是常驻 Worker。

### 数据重启后不见

- SQLite：检查不同终端是否使用同一个数据库文件。
- Compose PostgreSQL：当前没有 volume，容器重建可能丢数据，这是已知高优先级问题。

## 29. 发布前黑盒验收

### 服务

- API health/ready/metrics 正常。
- Web 能读取项目。
- MCP 能调用 API。
- Worker 自动运行。

### Developer

- 真实 AI 工具从真实本地项目解析 Project。
- 创建/复用 WorkItem 和 WorkSession。
- 获取正式 Context/Workflow/Skill 版本。
- 完成分析、设计、评审、开发、自测、交付。
- 每一步有产物和人工确认。
- 测试进入 QualityEvidence。
- 任务结束提交必要 proposal/candidate 并 close。

### Reviewer

- Agent 审批被拒绝。
- 独立 Reviewer human 身份审批成功。
- allow/deny 都进入审计。
- Stale proposal 不能覆盖最新 head。

### PM 和 Quality

- AI 与 Web 的任务、阶段、阻塞、审批和质量状态一致。
- Failed evidence 阻塞交付。
- 缺失证据显示 unverified。

### Operations

- PostgreSQL 集成测试通过。
- 容器重建后数据仍存在。
- 备份和恢复演练通过。
- Outbox 重试、死信和并发通过。
- 依赖扫描无 high/critical。
- 非测试环境不能启用 auth bypass。
- 服务端任意路径扫描已禁用或严格限制。

## 30. 后续研发顺序

1. 补回 MCP 工作流推进工具。
2. 修复 Docker 变量、PostgreSQL volume 和常驻 Worker。
3. 禁用共享部署的旧 server-side repository scan。
4. 实现团队成员、角色、个人 token、撤销和轮换。
5. 修复高危前端依赖和 readiness 状态码。
6. 完成真实 PostgreSQL、Compose 和多角色黑盒。
7. 接入真实 Git/CI/task provider adapter。
8. 再决定 PostgreSQL 检索或 Qdrant/OpenSearch。

## 31. 新手记忆版总结

只需先记住六件事：

1. 平时在 AI 工具里工作，Web 用来查看和审批。
2. AI 先 start work，再拿 ContextBundle。
3. 源码留在本地，AI 生成 ContextProposal。
4. AI 只能提交候选，正式 Context 和 Skill 要由人审批。
5. 测试结论必须有 QualityEvidence，没证据就是未验证。
6. 当前还是试点版，修复高优先级问题后才能进入生产-like 验收。
