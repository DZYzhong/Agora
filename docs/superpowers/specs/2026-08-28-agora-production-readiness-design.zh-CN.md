# Agora 首个生产版本就绪设计

> 文档状态：设计方向已确认，独立规范评审通过，待用户文档复核
>
> 确认日期：2026-08-28
>
> 目标环境：企业内网、单组织、Docker Compose
>
> 产品依据：`docs/superpowers/specs/2026-08-14-agora-product-functional-design.zh-CN.md`
>
> 架构依据：`docs/superpowers/specs/2026-08-14-agora-technical-architecture-design.zh-CN.md`
>
> 问题基线：`docs/reviews/2026-08-28-agora-p0-p9-code-review.zh-CN.md`

## 1. 目标

把当前“本地开发和受控试点版”加固为首个可用于真实软件研发团队的生产版本。首版必须让开发人员、评审人员、项目经理、质量人员和管理员通过真实身份，在自己的 AI 工具与 Agora Web 中完成可追溯、可恢复、权限隔离的协作流程。

生产就绪不是“功能页面能打开”，而是同时满足：

- 源码默认只在开发人员本地或 CI runner 中读取。
- AI 工具能够通过 MCP 完成完整标准工作流。
- PostgreSQL 数据、异步任务和索引在服务重启后可恢复。
- 每个成员、AI 工具和 CI 凭据可识别、可授权、可吊销。
- 上下文变更有 Git 基线、并发保护、审批和 freshness 状态。
- 系统具备部署、备份、恢复、监控、升级和故障处理手册。
- 自动化测试与真实多角色黑盒验收均通过。

## 2. 首版边界

### 2.1 包含

- 一个 Organization。
- 多个 Project，每个项目首版关联一个主 Git 仓库。
- Developer、Reviewer/Tech Lead、Project Manager、Quality、Admin、Viewer 角色。
- Docker Compose 单机部署，可在企业内网服务器运行。
- PostgreSQL 作为事实源、全文检索和可重建投影存储。
- API、Web、MCP/Local Connector、常驻 Worker 和反向代理。
- Personal、Agent、CI 三类凭据及生命周期管理。
- 本地 AI 工具驱动的上下文生成、工作流推进和任务收尾。
- 审计、备份恢复、健康检查、指标和基础告警。

### 2.2 不包含

- 公网多租户 SaaS。
- Kubernetes、高可用多节点或跨地域容灾。
- 强制接入企业 OIDC/SSO；首版先提供可审计的本地身份与 Token，OIDC 作为后续增强。
- Agora 服务端克隆、扫描或保存完整客户源码。
- Qdrant、OpenSearch、Neo4j 等独立检索基础设施。
- 中央 LLM Gateway；模型继续由客户本地 AI 工具提供。
- 自动绕过人工审批或自动发布 AI 生成的团队资产。

## 3. 方案选择

采用“渐进式生产加固”：保留现有模块化单体、领域模型、FastAPI、Next.js、SQLAlchemy、Alembic 和 Harness 边界，按安全风险和依赖顺序修复。

没有采用基础设施优先方案，因为它会先固化尚不完整的 MCP 和身份模型。没有采用核心重写方案，因为当前领域骨架和测试具有复用价值，全面重写会显著增加回归风险。

## 4. 生产拓扑

```text
开发人员电脑 / CI Runner
┌─────────────────────────────────────────────────────┐
│ AI Tool                                             │
│  ├─ 读取本地源码、文档、Git 和未提交变更             │
│  └─ Agora Local Connector / MCP stdio               │
│      ├─ Repository detector / Git observer          │
│      ├─ Ignore / secret scan / redaction            │
│      ├─ Context schema and source anchors           │
│      └─ Authenticated HTTPS client / retry queue    │
└──────────────────────┬──────────────────────────────┘
                       │ HTTPS
企业内网               ▼
┌─────────────────────────────────────────────────────┐
│ Reverse Proxy                                       │
│  ├─ TLS termination                                 │
│  ├─ request size / timeout / security headers       │
│  └─ /api -> API, / -> Web                           │
├─────────────────────────────────────────────────────┤
│ Agora API                                           │
│  ├─ AuthN/AuthZ / rate limit / idempotency          │
│  ├─ Harness Coordinator                             │
│  └─ Project/Work/Context/Skill/Quality/Audit        │
├──────────────────────┬──────────────────────────────┤
│ Agora Web            │ Persistent Worker           │
│ governance/audit     │ outbox/retry/projections     │
├──────────────────────┴──────────────────────────────┤
│ PostgreSQL                                          │
│ facts + FTS + outbox + audit + schema migrations    │
└─────────────────────────────────────────────────────┘
```

