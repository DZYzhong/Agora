# Agora 使用手册（本地试用版）

> 适用：本机部署栈（Web + API + MCP 通道）。目的：让你以"人"的身份在 Web 审阅/批准，让 AI 工具（Cursor/Codex 等）经 Agora MCP 干活，完整走通一个任务闭环。
> 配套：黑盒检查单 `docs/development/blackbox-checklist.zh-CN.md`、运行手册 `local-production-runbook.zh-CN.md`、部署手册 `deployment-manual.zh-CN.md`。

## 0. 一句话说清 Agora 怎么用

**AI 工具通过 MCP 工具调用 Agora 干活（起会话、准备上下文、交提案、汇报证据、关闭会话）；你通过 Web 做 AI 做不了的事（审阅并批准上下文提案、看项目状态与审计）。** 双方围绕同一个"工作项/会话"协作，全部动作留痕。

## 1. 系统入口与凭据

| 项 | 值 |
|---|---|
| Web（你操作） | http://127.0.0.1:3000 |
| API | https://127.0.0.1:8443 |
| 管理账号 | `admin`，密码在 `/tmp/agora_admin_pass.txt` |
| Agent 令牌 | `infra/.env` → `AGORA_BOOTSTRAP_AGENT_TOKEN`（给 AI 工具通道用，勿外发） |
| 演示项目 | **Agora BB Demo**（slug `agora-bb-demo`，绑定仓库 remote `github.com/dzyzhong/agora-bb-demo`） |
| AI 工作仓库 | `/Users/daniel/Agora-bb-demo`（退款幂等演示任务；origin 已指向上述 remote） |

## 2. 角色与权限速览

| 动作 | 谁做 | 通道 |
|---|---|---|
| start-work / prepare-context / submit-proposal / record-evidence / complete-step / close | **AI 工具**（agent） | MCP |
| 审阅提案、**批准**（含 reauth） | **你**（human，需 admin/owner/reviewer） | Web |
| 看状态、质量证据、会话审计 | 你 | Web（只读） |

> Agent 令牌永远不能批准（A6 矩阵验证点）；批准要求"人类凭据 + 最近一次 reauth"，所以批准前页面会让你重新输一次密码。

## 3. 一次完整闭环（照着做即可）

### 3.1 前提
- 服务在跑：`docker compose ps` 应见 api/web/nginx/postgres/redis/worker healthy；`https://127.0.0.1:8443/ready` 返回 200。
- Web 已用 `admin` 登录（未登录时页面会**静默显示空态**而不是报错——先登录再刷新）。

### 3.2 AI 侧：起活（第 1 段提示词，发给 Cursor 里的 agent）

在配置好 agora MCP 的 Cursor 里，让 agent 粘贴执行（**只准用 agora MCP 工具，禁止直接 HTTP**）：

```
第 1 步 agora_start_work：
  user_message = "AG-200 退款重试幂等修复：分析并修复 agora-bb-demo 仓库中的退款幂等 bug"
  repo_remote = "git@github.com:DZYzhong/agora-bb-demo.git"
  agent_type = "codex"
  idempotency_key = <新 uuid>（协议 1.1 必需）
第 2 步 agora_prepare_context：
  用返回的 session_id，query = "退款重试幂等修复的上下文"，token_budget = 4000，idempotency_key = <新 uuid>
把两步返回 JSON 贴给我。
```

预期：start-work 返回 `session_id`、`next_action = plan_context`；prepare-context 返回 `level = empty` + `provisional = true`（项目还没有已入库 assets，**属预期**）。

### 3.3 AI 侧：本地分析并提交提案（第 2 段提示词）

agent 在 `/Users/daniel/Agora-bb-demo` 改代码、跑测试、提交（git 身份已配置），然后：

```
agora_submit_context_proposal：
  session_id = <上面拿到的>
  type = "task_update"
  title = "AG-200 退款重试幂等修复上下文"
  summary = <一句话证据：改了什么、pytest 前后结果>
  target_branch = "main"
  from_commit_sha = <修复前 commit>
  to_commit_sha = <修复后 commit>
  content = {"modules":[...],"tests":[...]}（结构化摘要，不含服务器本地路径）
  source_anchors = [{"kind":"code","path":"src/payments/refund.py"}]
  provenance = {"generating_tool":"codex"}
  idempotency_key = <新 uuid>
把返回 JSON 贴给我。
```

### 3.4 人侧：审阅并批准（你，Web）

1. 打开项目 **Agora BB Demo**：`http://127.0.0.1:3000/projects/e2309a41ccef4ef8b8940d48987ca3d9`（首页项目列表也能点进去）。
2. 进 **上下文状态** 页（左侧导航或 URL `…/context`），滚到 **上下文提案**，看到琥珀色 `submitted` 卡片 → 点 **查看提案**。
3. 审阅 content / 来源锚点 / provenance，点绿色 **批准提案**（observed head SHA 已预填）。
4. 若跳到 **/reauth**：输 admin 密码完成 reauth，自动回提案页后**再点一次批准**。
5. 预期：提案变 `approved`；上下文页出现 accepted revision、上下文状态变绿。

