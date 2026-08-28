# Agora P0-P9 代码审查报告

> 审查日期：2026-08-28
>
> 审查基线：`1d5b356`（`codex/agora-p0`）
>
> 审查方式：源码审查、完整 Python 测试、Web 生产构建、依赖审计、真实 API/Web 本地运行与页面检查。

## 1. 结论

当前仓库已经实现了较完整的领域骨架和试点闭环，包括项目、WorkItem、WorkSession、Workflow、Context、Skill、QualityEvidence、集成信号、审计和运维命令。但是，**目前不能判定为“P0-P9 全部完成并具备生产上线条件”**。

主要原因：

- 真实 AI 工具主流程缺少 MCP `agora_complete_workflow_step`，标准工作流不能通过当前 stdio MCP 完整推进。
- 现有 Docker Compose 的 Web 和 Local Connector 无法正确连接 API，PostgreSQL 数据也没有持久化卷。
- 旧的服务端仓库初始化接口允许读取服务端任意可访问目录，与“源码保留在客户本地”的架构原则冲突。
- P7 的多人、成员、身份生命周期和企业认证没有实现；当前只有一个 Local Bootstrap User。
- Outbox 只有手动单次执行命令，没有常驻 Worker。
- 运行时仍使用进程内 FakeKeywordIndex/FakeVectorIndex，Compose 中的 Qdrant/OpenSearch 没有接入。
- 当前依赖审计发现 3 个 high severity 前端依赖问题。
- PostgreSQL 集成测试在本次审查中因没有配置测试数据库而跳过。

因此，建议把当前版本定义为：

> **功能较完整的本地/单团队试点版，进入 P0-P9 收尾修复和生产化验收阶段。**

## 2. 审查发现

### CRITICAL-1：服务端仓库初始化可读取服务端任意可访问目录

证据：

- `apps/api/routers/projects.py:200` 暴露 `POST /projects/{project_id}/initialize-local`。
- `apps/api/routers/projects.py:218-223` 将调用方提交的 `repo_path` 直接保存。
- `apps/api/routers/projects.py:355` 将该字符串直接构造成 `Path`。
- `packages/integrations/git/analyzer.py:130-167` 使用 `os.walk` 遍历目录。
- `packages/integrations/git/analyzer.py:17-34` 会读取 `.py`、`.ts`、`.yaml`、`.xml` 等源码和配置文件。
- `packages/core/models.py:61` 将绝对路径持久化到数据库。
- `apps/web/app/projects/[projectId]/page.tsx:54` 在 Web 中展示绝对路径。

触发场景：

1. Agora 部署为团队共享服务。
2. 持有人类凭据的项目成员提交 `/app`、挂载目录或其他服务账号可读路径。
3. API 扫描这些文件并将内容保存成项目资产。
4. 项目成员通过 Assets 页面/API 读取内容。

影响：

- 可能泄露 Agora 服务端源码、配置或挂载进容器的客户文件。
- 明确违反“客户源码和本地绝对路径默认不上传 Agora”的产品与技术架构。
- Web 仍把该旧能力作为项目首页主入口，用户很容易误用。

建议：

- 共享部署默认删除或禁用 `initialize-local`。
- 本地扫描只能发生在 AI Tool/Local Connector 进程中。
- 如果保留管理员导入能力，必须使用独立 Worker、明确 allowlist 根目录、realpath 边界校验、专用管理员权限和完整审计。
- 不在服务端保存或展示客户端绝对路径，只保存清理后的相对 source anchor、hash 和 workspace fingerprint。

### HIGH-1：真实 MCP 未暴露工作流步骤完成工具

证据：

- `apps/mcp/server.py:31-179` 的 `TOOLS` 列表没有 `agora_complete_workflow_step`。
- `apps/mcp/server.py:206-362` 的 `_dispatch` 没有该工具分支。
- `packages/core/services/protocol.py:7-19` 的 canonical tool manifest 也没有该工具。
- `apps/mcp/tools.py:73-94` 虽然存在 Python 内部 facade 方法，但 stdio MCP 不会暴露它。
- `tests/unit/mcp/test_stdio_server.py:10-22` 的期望列表反而固定了这个遗漏。
- P4 路线和黑盒文档明确要求 AI 工具调用 `agora_complete_workflow_step`。