每个容器使用固定版本镜像。PostgreSQL 数据目录挂载在企业批准的加密磁盘/文件系统上；备份先写加密暂存目录，再复制到独立主机、企业对象存储或受控 NFS，不能与数据库只存在于同一磁盘。API 和 Worker 使用同一应用镜像与数据库 schema，启动前执行单实例迁移任务。

## 5. 组件设计

### 5.1 Local Connector 和 MCP

Local Connector 是源码访问边界。它可以读取本地目录，但上传前必须：

- 确认目录属于 Git 工作树。
- 规范化 Git remote 并删除用户名、密码和 Token。
- 应用 `.gitignore`、Agora ignore 和默认敏感目录规则。
- 执行 secret pattern 检查和大小限制。
- 将绝对路径替换为 repository-relative path。
- 附带 commit SHA、branch、dirty 状态和匿名 workspace fingerprint。
- 只上传结构化上下文、必要引用、产物和证据。

MCP stdio server 必须发布一份规范化工具清单。生产协议升级为 `1.1`，同时声明兼容 `1.0`；`1.0` 的 canonical 名称保持不变，`1.1` 只新增完整工作流工具：

- `agora_start_work`
- `agora_prepare_context`
- `agora_fetch_context_ref`
- `agora_complete_workflow_step`
- `agora_submit_context_proposal`
- `agora_submit_skill_candidate`
- `agora_suggest_skills`
- `agora_record_evidence`
- `agora_get_project_status`
- `agora_get_quality_status`
- `agora_get_protocol_manifest`
- `agora_close_work`

工具 schema、dispatch、协议 manifest 和进程级测试必须来自同一份定义，禁止各自维护后漂移。`1.0` 客户端可以使用原有工具，但 manifest 必须明确其不能执行标准工作流；要求完整工作流的服务端响应 `upgrade_required` 和最低 Connector 版本。所有写命令支持 idempotency key，错误必须返回 AI 工具可执行的恢复动作。

### 5.2 API 和 Harness

API 是唯一远程业务入口。Harness 是 AI 工具的任务级门面，不直接绕过领域服务操作数据库。

生产环境彻底禁用服务端任意路径 `initialize-local`。若保留开发辅助接口，只能在明确的 local/test profile 中启用，并限制在配置好的 fixture root；生产 profile 检测到启用配置必须拒绝启动。

一次工作会话遵循：

```text
authenticate
-> resolve project and repository identity
-> resolve/create WorkItem
-> create/resume WorkSession
-> pin accepted context/workflow/skill versions
-> prepare token-budgeted ContextBundle
-> complete workflow steps with artifacts and human confirmations
-> record quality evidence
-> submit context/skill candidates
-> close session and enqueue writeback/outbox work
```

服务端拒绝跳步、错误角色确认、过期 expected revision、重复副作用和未授权项目访问。

### 5.3 身份、角色和凭据

首版采用本地管理员引导，不依赖测试 bootstrap bypass：

