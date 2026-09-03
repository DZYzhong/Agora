# Agora 本机生产运行手册

> 适用：在单台本机（macOS + colima docker 或任意 docker 主机）以 production 模式部署 Agora 并日常运维。
>
> 基线：2026-09-02 生产就绪整改后的 `codex/agora-p0`（A/B/C/D 块）。
>
> 身份模式：Web 治理界面使用 **Cookie 会话 + 重新认证**；MCP/AI 工具使用 **Agent Bearer Token**；审批仅允许已重新认证的 Web 会话或一次性 grant（Personal/Agent/CI token 一律拒绝）。

## 1. 首次部署

### 1.1 前置

- Docker（本机用 colima：`colima start --cpu 4 --memory 4 --disk 40`）
- `docker-compose` 可用；`docker compose` 需插件（brew 版用 `docker-compose`）
- `infra/.env`（本机 secrets，gitignored）：首次部署用
  `scripts/deploy_local.sh` 自动生成随机 bootstrap tokens，或手工 `cp infra/env.production.example` 参考后创建。**绝不要**让 `.env.example` 里的占位值（`replace-with-*`）进入容器——它们会在启动时被当成真实凭据写进数据库（2026-09-02 已修复并加入回归测试）。

### 1.2 生成 TLS 自签证书（生产替换为托管证书）

`scripts/deploy_local.sh` 会自动生成；手工方式：

```bash
mkdir -p .agora/certs
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout .agora/certs/agora.key -out .agora/certs/agora.crt \
  -days 365 -subj "/CN=localhost"
```

### 1.3 启动全栈

一键（推荐）：

```bash
scripts/deploy_local.sh            # 生成 secrets/证书 → up -d --build → 等待 /ready
scripts/deploy_local.sh --bootstrap-admin <username> <强密码>
```

或手工：

```bash
cd .worktrees/agora-p0   # 或仓库根
docker-compose -f infra/docker-compose.yml up -d --build
```

服务与入口（2026-09-02 实测拓扑）：

| 服务 | 说明 | 本机入口 |
|---|---|---|
| `nginx` | API 反向代理（TLS、限流、1MiB 上限） | `https://127.0.0.1:8443`（API）；8080 http→https 跳转 |
| `api` | FastAPI（health/ready/metrics） | 容器内 `api:8000`；宿主 8000 可能被其它本地栈占用，**以 nginx 8443 为准** |
| `web` | Next.js 治理界面（cookie 会话） | `http://127.0.0.1:3000`（colima 端口转发直达 web 容器） |
| `worker` | 常驻 outbox worker | — |
| `postgres` | PostgreSQL（命名卷持久化） | 容器内 5432 |
| `migrate` | 一次性迁移任务（api 启动前完成） | — |

**拓扑说明**：web 容器内服务端调用走 `http://api:8000`（compose 内网）；浏览器只访问 `:3000` 的 Web。nginx 当前承载 API 的 TLS 外部入口（`/ready`、`/metrics`、`/auth/*` 等全部 API 路由）。Web 与 API 统一经 nginx 反代对外（仅暴露 443/80）见 §8 进阶。

### 1.4 引导 Admin（一次性）

```bash
# 在 api 容器内执行（或经 deploy 脚本）
docker-compose -f infra/docker-compose.yml exec api \
  python -m scripts.agora_admin bootstrap-admin \
  --database-url "postgresql+psycopg://agora:agora@postgres:5432/agora" \
  --org-id local-org --admin-username admin --admin-password '<强密码>'
```

成功后记录输出；重复执行会确定性失败（`ADMIN_ALREADY_BOOTSTRAPPED`）。强密码建议随机生成并妥善保管（`openssl rand -base64 18`）。

### 1.5 创建成员用户

Admin 登录 Web（`http://127.0.0.1:3000/login`，注意不是 8443——那是 API 的 TLS 入口）→ Users 页创建用户 → **将一次性 activation token 通过企业已认证渠道**交付 → 用户访问激活（`/users/activate`）设置密码后即可登录。

## 2. 日常使用闭环