实际验证：

```text
has_complete_workflow_step = False
manifest_has_complete_workflow_step = False
```

影响：

- AI 工具可以开始任务和准备上下文，但不能通过真实 MCP 提交固定产物、人工确认并推进分析/设计/评审/开发/自测/交付流程。
- P4 的核心验收闭环被阻断。

建议：

- 将工具 schema、dispatch、protocol manifest 和 stdio MCP 测试同时补齐。
- 增加真实 MCP 进程级测试，不能只测试 `apps/mcp/tools.py` 的内部 facade。

### HIGH-2：Docker Compose 的 Web 和 Local Connector API 地址变量错误

证据：

- `infra/docker-compose.yml:28` 和 `:42` 设置 `AGORA_API_BASE_URL=http://api:8000`。
- Web 实际读取 `NEXT_PUBLIC_AGORA_API_URL`：`apps/web/lib/api.ts:1`。
- MCP 实际读取 `AGORA_API_URL`：`apps/mcp/server.py:14`。

影响：

- Web 容器回退到 `http://localhost:8000`，该地址在 Web 容器内指向 Web 容器自身，而不是 API 容器。
- Local Connector 容器同样回退到自身的 `127.0.0.1:8000`。
- Compose 宣称的 API/Web/Connector 联合部署不能工作。

建议：

- Web 服务设置实际读取的服务端 API 地址变量，并为构建期/运行期配置建立单一命名约定。
- Local Connector 设置 `AGORA_API_URL=http://api:8000`。
- 增加 Compose 启动后的真实 smoke 测试，验证 Web 页面能读取项目、MCP 能调用 API。

### HIGH-3：Compose PostgreSQL 没有持久化卷

证据：

- `infra/docker-compose.yml:47-59` 定义 PostgreSQL，但没有任何 `volumes` 挂载。
- 文件末尾也没有 named volume 声明。

影响：

- 执行 `docker compose down` 后重新创建容器可能丢失全部 Agora 项目、上下文、任务、技能、审批和审计数据。
- 与 P9 的“可恢复、可升级、数据持久化”目标冲突。

建议：

- 为 `/var/lib/postgresql/data` 添加 named volume。
- 明确备份、恢复、升级前备份和恢复演练流程。
- 增加“写入数据 -> 重建容器 -> 数据仍存在”的部署测试。

### HIGH-4：测试认证绕过没有生产环境防护

证据：

- `apps/api/dependencies.py:55-56` 只要 `AGORA_TEST_AUTH_BYPASS=1` 就启用绕过。
- `packages/core/auth.py:48-56` 绕过身份被视为 human/owner。
- `packages/core/auth.py:119-127` 绕过身份自动通过所有项目成员检查并取得 owner 角色。
- `apps/api/routers/health.py:84-98` 在绕过开启时还会减少必需配置检查，没有禁止 production-like 环境启用。

影响：

- 生产环境误设一个变量即可让未认证调用方获得全部项目 owner 权限。

建议：

- 仅当 `AGORA_ENV=test` 且数据库是隔离测试库时允许绕过。
- 其他环境检测到该变量必须拒绝启动。
- `/ready` 明确暴露安全配置错误并返回 HTTP 503。

### HIGH-5：Outbox 没有常驻 Worker，Compose 也没有 Worker 服务

证据：

- `apps/workers/main.py:9-22` 只支持 `outbox-once`，处理一批后进程退出。
- `apps/workers/workflows/outbox.py:11-21` 只提供单批处理函数。
- `infra/docker-compose.yml` 没有 worker 服务。
- 文档只在 P3 黑盒中要求人工运行一次 worker。

影响：