- 首次启动通过一次性 CLI 创建 Organization 和 Admin；数据库唯一约束和事务锁保证并发只成功一次，成功后 bootstrap secret 立即失效并留下审计事件。
- 用户密码使用 Argon2id 哈希；参数写入哈希串并支持登录时升级，数据库不保存明文或可逆密码。
- Admin 在 Web 创建或停用 User、OrganizationMembership 和 ProjectMembership。新用户获得随机、单次、30 分钟有效的 activation credential；它通过企业已认证的独立沟通渠道交付，只保存哈希。用户首次使用时必须设置密码，成功、过期、重发或撤销后旧 credential 均不可再用并写审计事件。
- 凭据只在创建时显示明文，数据库只保存不可逆哈希、前缀、scope、过期时间和最后使用时间。
- Personal Token 代表人；Agent Token 代表某个人授权的 AI 工具；CI Token 代表项目自动化。
- Token 可轮换、吊销和过期；停用成员立即使其全部凭据失效。
- 权限由 principal type、organization membership、project membership、role 和 action policy 共同判定。
- 所有身份、权限和凭据变更写 AuditEvent，敏感值不得进入日志。

认证协议严格分离：

- Web：用户名/密码换取服务端 session；session ID 只放 `Secure`、`HttpOnly`、`SameSite=Strict` Cookie，空闲 30 分钟、最长 12 小时，退出、停用用户和安全事件可立即吊销。所有状态变更使用 CSRF token 和 Origin 校验。登录与密码重置按用户和来源限流。
- MCP/AI 工具：只接受 Bearer Agent Token，不使用 Web Cookie；Token 必须绑定 user、organization、允许项目和 scope。
- CI：只接受 Bearer CI Token，必须绑定单个项目和允许的 integration/evidence scope。
- 管理员恢复：由服务器 CLI 在本机控制台生成一次性、短时恢复码；使用后强制重设密码并吊销旧 session，不提供匿名邮件重置。
- Agent、CI 和 Personal Token 永远不能执行 Approval 或高风险 HumanConfirmation，也不能管理成员、签发高权限凭据、修改角色、审批安全例外或执行备份恢复。Approval 和高风险 HumanConfirmation 必须来自已重新认证的 Web human session，或由该 session 签发的一次性短时 approval grant；grant 绑定 human user、object ID、payload digest、decision、policy version 和五分钟内的 expiry，使用一次即失效。
- 普通工作流确认不是 Approval。具备 `human_prompt` capability 的 AI 工具可以用 Agent Token 记录用户在本地 AI 界面作出的低风险 workflow acknowledgment，必须提交 step ID、prompt digest、用户选择、local interaction ID 和时间。它只证明“工具声明用户确认了这一步”，不能批准 Context、Skill、安全例外或质量豁免；项目策略可以把任意步骤升级为高风险 grant 流程。
- 普通用户忘记密码时，由 Admin 在 Web 签发一次性、15 分钟有效的 reset credential，并通过企业已认证的独立渠道交付。签发时吊销该用户现有 session；成功、过期、重发或撤销后旧 credential 不可重用。签发者、接收者、使用和失败尝试全部审计。

关键拒绝矩阵：

| Principal | 允许 | 必须拒绝 |
|---|---|---|
| Web human session | 角色授权的管理、查询和审批 | 未授权项目、过期/无 CSRF 的写操作 |
| Personal Token | 角色授权的 API 查询和个人低风险自动化 | Approval、高风险 HumanConfirmation、Web session 管理、签发高权限 Token |
| Agent Token | Harness、产物、证据、proposal、策略允许的低风险 workflow acknowledgment | Approval、高风险 HumanConfirmation、成员/角色/凭据管理 |
| CI Token | 指定项目的 revision/quality signal | Approval、任意 HumanConfirmation、资产审批、跨项目访问 |
| Test bypass | 仅隔离测试数据库 | development/production 启动 |

首版角色权限：

| 角色 | 主要权限 |
|---|---|
| Admin | 组织、成员、项目、凭据、策略和审计管理 |
| Project Manager | 项目成员、WorkItem、Workflow 选择、状态和流程审批 |
| Reviewer / Tech Lead | 上下文、技术产物、Skill 和高风险技术审批 |
| Developer | 执行任务、提交产物、证据、上下文和 Skill 候选 |
| Quality | 查看质量、提交质量结论、要求补充证据 |
| Viewer | 只读已授权项目的已批准资产和状态 |