1. **AI 工具**：配置 Agora MCP（stdio），`AGORA_AGENT_TOKEN` 指向 API（compose 已把 `infra/.env` 的 agent secret 注入 local-connector）；开始任务（start-work）→ 本地分析 → 提交 ContextProposal/SkillCandidate/development update（summary-only；高风险上传需审批人 grant）。
2. **Reviewer/PM**：Web 登录 → Pending 队列（`http://127.0.0.1:3000/projects/<id>/pending`）审阅待批上下文提案与技能候选 → 点审批会要求**重新输入密码（reauth）**→ 通过后形成 Accepted ContextRevision / SkillVersion。
3. **质量/交付**：Project status 页查看质量证据、blockers、交付就绪；Knowledge 页查看团队知识积累与版本历史。
4. **经验沉淀**：development update writeback 草稿 → Accept 入库为 asset。

## 3. 备份与恢复（加密）

```bash
# 备份（加密；passphrase 走环境变量，不进 argv/日志）
AGORA_BACKUP_PASSPHRASE='<强口令>' docker-compose -f infra/docker-compose.yml exec postgres \
  sh -c 'pg_dump -U agora -d agora | openssl enc -aes-256-cbc -pbkdf2 -pass env:AGORA_BACKUP_PASSPHRASE -out /backup/agora-$(date +%F).enc'   # 需挂载卷

# 本机 SQLite 试运行版：
AGORA_BACKUP_PASSPHRASE='<口令>' .venv/bin/python -m scripts.agora_admin backup-sqlite \
  --database-url sqlite+pysqlite:///.agora/agora.db --output .agora/backup.enc
AGORA_BACKUP_PASSPHRASE='<口令>' .venv/bin/python -m scripts.agora_admin restore-sqlite \
  --backup .agora/backup.enc --database-url sqlite+pysqlite:///.agora/agora.db --yes
```

备份文件离开数据库主机前必须加密（AES-256-CBC / PBKDF2）；口令由运维托管，至少每年轮换。

## 4. 升级

```bash
git pull   # 或切到新版本提交
docker-compose -f infra/docker-compose.yml build api web worker
docker-compose -f infra/docker-compose.yml up -d --no-deps migrate   # 先跑迁移
docker-compose -f infra/docker-compose.yml up -d --no-deps api worker web nginx
docker-compose -f infra/docker-compose.yml exec api python -m scripts.agora_admin compatibility-check
```

原则：先备份 → 迁移一次 → 再滚动替换；`/ready` 在 schema 落后时返回 503，避免旧进程写新结构。

## 5. Worker 运维

- 常驻 `worker` 服务处理 outbox；事件为租约式领取（崩溃后 5 分钟自动回收），支持重试与死信（超过 max-attempts 标记 dead）。
- 手动单批处理：

```bash
docker-compose -f infra/docker-compose.yml exec worker \
  python -m apps.workers.main outbox-once --limit 50
```

- 诊断：`scripts.agora_admin outbox-summary`（积压/死信）、`cleanup-retention`（清理终态）。

## 6. 健康与日志

```bash
curl -k https://127.0.0.1:8443/ready    # ready=200；任何检查失败=503
curl -k https://127.0.0.1:8443/metrics   # Prometheus 文本
docker-compose -f infra/docker-compose.yml logs -f api worker web
```

日志已脱敏（Authorization/cookie/remote 凭据/secret 值替换为 `***REDACTED***`）。

## 7. 安全要点

- 登录/重新认证按用户+来源限流；会话 Cookie `Secure/HttpOnly/SameSite=Strict`，空闲 30 分钟、最长 12 小时。
- 审批/高风险确认仅允许**已重新认证的 Web 会话**；Agent/CI/Personal token 无法审批。
- 上传服务端二次校验并分级：高风险（excerpt/secret/越限/豁免）需要审批人 grant，客户端不能自报降级。
- 请求体上限 1MiB；CORS 仅允许 `AGORA_ALLOWED_ORIGINS` 配置的源。
- 服务端本地仓库初始化在生产不可用（404）——源码留在 AI 工具本地。

## 8. 进阶（生产建议，超出本机演示）