- 上下文 head 变化后的异步事件会持续积压，除非运维人员手动执行命令。
- 重试、死信和投影更新不具备“自动运行”能力。

建议：

- 增加常驻 Worker 循环、优雅退出、退避、并发锁和可观测性。
- Compose/生产部署中将 Worker 作为必需服务。
- 增加进程级重启、重复投递和多 Worker 竞争测试。

### HIGH-6：真实团队身份和角色管理尚未实现

证据：

- `packages/core/repositories/identities.py:41-54` 只创建 `Local Bootstrap User`。
- `packages/core/auth.py:73-98` 把 human、agent 和 CI token 都绑定到这个 bootstrap user。
- API 共 48 个路由，但没有用户、成员、邀请、角色分配、凭据撤销/轮换或登录路由。
- Web 没有团队成员或权限管理页面。
- 路线文档 P7 自身仍标记为 `In progress`。

影响：

- 无法真实建立开发人员 A/B/C、Reviewer、项目经理、质量人员等不同身份。
- 不能在产品界面配置角色、离职禁用、token 生命周期和审批责任人。
- 当前 RBAC 测试主要通过测试代码直接插入 User/Membership，用户无法通过产品操作完成同样配置。

建议：

- 将 P7 重新定义为未完成阶段。
- 先实现最小团队管理：成员、项目角色、个人 human/agent token、吊销与轮换；再接入 OIDC/SSO。
- 所有角色黑盒测试必须使用不同真实身份，而不是一个 bootstrap user 模拟所有角色。

### HIGH-7：前端生产依赖存在 high severity 漏洞

验证命令：

```bash
npm audit --omit=dev --registry=https://registry.npmjs.org --json
```

结果：

- 3 个 high severity vulnerability 条目。
- `next@15.5.23` 依赖 `postcss@8.4.31` 和 `sharp@0.34.5`。
- 审计报告指出 PostCSS 路径读取/信息泄露问题和 sharp/libvips 问题。

影响：

- 生产 Web 镜像包含已知高危依赖。

建议：

- 评估升级到已修复的 Next.js 版本，并重新执行构建、回归和 `npm audit`。
- 增加依赖安全扫描到 CI，high/critical 默认阻断发布。

### MEDIUM-1：Qdrant/OpenSearch 容器存在，但运行时只使用 Fake 内存索引

证据：

- `apps/api/dependencies.py:12-13,59-66` 固定创建 FakeKeywordIndex/FakeVectorIndex。
- `packages/storage/opensearch/fake.py:16-84` 和 `packages/storage/qdrant/fake.py:16-69` 都是 Python 内存列表。
- `infra/docker-compose.yml:66-78` 启动 Qdrant/OpenSearch，但 API 没有使用对应 URL。

影响：

- 多 API 进程之间索引状态不一致。
- 每次启动需要从数据库全量重建，数据增大后启动时间和内存不可控。
- Compose 额外消耗资源却不提供实际能力。

建议：

- 小团队首版可先使用 PostgreSQL FTS/pgvector，或明确保持单进程并删除未使用容器。
- 只有在真实检索评测证明需要时再接 OpenSearch/Qdrant。

### MEDIUM-2：`/ready` 在 not_ready 时仍返回 HTTP 200

证据：

- `apps/api/routers/health.py:19-40` 只在 JSON 中写 `status=not_ready`，没有返回 503。
- `infra/docker-compose.yml:16` 使用 `curl -f`，只看 HTTP 状态。

影响：

- 编排器可能把配置错误或数据库错误的实例标记为 healthy。

建议：

- readiness 失败时返回 HTTP 503。
- 同时保留结构化 checks，供 `smoke` 和监控读取。

### MEDIUM-3：Web 缺少统一错误、加载和权限状态

证据：