### 5.4 PostgreSQL、检索和迁移

PostgreSQL 是首版唯一必需数据基础设施：

- 业务对象、审批、审计、Outbox 和幂等记录存数据库。
- 通过 `tsvector`/GIN 完成首版关键词和全文检索。
- 向量召回不是首版生产门槛；保留 adapter 接口但不启动未使用容器。
- 索引是可重建投影，数据库事实不依赖进程内 Fake index。
- Alembic 迁移必须支持从上一发布版本升级到当前版本。
- 发布前自动备份，迁移失败不启动新 API。

持久数据清单：

| 数据 | 事实源与限制 | 备份范围 |
|---|---|---|
| 项目、身份、任务、审批、审计、Outbox | PostgreSQL 关系表 | 必须 |
| ContextRevision、ContextBundle、Skill 和结构化产物 | PostgreSQL JSON/text；单对象默认 1 MiB，项目策略可下调 | 必须 |
| 测试日志和附件 | PostgreSQL bytea/text；单附件 10 MiB，总量受项目 quota 限制 | 必须 |
| 搜索投影 | PostgreSQL FTS，可由事实表重建 | 可重建但随数据库备份 |
| Local Connector 离线队列 | 开发人员本机加密文件，默认最多 100 条或 100 MiB、最长保留 7 天 | 不属于 Agora 服务端备份，由 Connector 诊断和清理 |
| 配置与密钥 | 受控环境文件/企业 secret store，不进入数据库备份 | 单独加密托管和恢复演练 |

超过数据库内容限制的完整源码、构建产物和大型日志不得上传首版 Agora；只上传摘要、哈希和外部受控引用。后续引入对象存储时需单独设计生命周期和备份，不在本阶段暗中写本地文件系统。

SQLite 仅用于开发和单元测试，不属于生产支持矩阵。

### 5.5 Worker 和异步处理

Worker 以常驻循环处理 Outbox：

- 有界批量领取和数据库锁，避免多 Worker 重复处理。
- 成功后标记完成；失败记录次数、最后错误和下一次重试时间。
- 指数退避并设置最大尝试次数，超过阈值进入 dead-letter 状态。
- 支持 SIGTERM 优雅退出，不领取新任务并完成当前事务。
- 暴露 backlog、success、retry、dead-letter 和处理时延指标。
- 运维人员可以在 Web 或 CLI 查看、重试和审计失败任务。

### 5.6 Web

Web 是治理与运维入口，应提供：

- 用户名/密码登录、Cookie session 建立与退出。
- 项目、成员、角色和凭据管理。
- WorkItem、WorkflowExecution、人工确认和任务产物审计。
- ContextProposal、SkillCandidate 和例外审批。
- 项目状态、质量状态、过期上下文和待处理事项。
- Outbox、集成、安全配置、备份状态和审计查询。
- 统一 loading、empty、unauthorized、forbidden 和 error 状态。

Web 不提供服务器本地目录输入框，不承担代码扫描，也不吞掉 API 错误。

## 6. 上下文 freshness 与多人并发

Accepted ContextRevision 记录：

- repository identity。
- analyzed commit SHA 或 commit range。
- source anchors。
- schema、生成工具和模型信息。
- parent revision 和 expected head revision。
- 创建者、审批者和时间。

每个 Accepted ContextRevision 和 observed head 都绑定 `(organization, project, repository, ContextStream, branch)`。feature branch 的 RevisionSignal 只影响同 branch stream；只有已验证 merge evidence 才能影响默认分支 stream。

服务端不持有仓库，因此不能自行声称两个 commit 的祖先关系。受信任的 Local Connector、签名 CI 或 Git provider 提交 `RevisionSignal`，至少包含 repository identity、ContextStream/branch、commit SHA、previous SHA、changed path 摘要、event ID、source ID、来源时间和 source-scoped 单调序号；可选包含由本地 Git 计算的 ancestor/merge relationship。服务端验证 Token scope、webhook 签名、事件唯一性、时间窗口和来源内序号后保存关系证据。