- 用托管 TLS 证书替换自签；把 web 与 api 统一经 nginx 反代对外（仅暴露 443/80）。
- PostgreSQL 数据卷静态加密、异地/离主机加密备份；备份周期满足 RPO≤24h，恢复演练计时满足 RTO≤4h。
- 依赖审计接 CI：`python -m scripts.dependency_audit`（pip-audit + npm audit --omit=dev）与 `npm run lint`。
- 干净主机全量恢复演练 + 多 API 实例前先完成 PR4（PostgreSQL FTS 替换进程内检索索引）。

## 9. 黑盒/验证文档索引

- 运维就绪黑盒：`p9-operations-readiness-blackbox.zh-CN.md`
- PR1A 运行时/MCP：`pr1a-runtime-mcp-blackbox.zh-CN.md`
- PR2 可恢复部署：`p2-real-ai-tool-blackbox.zh-CN.md`、`pr1a-runtime-mcp-blackbox.zh-CN.md`
- P3-P8 治理域黑盒：`p3-context-governance-blackbox.zh-CN.md` … `p8-ci-quality-signal-blackbox.zh-CN.md`
- 执行清单与 roadmap：`docs/superpowers/plans/2026-09-02-production-ready-web-deploy.md`、`docs/superpowers/plans/2026-08-28-agora-production-readiness-implementation.md`

## 10. 2026-09-02 本机部署实测记录（evidence）

- 全栈 `docker compose up`：api(healthy) / web / worker / nginx / postgres(healthy) / redis；`/ready` 200（configuration/database/schema 全 ok）。
- 引导：`bootstrap-admin` 建 admin（org local-org）；Web 会话登录 /reauth 200；创建成员 `pm` + activation（30 分钟单次）+ 登录成功。
- 业务冒烟：建项目、项目主页/状态/pending/knowledge 等页面 200 渲染；审批路由拒绝矩阵实测——无权限主体 `Project not found` 404、已 reauth admin 到达提案查找 404（权限分支正确）。
- 部署中抓出并修复两个 SQLite 掩盖的 PostgreSQL-only 缺陷（回归测试已补入 `tests/integration/test_p2_postgres.py`）：
  1. `security_audit_events.actor_credential_id` 外键指向 `credentials.id`，但 Web 会话/一次性 grant 主体的 id 在 `web_sessions`/grants 表 → PG 审计写入 500。修复：迁移 `20260902_0017` 去掉该外键（主体身份本就多态，kind 列已区分）。
  2. 跨后端 schema fingerprint 差异：PG 布尔默认值 `false` vs SQLite `0`、部分唯一索引谓词 `= ANY (ARRAY[...])` vs `IN (...)`、`::TYPE` 强制转换、以及按表主键推导列级 `primary_key` —— 已在 `schema_manager._schema_signature` 归一化，PG 与 canonical SQLite 指纹一致。
- 环境安全修复：compose 不再把 `.env.example` 占位 token（`replace-with-*`）注入容器（原先会被当真实凭据写入 DB）；真实随机 secrets 走 gitignored 的 `infra/.env`；web 不再携带静态占位 Bearer（改为纯 cookie 会话）。
- PG 专属测试（隔离 postgres 实例）：rollback / idempotency 唯一性 / audit 多态 actor / fingerprint 一致 —— 4 passed。

## 11. 2026-09-03 加密备份恢复演练（本机 DR 可做部分）

- 命令：`pg_dump -U agora -d agora | openssl enc -aes-256-cbc -pbkdf2`（passphrase 走 env）→ 101,136 字节加密文件；解密后灌入 scratch PostgreSQL。
- 结果：0 SQL 错误；`alembic_version=20260902_0018`；users=3 / projects=1 与源库一致；**恢复后 schema fingerprint 与 canonical 一致**（`ensure_schema` 可启动）。
- 演练发现并修复：pg_dump/restore 会把部分唯一索引谓词改写为逐字面量加括号 `ARRAY[('OWNER')::text,...]` → 归一化新增单字面量去括号（`schema_manager`），回归单测 `test_normalized_predicate_unwraps_dump_wrapped_in_list_literals`。
- 挂起：干净主机全量恢复 + RPO≤24h/RTO≤4h 实测（需真实环境）。