- `apps/web/app` 下没有 `error.tsx`、`loading.tsx`、`unauthorized.tsx` 或 `forbidden.tsx`。
- `apps/web/app/projects/create/route.ts:16-24` 的创建错误未捕获，用户会得到框架错误页。
- `apps/web/app/projects/[projectId]/page.tsx:34-38` 静默吞掉初始化历史读取错误并显示为空。
- `apps/web/lib/api.ts:43-52` 不能展示 API 返回的结构化 `detail.message`。

影响：

- 新手很难区分 token 错误、服务未启动、权限不足、数据库故障和业务校验失败。

建议：

- 增加全局和路由级错误/加载状态。
- 解析结构化错误码与 message，并提供可执行的恢复建议。
- 不要把后端错误伪装成“没有数据”。

### MEDIUM-4：路线状态和实现状态互相矛盾

证据：

- Roadmap 顶部称“P0-P9 are implemented”。
- 同一文件 P2 标记 `Next`。
- P7 标记 `In progress`。
- P8/P9 的 exit criteria 包含真实 provider adapter、后台 stale detection、离线队列、Worker、对象存储、容器化 Worker 等尚未实现能力。

影响：

- 后续聊天丢失后，会从错误状态恢复研发，继续把未完成能力当成已完成。
- 使用手册和黑盒测试容易承诺不存在的功能。

建议：

- Roadmap 顶部改为“功能切片已实现，阶段退出条件尚未全部满足”。
- 每个 P 阶段分别维护 `implemented / black-box passed / exit criteria passed` 三种状态。

## 3. 测试与验证结果

### 已通过

```text
Python full suite: 255 passed, 2 skipped, 62.30s
Web production build: passed (Next.js 15.5.23)
Python compileall: passed
pip check: passed
git diff --check: passed
Local API /health: HTTP 200, X-Request-ID present
Local Web /projects: rendered successfully
Local project create + sample repository initialization: passed
```

### 未完成或受环境限制

- PostgreSQL 两个集成测试跳过：`AGORA_TEST_POSTGRES_URL is not configured`。
- 本机没有 `docker` 命令，因此没有执行真实 Compose build/up/smoke。
- 四个并行审查代理因外部额度限制中止，最终报告不引用其未完成结果。
- 没有执行压力、长时间运行、多 API worker、多 Outbox worker 或真实 SSO 测试。
- 没有执行真实 GitHub/GitLab/Gitee webhook 签名和 provider adapter 测试，因为当前代码没有这些 adapter。

## 4. 建议修复顺序

### R1：先恢复真实主流程

1. 补回 `agora_complete_workflow_step` 的 MCP schema、dispatch、manifest 和进程级测试。
2. 修复 Compose API 地址变量。
3. 增加常驻 Worker 和 Compose worker 服务。
4. 完成真实 AI 工具端到端黑盒：开始任务 -> 上下文 -> 全工作流 -> 证据 -> proposal -> 审批 -> close。

### R2：封住数据和安全风险

1. 禁用共享部署的服务端 `initialize-local` 任意路径扫描。
2. 增加 auth bypass 生产保护。
3. 给 PostgreSQL 增加持久化卷并完成备份恢复演练。
4. 升级高危前端依赖。

### R3：补齐真实团队能力

1. 用户、成员、角色和个人凭据管理。
2. token 撤销、轮换、过期和 Web 登录会话。
3. Reviewer/PM/Quality/Developer 不同身份黑盒。
4. OIDC/SSO 和企业生命周期。

### R4：完成生产化和安静自动化

1. 真实 Git/CI/task provider adapter、签名和重放保护。
2. Local Connector 离线队列和同步诊断。
3. PostgreSQL 检索或真实索引 adapter。
4. 多进程、并发、性能、升级和灾难恢复验收。

## 5. 发布判定

当前建议：

- 本地开发、自测、产品演示：**可以**。
- 单机、可信小团队、明确知道限制的试点：**修复 HIGH-1 至 HIGH-5 后再进行**。
- 共享服务器或生产环境：**暂不建议**。
- 对外宣称 P0-P9 全部完成：**不建议，应以各阶段 exit criteria 的真实通过记录为准**。