### 3.5 AI 侧：记录证据、完成步骤、关闭（第 3 段提示词）

```
第 1 步 agora_record_evidence：
  session_id 同上；evidence_type = "local_test"；source = "ai_tool"；status = "passed"
  conclusion = <结论>；command = "pytest tests/test_refund.py"；output_summary = "1 passed in 0.00s"
  idempotency_key = <新 uuid>
第 2 步 agora_complete_workflow_step：
  session_id 同上；step_key = "analysis"（当前步骤）；summary = <证据化小结>；idempotency_key = <新 uuid>
第 3 步 agora_close_work：
  session_id 同上；agent_summary = <小结>；test_result = <测试结果>；idempotency_key = <新 uuid>
把三步返回 JSON 贴给我。
```

### 3.6 人侧：验证（你，Web）

- 项目状态页 `…/status`：应见 delivery readiness **ready**、质量 **passing**、`local_test passed` 证据。
- 会话页 `…/sessions` → 打开该 session：审计含 evidence / 步骤完成 / close 事件。
- 上下文页 `…/context`：提案 `approved`、head revision 已更新。

> 注意：Web 会话页是**只读**的，没有关闭按钮——close 只能由 AI 侧 `agora_close_work` 完成。

## 4. MCP 通道配置（Cursor 示例）

`~/.cursor/mcp.json` 中的 agora 条目（bash 拉起 stdio server）：

```json
{ "mcpServers": { "agora": { "type": "stdio", "command": "bash", "args": ["-lc", "cd <worktree> && SSL_CERT_FILE=$(pwd)/.agora/certs/agora.crt AGORA_API_URL=https://127.0.0.1:8443 AGORA_AGENT_TOKEN=<agent token> exec .venv/bin/python -m apps.mcp.server"] } } }
```

- 修改 connector 代码（如 `apps/mcp/server.py`）后，需**重启 Cursor 窗口**让 stdio server 重新加载。
- 13 个 canonical 工具：`agora_start_work`、`agora_prepare_context`、`agora_fetch_context_ref`、`agora_submit_context_proposal`、`agora_complete_workflow_step`、`agora_submit_skill_candidate`、`agora_suggest_skills`、`agora_record_evidence`、`agora_get_quality_status`、`agora_get_project_status`、`agora_lookup_project_context`、`agora_get_protocol_manifest`、`agora_close_work`。协议当前 1.1，**所有变更类调用都要带 `idempotency_key`**（只读查询如 lookup/get-status 不需要）。

## 4.5 知识引导式工程对话（标准循环）

正常用法不是"上来就起会话"，而是**先查再用、用完反哺**：

1. **查**：工程对话开头调 `agora_lookup_project_context`（repo_remote/项目名 + query，**不建会话**）。返回：`has_accepted_context`、head revision、可检索知识（`knowledge_source_refs`）、适用 skill（含 instructions）、`recommended_action`。
2. **判断**：
   - `use_accepted_context` → 用 `agora_fetch_context_ref` 取已批准知识，在对话里复用；
   - `generate_context` → **告诉用户"本项目还没有 Agora 上下文，需要先生成"**，然后走第 3 步；
   - `use_provisional_context` → 有临时资产未批准，按需继续。
3. **生成并反哺**：`agora_start_work` → 分析本地仓库 → `agora_submit_context_proposal`（initial/refresh/task_update）→ 你在 Web 批准 → 该 head 成为**可检索知识资产**，后续 lookup/prepare 都能查回。
4. **开发中更新**：后续任务先 lookup 复用；改动大时以 `task_update`/`refresh` 提案补充并批准更新。

> 语义：**批准后的已接受上下文才是项目知识**（被检索并返回给 AI）；未批准提案只处于"待审"。Web 上下文页在项目无上下文时会显示引导 CTA。

## 5. Web 页面地图（URL 模板）

| 页面 | URL |
|---|---|
| 项目列表 | http://127.0.0.1:3000 |
| 项目首页 | `/projects/{projectId}` |
| 上下文状态（提案/流/修订） | `/projects/{projectId}/context` |
| 提案审阅/批准 | `/projects/{projectId}/context/proposals/{proposalId}` |
| 项目状态（质量/就绪/证据） | `/projects/{projectId}/status` |
| 会话列表 / 会话审计 | `/projects/{projectId}/sessions`、`…/sessions/{sessionId}` |
| 知识/assets、工作项、成员 | `/projects/{projectId}/knowledge|assets|work-items|members` |

## 6. 常见问题排查