每个 source 独立排序，不创建跨 source 的虚假全局序号。项目策略声明 authoritative source 优先级（默认 provider webhook > CI > Local Connector）。更新 observed head 使用 previous-SHA compare-and-set；低优先级来源与当前权威 head 冲突时不覆盖，只记录待协调证据。

Git/CI RevisionSignal 到达后，服务端基于已验证证据判断：

- 相同 commit：fresh。
- 可信证据证明 accepted baseline 是新 commit 祖先：potentially_stale，并按 changed paths 计算影响。
- 无法比较或历史改写：unknown，需要人工/AI 重新分析。
- 两个 proposal 基于同一旧 head：后审批者收到 conflict，不允许静默覆盖。

乱序事件不会回退对应 branch observed head；重复 event ID 幂等返回；force-push、来源序号缺口和冲突关系证据一律使对应 stream 进入 `unknown` 并生成诊断事件，不污染其他 branch。只有新的 Accepted ContextRevision 覆盖该 stream 当前 observed head 后才能恢复 `fresh`。

Agora 只发出需要本地重新分析的动作。开发人员的 AI 工具在下一次 `start_work` 时自动感知 `potentially_stale` 或 `unknown` 状态，扫描本地代码并提交 proposal，用户无需手工维护“是否最新”。

## 7. 安全设计

### 7.1 环境 profile

`AGORA_ENV` 只能是 `test`、`development` 或 `production`。生产 profile：

- 禁止 auth bypass、fixture scanner 和调试凭据。
- 缺少 Token pepper、数据库密码、公开 URL 或 TLS 配置时 readiness 失败。
- 启动日志输出配置项名称和状态，不输出秘密值。

### 7.2 API 防护

- HTTPS only，反向代理传递可信 request ID。
- JSON 和上传内容设大小上限。
- 对认证、查询和写命令设置不同限流。
- 统一结构化错误码，不暴露 traceback、SQL 或本地路径。
- CORS 只允许配置的 Web origin。
- 所有写操作校验 scope、project membership 和幂等键。
- Webhook 校验签名、时间窗口和 replay key。

客户端清洗不是唯一安全边界。组织和项目策略必须定义允许的 payload kind、repository-relative path pattern、MIME/type、单项与总大小、是否允许源码 excerpt、secret rule 和需要人工确认的内容类别。API 对每次上传再次执行 schema、路径规范化、内容类型、大小、control character、secret pattern 和 policy version 校验；拒绝绝对路径、`..`、凭据化 remote、未知 payload kind 和过期 Connector protocol。恶意或旧版 Connector 不能依赖客户端自律获得例外。

上传确认按服务端策略计算风险等级，客户端不能自报降级：

- 只包含允许的结构化摘要、哈希、测试结论和无 excerpt 的 source anchor 时，可以使用 §5.3 的低风险 Agent workflow acknowledgment，必须携带 step ID、prompt digest、用户选择、local interaction ID、payload digest、policy version 和时间。
- 包含任何源码/文档 excerpt、secret-rule 例外、通常禁止的路径或类型、超过默认限制的内容、策略 override 或质量豁免时，必须使用 §5.3 的 Web reauthentication/high-risk approval grant，绑定 object/session、payload digest、decision、policy version 和 expiry。
- API 以实际 payload 和当前 policy 重新计算 tier；confirmation 类型或字段与 tier 不匹配、摘要变化、grant 过期或尝试降级时一律拒绝并记录安全审计事件。

### 7.3 数据和日志

- Token、密码和 webhook secret 只存哈希或加密密文。
- PostgreSQL 数据卷和本机暂存区必须位于企业批准的静态加密存储上；磁盘密钥由 Operations 托管，恢复密钥由 Admin 分权保管，至少每年轮换并在月度恢复演练中验证。生产 readiness 配置检查和发布清单必须确认加密卷标识，未满足时不得批准生产启动。
- 日志脱敏 Authorization、cookie、remote credential 和疑似 secret。
- 审计事件保存 actor、action、target、result、request ID 和前后状态摘要。
- 备份加密并限制文件权限。
- 项目归档不等于删除；删除遵循明确保留策略并留下审计记录。

