# Agora 新手手册（完整版）

> 适用：第一次接触 Agora 的人。从"这是什么"讲起，带你配好环境、看懂每个页面、自己建一个项目、跑通一次完整的人机协作闭环。
> 环境基线：本机部署栈（Web `http://127.0.0.1:3000`、API `https://127.0.0.1:8443`）。仓库版：`docs/development/agora-usage-manual.zh-CN.md`（含运维细节）。

---

## 目录

1. [Agora 是干什么的](#1-agora-是干什么的)
2. [测试环境配置](#2-测试环境配置)
3. [界面导览：每个页面是干嘛的](#3-界面导览每个页面是干嘛的)
4. [第一次操作：自己建一个项目](#4-第一次操作自己建一个项目)
5. [跑通完整闭环（A1–A5）](#5-跑通完整闭环a1a5)
6. [常见问题排查](#6-常见问题排查)
7. [收尾与下一步](#7-收尾与下一步)

---

## 1. Agora 是干什么的

一个**人机协作的研发治理系统**：AI 工具（Cursor 里的 agent）通过 Agora MCP 通道"干活"，但它的每一步产出——尤其是**上下文提案**——都要经过**你（人）在 Web 上审阅批准**才生效。人和 AI 的动作全部留痕，可追溯、可审计。

它解决三个问题：**AI 干了什么？凭什么信它？谁批准的？**

核心对象一条链：

```
项目（一个仓库/领域）
  → 工作项 + 会话（一次任务 + 一次 AI 干活过程）
  → 上下文提案（AI 提交；你批准后成为"已接受修订"，推进上下文 head）
  → 质量证据（测试/检查结论，驱动项目质量与 delivery readiness）
```

**角色分工（最重要的一句话）**

| 动作 | 谁做 | 在哪 |
|---|---|---|
| 起活 / 准备上下文 / 提交提案 / 报证据 / 完成步骤 / 关闭会话 | **AI 工具（agent）** | Cursor（经 agora MCP 工具） |
| 审阅并**批准**上下文提案（含 reauth） | **你（人）** | Web（需 owner/admin/reviewer 角色） |
| 看状态 / 质量证据 / 会话审计 | 你 | Web（只读） |

> Agent 永远不能批准；批准要求"人类凭据 + 最近一次 reauth"，所以批准前会让你重输一次密码。

---

## 2. 测试环境配置

**推荐在本机栈跑完整闭环**（MCP、演示仓库都已配好）：

| 项 | 值 |
|---|---|
| Web | http://127.0.0.1:3000 |
| API | https://127.0.0.1:8443（`/ready` `/health` `/metrics`） |
| Prometheus | http://127.0.0.1:9091 |
| admin 账号 | 用户名 `admin`；密码文件 `/tmp/agora_admin_pass.txt` |
| Agent token | `.worktrees/agora-p0/infra/.env` → `AGORA_BOOTSTRAP_AGENT_TOKEN` |
| Cursor MCP | `~/.cursor/mcp.json` 的 `agora` 条目（bash 拉起 stdio server，自带 token/证书环境；工具列表应有 12 个 `agora_*`） |
| 演示仓库 | `/Users/daniel/Agora-bb-demo`（origin=`git@github.com:DZYzhong/agora-bb-demo.git`，当前为含 AG-200 退款幂等 bug 的初始提交 `cb547f4`） |
| 项目 | 演示项目 Agora BB Demo 已归档；由你按 §4 新建自己的项目 |

**干净主机（生产式部署，可体验 Web/API）**：172.29.30.128 —— Web `http://172.29.30.128:3000`、API `https://172.29.30.128:8443`；admin 密码文件 `/tmp/c1_admin_pass.txt`。该机还没有项目/演示仓库，完整 AI 闭环建议在本机栈跑。

---

## 3. 界面导览：每个页面是干嘛的

**顶部导航（全局）**

- **项目**：所有项目；新建项目也在这里（列表页有"新建项目"）。
- **用户**：账号管理——建号、激活、禁用、重置密码、签发/吊销凭据。
- **组织成员**：组织层成员与角色。

**进入一个项目后有 11 个功能页**

| 页面 | 干什么 | 什么时候用 |
|---|---|---|
| 首页 | 项目概览 + 最近会话 | 每次进来先看 |
| 工作项 | 任务列表（可带外部编号如 AG-200） | 看任务进度 |
| 会话 | AI 干活过程（start→…→close）的列表与审计；**只读**（关闭只能 AI 侧做） | 追溯 AI 动作 |
| **上下文** | ⭐核心页：上下文状态/流/**上下文提案**；AI 的提案在这里审阅 → reauth → **批准** | 闭环的第 3 步 |
| 项目状态 | 质量证据（local_test passed…）、delivery readiness、待批准数 | 验收看证据 |
| 知识 | 已入库资料总览 | 看项目资产 |
| 资产 | 项目材料清单（源码/文档索引） | 材料管理 |
| 技能 | 内置技能版本与运行记录 | 高级用法 |
| 运营摘要 | 操作级指标 | 运维视角 |
| 安全审计 | 审批尝试/拒绝等安全事件留痕 | 审计 |
| 写回草稿 | AI 关闭会话生成的回写草稿，供人审阅采纳 | 收尾 |
| 成员 | 项目成员与角色；**批准权=owner/admin/reviewer**，developer/viewer 不能批 | 加人/改角色 |

> 你真正要走的闭环只有一条线：**项目 → AI 起活 → AI 提交提案 → 你在"上下文"页批准 → "项目状态"页看证据 → "会话"页看审计 → AI 关闭**。

---

## 4. 第一次操作：自己建一个项目

### 4.1 建项目（Web）

1. 顶部 **项目** → **新建项目**（URL：`http://127.0.0.1:3000/projects/create`）。
2. 填写：
   - 名称：如 `我的试用项目`
   - 标识 slug：如 `my-trial`（小写短横线）
   - **Git 远端**：填 `git@github.com:DZYzhong/agora-bb-demo.git`（要与你的工作仓库 origin 一致；解析只做字符串归一化匹配，仓库不需真实可达）
   - 默认分支：`main`
3. 创建 → 回到项目列表能看到它（active）。

> 注意：**一个 Git 远端只应绑一个活动项目**，否则 AI start-work 解析会歧义（旧演示项目已归档，可直接绑定演示远端）。

### 4.2 把 agent 通道身份加进项目（必须，否则 AI start-work 报 404 "Project not found"）

- 进入你的项目 → **成员** → 添加成员：用户选 **Local Bootstrap User**（Cursor MCP 通道背后的身份），角色选 `reviewer`（或 owner）→ 添加。

### 4.3 可选：体验账号管理

- **用户**页 → 新建用户 → 拿到一次性激活链接/令牌 → 激活并设密码 → 用新账号登录，体验"另一个用户"的视角；可再试 禁用/重置密码/签发凭据。

---

## 5. 跑通完整闭环（A1–A5）

三段提示词粘贴到 **Cursor**（agent 只准用 `agora_*` MCP 工具，禁止直接 HTTP）；批准与验证在 **Web**。

### 第 1 段：起活（AI 侧）

```
1) agora_start_work：
   user_message="AG-200 退款重试幂等修复：分析并修复我工作仓库中的退款幂等 bug"
   repo_remote="git@github.com:DZYzhong/agora-bb-demo.git"
   agent_type="codex"
   idempotency_key=<新 uuid>          （协议 1.1 必需，每次调用都换新）
2) agora_prepare_context：
   用第 1 步返回的 session_id；query="退款重试幂等修复的上下文"；token_budget=4000；idempotency_key=<新 uuid>
把两步返回 JSON 贴给我（session_id / next_action）。
```

预期：返回 `session_id`、`next_action=plan_context`；prepare 返回 `level=empty` + `provisional`（新项目还没有已入库资产，**正常**）。

### 第 2 段：本地分析并提交提案（AI 侧）

让 agent 在 `/Users/daniel/Agora-bb-demo` 里改代码（`src/payments/refund.py`）、跑 `pytest tests/test_refund.py`、`git commit`，然后：

```
agora_submit_context_proposal：
  session_id = <第 1 步的>
  type = "task_update"
  title = "AG-200 退款重试幂等修复上下文"
  summary = <一句话：改了什么、pytest 修复前 1 failed → 修复后 1 passed>
  target_branch = "main"
  from_commit_sha = <修复前 commit>
  to_commit_sha = <修复后 commit>
  content = {"modules":[...],"tests":[...]}      （结构化摘要，禁止服务器本地路径）
  source_anchors = [{"kind":"code","path":"src/payments/refund.py"}]
  provenance = {"generating_tool":"codex"}
  idempotency_key = <新 uuid>
把返回 JSON 贴给我（proposal id / status）。
```

### 第 3 步：审阅并批准（你，Web）

1. 打开你的项目（首页项目列表点进去）。
2. 进 **上下文** 页（`…/context`）→ 滚到 **上下文提案** → 看到琥珀色 `submitted` 卡片 → **查看提案**。
3. 审阅 content / 来源锚点 / provenance，点绿色 **批准提案**。
4. 若跳到 `/reauth`：输 admin 密码完成 reauth → 自动回到提案页 → **再点一次批准**。
5. 预期：提案变 `approved`、上下文状态变绿、出现 accepted revision。

### 第 4 段：证据 + 完成步骤 + 关闭（AI 侧）

```
1) agora_record_evidence：
   session_id 同上；evidence_type="local_test"；source="ai_tool"；status="passed"
   conclusion=<结论>；command="pytest tests/test_refund.py"；output_summary="1 passed in 0.00s"
   idempotency_key=<新 uuid>
2) agora_complete_workflow_step：
   session_id 同上；step_key="analysis"；summary=<证据化小结>；idempotency_key=<新 uuid>
3) agora_close_work：
   session_id 同上；agent_summary=<小结>；test_result=<测试结果>；idempotency_key=<新 uuid>
把三步返回 JSON 贴给我。
```

### 第 5 步：验证（你，Web）

- 你的项目 → **项目状态**（`…/status`）：应见 delivery readiness **ready**、质量 **passing**、`local_test passed` 证据。
- **会话**页打开该 session：审计含 evidence / 步骤完成 / close 事件。

---

## 6. 常见问题排查

| 现象 | 原因与处理 |
|---|---|
| start-work 返回 404 + `PROJECT_UNRESOLVED` | 项目没解析到：补 `repo_remote`（=项目 Git 远端），或在 user_message 里点名项目名/slug |
| 404 "Project not found"（字符串 detail） | 项目已解析但该凭据不是成员 → 成员页把 Local Bootstrap User 加进项目 |
| 400 `IDEMPOTENCY_KEY_REQUIRED` | 漏了 `idempotency_key`：每次调用都补一个新 uuid |
| 403 `APPROVAL_CREDENTIAL_REQUIRED` | 批准需要 reauth：跳 `/reauth` 输密码后回到提案页再批一次 |
| 403 `PROJECT_ROLE_REQUIRED` | 当前角色不在 {owner, admin, reviewer}：用有批准权的账号（admin/owner/reviewer） |
| Web 页面"啥也没有" | 大概率未登录/会话过期——页面静默显示空态：重新登录再刷新 |
| prepare-context `level=empty` | 项目尚无已入库资产，属预期；AI 本地分析后提交提案即可 |
| 同项目第二次相似提案被 `needs_rebase` | 项目上下文流已有 accepted head：新提案要带 `expected_head_revision_id`（当前 accepted revision）并在其之上推进内容，不能重复已接受内容 |
| 工具报错文本里只有 "Not Found" | 读错误中 `HTTP response body:` 之后的内容，按 `code`/`next_actions` 处理 |

---

## 7. 收尾与下一步

- 跑通后把关键结果发我（session_id、提案 id、approve 后状态、evidence），帮你归档进黑盒验收记录。
- 想深入了解：仓库文档
  - 使用手册（运维向）：`docs/development/agora-usage-manual.zh-CN.md`
  - 部署手册：`docs/development/deployment-manual.zh-CN.md`
  - 运行手册：`docs/development/local-production-runbook.zh-CN.md`
  - 黑盒检查单与证据：`docs/development/blackbox-checklist.zh-CN.md`、`docs/superpowers/plans/2026-09-03-production-readiness-report-draft.md`