| 现象 | 原因与处理 |
|---|---|
| start-work 返回 404，错误文本只有 "Not Found" | 协议澄清响应：读错误里的 `HTTP response body:`，按 `code`/`next_actions` 处理；`PROJECT_UNRESOLVED` → 补 `repo_remote` 或在 user_message 点名项目名/slug |
| 返回 400 `IDEMPOTENCY_KEY_REQUIRED` | 漏了 `idempotency_key`，补一个 uuid 重试 |
| 404 `Project not found`（字符串 detail） | 项目已解析但该凭据不是项目成员 → 让 admin 在 `…/members` 加人 |
| 403 `CSRF_ORIGIN_REJECTED` / `CSRF_TOKEN_REQUIRED` | 这是给浏览器的防护：从 Web 页面操作（Origin 3000 + CSRF cookie 双提交）；curl 等脚本要走 Bearer agent 通道 |
| 403 `APPROVAL_CREDENTIAL_REQUIRED` | 批准需要 reauth：走 /reauth 输密码后再批 |
| Web 页面"啥也没有" | 大概率未登录/会话过期——页面静默显示空态；先以 admin 登录并刷新 |
| prepare-context `level=empty` | 项目尚无已入库 assets，属预期；AI 在本地分析后提交提案即可 |
| 第二次对同一项目提交相似 task_update 被 `needs_rebase` | 项目上下文流已有 accepted head：新提案必须带 `expected_head_revision_id`（当前 accepted revision）并在其之上推进内容，不能重复已接受内容 |
| close 后 development_update 为空 | connector 观察的是它自己的工作目录（agora 工作树）而非 agent 工作仓库；工作树干净时显示空属正常 |

## 7. 术语表

- **Work Item（工作项）**：一个任务（可带外部 key 如 AG-200）；多个会话可挂同一工作项。
- **Session（会话）**：一次 AI 工具的干活过程（start→…→close），全程留痕。
- **Context Proposal（上下文提案）**：AI 把本地分析结论整理成的待审内容；只有你批准后才成为 **Context Revision（已接受修订）**并推进上下文流 head。
- **Quality Evidence（质量证据）**：AI 上报的测试/检查结论（如 local_test passed），驱动项目质量与 delivery readiness。
- **Workflow Step**：每个工作项的标准化阶段（analysis → design → review → implementation → self_test → delivery），AI 逐步 complete，状态在项目状态页可见。
- **reauth**：批准类高风险动作前要求人类最近重新验证身份。

## 8. 边界与安全（为什么这么设计）

- Agent 只能提交，不能批准；批准必须是"人类 + reauth"。
- summary-only：PR1B/PR1C 之前的临时边界——complete-step 只收摘要，不收未分级工件/审批授权（上传分级与拒绝矩阵是 A6 验收点）。
- 提案 content 不得包含服务器本地路径；connector 只上报本地 git 相对变更与 diff 统计。

## 9. 新用户功能导览（Web 每个页面是干嘛的）

顶部导航（全局）：**项目**（列表/新建/归档）、**用户**（账号管理：建号、激活、禁用、重置密码）、**组织成员**（组织层成员与角色）。

进入任意项目后有 11 个功能页：

| 页面 | 干什么 | 何时用 |
|---|---|---|
| 首页 | 项目概览 + 最近会话 | 每次进来先看这 |
| 工作项 | 任务列表（可带外部编号如 AG-200），会话按工作项聚合 | 看任务进度 |
| 会话 | 一次 AI 干活过程（start→…→close）的列表与审计（只读；close 只能 AI 侧做） | 追溯 AI 做了什么 |
| **上下文** | 核心页：上下文状态/流/**上下文提案**；AI 提交的提案在这里审阅 → reauth → **批准** | A3 批准就在这里 |
| 项目状态 | 质量证据（local_test passed…）、delivery readiness、待批准数 | 验收时看证据 |
| 知识 | 已入库资料总览 | 看项目知识资产 |
| 资产 | 项目材料清单（源码/文档索引） | 材料管理 |
| 技能 | 内置技能版本、运行记录 | 高级用法 |
| 运营摘要 | 操作级汇总 | 运维视角 |
| 安全审计 | 安全事件留痕（审批尝试/拒绝等） | 审计 |
| 写回草稿 | AI 关闭会话生成的回写草稿（供人审阅采纳） | 收尾 |
| 成员 | 项目成员与角色；**批准权 = owner/admin/reviewer**，developer/viewer 不能批 | 加人/改角色 |

主闭环只走一条线：**项目 → AI 起活(会话/工作项) → AI 提交上下文提案 → 你在"上下文"页批准 → "项目状态"页看证据 → "会话"页看审计 → AI 关闭**。

## 10. 新用户自己建项目并跑通（步骤）

1. 准备一个工作仓库（二选一）：
   - 复用演示仓库：`/Users/daniel/Agora-bb-demo`（origin=`git@github.com:DZYzhong/agora-bb-demo.git`，当前是含 AG-200 bug 的初始提交）；
   - 或自己 `git init` 一个仓库并设 origin（远端字符串需与下面项目填的一致）。
2. 新建项目：项目列表页 → 新建项目：名称（如"我的试用项目"）、slug（小写短横线）、**Git 远端填工作仓库的 origin**、默认分支 main → 创建。注意：一个远端只应绑一个活动项目（否则 start-work 解析歧义）。
3. 把 agent 通道身份加入项目：项目 → 成员 → 添加成员 = "Local Bootstrap User"，角色任意（如 reviewer）——不加的话 AI start-work 会 404 "Project not found"。
4. 按 §3 的三段提示词跑闭环，repo_remote 用你仓库的 origin；你在"上下文"页批准、在"项目状态"页验证证据。