## 8. 可用性、恢复和可观测性

### 8.1 首版服务目标

- 内网服务月可用性目标：99.5%，不含计划维护。
- API 非 AI 业务请求 p95 小于 500 ms（50 并发、基准数据集下）。
- `start_work`/`prepare_context` p95 小于 2 s，不包含本地 AI 分析时间。
- RPO 不超过 24 小时，RTO 不超过 4 小时。
- 审计、审批和 Accepted ContextRevision 不允许静默丢失。

这些是验收目标，不是当前能力声明。验收环境必须记录数据量、机器规格和测量方法。

### 8.2 健康检查

- `/health` 只表示进程存活，始终不访问外部依赖。
- `/ready` 检查数据库、迁移版本和生产必需配置；失败返回 HTTP 503。
- Worker 有独立 heartbeat 和 backlog 指标。
- Compose healthcheck 使用 readiness，而不是只检查端口。

### 8.3 备份恢复

- 每日 PostgreSQL 逻辑备份，至少保留 7 天；发布前额外备份。
- 备份使用独立 backup encryption key 加密并生成校验和，完成后复制到主机外独立介质；只有本机 named volume 的备份视为失败。
- 数据库备份、配置模板、密钥恢复材料和版本 manifest 共同组成恢复集，密钥由 Admin 与 Operations 分权托管。
- 删除台账以完整性保护的 append-only 文件同步到独立备份介质，保留时间至少为最长备份保留期加 30 天；台账签名密钥与数据库恢复点分开托管。
- 每月至少一次在全新主机、全新数据库和空 Compose 环境完成恢复演练。
- 恢复必须先进入隔离网络，运行迁移检查、对象/记录数与抽样哈希校验、索引重建，并重放独立删除台账；确认没有数据复活后才能开放服务，再执行多角色 smoke test并实际记录 RPO/RTO。
- 操作手册记录备份位置、校验和、镜像 digest、迁移版本、恢复命令、责任人和演练结果。

## 9. 错误处理和降级

- Agora 不可用时，Local Connector 可以保存有上限、加密的待同步命令；不能显示为已同步。队列密钥存操作系统 Keychain/credential vault，队列文件仅 owner 可读写，并绑定 organization、project 和 principal。Connector 提供查看元数据和安全删除命令；损坏或超过 7 天的条目隔离后删除。Token 过期、吊销或 principal 改变时不得自动改用新 Token 重放，必须由重新认证的原用户确认。
- 幂等写请求网络超时后可以安全重试。
- Worker 故障不阻止只读查询，但 readiness/metrics 必须暴露 backlog 风险。
- 检索投影故障时退化到 PostgreSQL 基础查询，并标记结果可能不完整。
- 上下文冲突必须由 Reviewer/Tech Lead 处理，禁止 last-write-wins。
- 数据库不可用时 API readiness 503，写操作不接受内存暂存。

## 10. 测试策略

所有行为变更按 TDD 实施：先编写能证明缺口的失败测试，再写最小实现。

测试分层：

- Unit：权限矩阵、Token/activation 哈希、MCP schema、freshness、离线队列、退避和状态机。
- Integration：FastAPI + PostgreSQL、Alembic 升级、事务边界、Outbox 竞争、审计。
- Process：MCP stdio、Worker SIGTERM、Compose 服务发现和环境变量。
- E2E：AI 工具 -> MCP -> API -> PostgreSQL -> Worker -> Web 审批。
- Security：越权、凭据渠道审批拒绝、普通/高风险确认边界、activation/reset 重用、Token 吊销、路径注入、secret redaction、重放、限流、队列窃取和损坏。
- Recovery：容器重建、数据库备份恢复、失败迁移回滚和索引重建。
- Performance：基准数据下的 API、ContextBundle 和 Worker backlog。

CI 发布门槛：

- 全部自动化测试通过，无意外 skip。
- PostgreSQL 集成测试必须运行。
- Web lint/typecheck/build 通过。
- Python compile、依赖一致性和迁移检查通过。
- 生产依赖无 Critical 已知漏洞。High 默认阻断；只有 Admin、Security Owner 和 Product Owner 共同批准、设置不超过 30 天到期日并落实补偿控制后，才允许隔离试运行，正式生产发布仍要求未关闭 High 为零。
- 镜像构建、Compose config、启动和 smoke test 通过。
- `git diff --check` 和文档一致性检查通过。

## 11. 实施阶段与退出标准

### PR1：核心安全与 MCP 闭环

- 生产禁用服务端本地目录扫描。
- auth bypass 仅允许隔离 test profile。
- MCP 工具定义单一来源并补齐工作流步骤。
- 协议升级到 1.1，1.0 兼容、升级提示和最低 Connector 版本测试通过。
- 服务端上传 policy、payload 二次校验、登录/session/CSRF 和 principal 拒绝矩阵落地。
- 修复生产依赖 Critical/High 漏洞并完成日志秘密脱敏。
- 真实 AI 工具完成 start -> workflow -> evidence -> proposal -> close。
- 路径、权限、协议和进程级测试通过。

### PR2：可恢复部署

- Compose 变量统一，PostgreSQL 和备份卷持久化。
- 增加 migration job、常驻 Worker、优雅退出、重试和 dead-letter。
- readiness 503、Worker heartbeat 和关键指标可用。
- TLS 反向代理、请求大小限制和基础限流启用。
- 容器重建数据不丢失，异机加密备份与全新主机恢复演练通过。

### PR3：团队身份与权限

- Admin 引导、用户、组织成员和项目成员生命周期可操作。
- 用户 activation/reset 的创建、过期、重发、撤销、session 吊销和单次使用测试通过。
- Personal/Agent/CI Token 可创建、轮换、过期和吊销。
- 权限矩阵与审计覆盖全部关键命令。
- Developer、Reviewer、PM、Quality 使用不同身份完成黑盒。

### PR4：上下文一致性与真实检索

- Local Connector 上传清洗后的 observation 和 proposal。
- Accepted ContextRevision 记录 commit baseline 和 expected head。
- RevisionSignal 自动产生 fresh/potentially_stale/unknown 状态。
- RevisionSignal 的签名、多分支、多来源优先级、乱序、重放、force-push 和 potentially_stale/unknown 状态测试通过。
- 并发 proposal 冲突不会静默覆盖。
- PostgreSQL FTS 取代 Fake 运行时索引并可重建。

### PR5：运维与纵深安全验收

- 持续扫描确认没有新引入的 high/critical 依赖漏洞。
- 验证 PR1/PR2 的 TLS、限流、大小限制和日志脱敏，并补齐安全响应头与攻击场景回归。
- 指标、结构化日志、告警和操作页面可用。
- 发布、升级、回滚、备份、恢复和事件处理手册完成。
- 安全与性能验收达到本设计目标。

### PR6：生产级验收

- 真实 PostgreSQL、Docker Compose 和真实 AI 工具环境。
- 至少三名开发身份并行执行不同 WorkItem。
- Reviewer、PM、Quality 完成各自查询和审批流程。
- 完成重启、网络中断、Worker 积压、Token 吊销和恢复演练。
- 所有证据写入生产就绪报告，Critical/High 未关闭项为零。

## 12. 发布判定

阶段状态分别记录：`implemented`、`automated verified`、`black-box passed`、`exit criteria passed`。实现代码不等于阶段完成。

允许进入真实数据内部试运行的最低条件：PR1、PR2、PR3 全部 exit criteria passed，且 PR4 的上下文并发与 freshness 主链路通过。TLS、日志脱敏、服务端上传限制、请求大小限制、基础限流以及 Critical/High 生产依赖修复已经前移到 PR1/PR2，任何一项缺失时只能在隔离环境使用非敏感合成数据。

允许正式生产发布的条件：

- PR1-PR6 全部 exit criteria passed。
- Critical/High 未关闭缺陷为零。
- PostgreSQL 恢复演练和真实多角色黑盒通过。
- 运维责任人确认部署、监控、备份和事件响应手册。
- 发布版本、镜像 digest、迁移版本和验收证据被永久记录。

## 13. 验收证据矩阵

每个 exit criterion 必须在路线文档中关联稳定测试 ID、自动化命令或签字证据。最低矩阵如下：

| Gate | 可重复证据 | 通过阈值 |
|---|---|---|
| PR1 协议 | `PR1-MCP-*` 进程测试与真实 AI 工具记录 | canonical tools 100% 可调用，旧版获得明确升级响应 |
| PR1 安全 | `PR1-AUTH-*`、`PR1-UPLOAD-*` | 凭据渠道拒绝矩阵、普通/高风险确认、activation/reset 和恶意 payload 用例 100% 通过，无 Critical/High 依赖 |
| PR2 部署 | `PR2-COMPOSE-*`、`PR2-WORKER-*` | 服务健康、SIGTERM、重试和 dead-letter 全部通过 |
| PR2 恢复 | `PR2-DR-*` | 加密卷验证、全新主机恢复和 delete -> old backup -> no resurrection 通过，RPO <= 24h、RTO <= 4h |
| PR3 权限 | `PR3-RBAC-*` | 每个 principal × action 允许/拒绝清单 100% 通过 |
| PR4 上下文 | `PR4-FRESH-*`、`PR4-CONFLICT-*` | 多分支/多来源、乱序、重放、force-push、并发覆盖无错误状态迁移 |
| PR5 性能 | `PR5-PERF-*` | 50 并发、固定基准数据下达到 §8.1 p95，连续 30 分钟无错误率劣化 |
| PR5 运维 | `PR5-OPS-*` | 指标、告警、升级、回滚和事件演练全部有时间戳证据 |
| PR6 黑盒 | `PR6-E2E-*` | 全部角色、故障和恢复场景通过，无 Critical/High 未关闭缺陷 |

## 14. 责任、保留和升级策略

责任矩阵：

| 活动 | 执行 | 批准/负责 |
|---|---|---|
| 发布、迁移、回滚 | Operations | Admin |
| 备份与月度恢复演练 | Operations | Admin |
| 安全漏洞和临时例外 | Security Owner | Admin + Product Owner |
| 生产事件响应 | Operations | Admin，涉及数据时通知 Project Manager |
| Context/Skill 审批 | Reviewer / Tech Lead | Project Manager 监督 SLA |
| 成员、角色和凭据 | Admin | Admin，变更自动审计 |
| 数据删除请求 | Admin 执行 | Project Manager + Data Owner 批准 |

默认保留：审计事件和审批记录 365 天，已接受上下文与 Skill 在项目存续期间保留，普通 session/event 180 天，失败 Outbox 90 天，备份 7 天。组织可以延长但不能低于法务或安全要求。删除先从在线事实源生成 tombstone，再按备份到期自然清除；恢复旧备份后必须重放 deletion ledger，禁止已删除数据重新上线。

数据库变更采用 expand/contract：先增加兼容字段/表并双读写，部署兼容应用并回填，再在后续版本删除旧结构。每次发布在迁移前设置回滚决策点。不可逆迁移必须先完成全新主机恢复验证；失败时恢复发布前备份和上一镜像，不承诺对不可逆 schema 执行 SQL down migration。

## 15. 文档与回溯规则

每次开发批次必须同步长期路线文档，记录：

- 完成的阶段和任务。
- 变更文件与提交号。
- RED 测试、GREEN 测试和完整回归结果。
- 实际黑盒步骤和用户结果。
- 已知限制、遗留风险和下一步。

聊天记录丢失后，以本设计、实施计划、长期路线和最新生产就绪报告恢复状态，不以聊天中的“完成”表述作为证据。
