# Agora 生产就绪状态报告（草稿，PR6 前身）

> 生成：2026-09-03（本机部署栈，证据版）。最终 PR6 报告需真实 AI 工具黑盒与多角色场景后定稿（§8 待办）。
> 仓库：`codex/agora-p0` @ `8614aa4`（分支领先 origin 212，未 push）

## 1. 发布基线（本机，2026-09-03 终版）

- 提交：`codex/agora-p0` @ `90e0cc8`（远端已同步）
- 镜像 ID（本地构建）：api `39aeca153c1f`、web `22de6f467449`、worker `4c0c0e5e24e5`、local-connector `98240b7b8ba3`；运行镜像 postgres `f1c3376c26f2`、redis `71da9275c5f3`、nginx `65645c7bb6a0`、prometheus `f6639335d34a`
- Schema revision：`20260902_0019`（PostgreSQL；PG↔SQLite fingerprint 一致；FTS 工件白名单排除）
- 测试基线：全量 pytest（SQLite）**548 passed**（曾 1 次偶发 1 failed，两次重跑未复现）、PG 专属 7、web-config 54；`tsc`/`next build`/依赖审计 0
- 验收：`scripts/verify_production.sh` → **PRODUCTION ACCEPTANCE PASS**（7/7）；备份快照 `agora-20260903T093041Z.enc`（101,536B，保留 2 份）

## 2. 验收证据矩阵（对应 §13，逐项状态）

| Gate | 状态 | 证据 |
|---|---|---|
| PR1 协议 `PR1-MCP-*` | 自动部分 ✅；**真实 AI 记录 ⛔** | canonical tools 100%（协议 1.1 测试）；真实工具黑盒待用户 |
| PR1 安全 `PR1-AUTH-*`/`PR1-UPLOAD-*` | ✅ | 拒绝矩阵/上传分级/激活重置/恶意 payload 测试；依赖 0 |
| PR2 部署 `PR2-COMPOSE-*`/`WORKER-*` | ✅ | compose healthy；worker 租约/重试/死信测试；/ready 503 语义 |
| PR2 恢复 `PR2-DR-*` | 本机部分 ✅（`983f19a` 加密备份→恢复演练证据）；**干净主机/RPO/RTO ⛔** | 运行手册 §11 |
| PR3 权限 `PR3-RBAC-*` | ✅ 自动化 | 41 行矩阵 + B4 UI（540+ passed） |
| PR4 上下文 `PR4-FRESH-*`/`CONFLICT-*` | 主链路 ✅（FRESH fresh/stale/missing 单测 + CONFLICT-1/2/4 自动化）；**PG FTS（真实检索）⛔ 设计门**（tsvector 与跨后端指纹冲突，见计划 B2 决策记录） | 计划 `2026-09-03-pr4-context-consistency.md` |
| PR5 性能 `PR5-PERF-*` | ⛔ 未做（需固定基准 + 50 并发 30 分钟） | 环境门 |
| PR5 运维 `PR5-OPS-*` | 部分 ✅：安全响应头 `58f54b2`、`/metrics` 证据 + 告警规则建议 + retention 证据（`2b7df25`，见 `docs/development/ops-metrics-and-alerts.zh-CN.md`）；Alertmanager 接线/演练 ⏳ | 升级/回滚/备份手册（运行手册 §3-4/§11） |
| PR6 黑盒 `PR6-E2E-*` | ⛔ | 待用户多角色真实黑盒 |

## 3. 已关缺陷/风险

- 本机部署抓出的 PG-only 缺陷均已修复并带回归：audit 多态外键（0017）、fingerprint 归一化（含 pg_dump 恢复差异 `983f19a`）、占位 token 环境注入
- 依赖审计：pip/npm 0 High/Critical

## 4. 挂起（用户/真实环境）

真实 AI 黑盒；DR 干净主机 + RPO≤24h/RTO≤4h；运维 TLS 证书；PR6 多角色 + 签字；push origin。

## 5. 黑盒 A1 前置修复（2026-09-03 追加）

- 现象：Cursor agent 经 Agora MCP 调 `agora_start_work` 反复报 `404 Not Found`，误判 "Local Connector 未运行"。
- 根因 1（环境）：本机部署栈 DB 在运维重建后只剩归档的 Smoke Demo，无任何绑定仓库的活动项目 → start-work 命中协议 404 `PROJECT_UNRESOLVED`（agent 看不到 body）。
- 根因 2（产品缺陷，已修复 `3c3d59c`）：stdio 客户端 `raise_for_status()` 把带 `code`/`message`/`next_actions` 的协议结构化 4xx 压成一句 "404 Not Found"；修复后协议结构化非 2xx 作为正常工具结果返回（含 `http_status`），其余 4xx/5xx 错误文本带响应体；`agora_start_work` 工具描述补充 next_actions 指引。mcp 单测 39 passed。
- 环境重建（本机栈）：项目 `agora-bb-demo`（slug `agora-bb-demo`，remote `github.com/dzyzhong/agora-bb-demo`，default main，active）；agent 用户（Local Bootstrap User）owner 成员（201）。
- 复验（真实 MCP dispatch，agent token）：`agora_start_work` 200 → `session_id`/AG-200 work item；`agora_prepare_context` 200（level empty——项目尚无 assets，属预期）；`agora_close_work` 200（探针 session 已关闭）。

## 6. 自助黑盒 A1→A5 全链路复验 PASS（2026-09-03）

驱动方式：真实 stdio MCP server 进程（`python -m apps.mcp.server`，JSON-RPC over stdin/stdout，与 Cursor 同一通道）；人工批准以 admin 凭据经 login→/auth/reauth→approve API 模拟 Web 操作。清理了此前半途流程在演示项目产生的提案/修订/会话（本地演示库卫生），在干净状态复验。

| 步 | 动作 | 结果 |
|---|---|---|
| A1 | `agora_start_work`（repo_remote agora-bb-demo）→ session `81b111b3`；`agora_prepare_context` | 200；level empty + provisional（新项目预期）；next_action plan_context |
| A2 | `agora_submit_context_proposal`（task_update，cb547f4→be7c21c6） | proposal `3a5f394f` submitted |
| A3 | admin reauth + approve（revision_signal observed be7c21c6） | **approved**；accepted revision `5db3d2b4`；流 head 更新 |
| A4 | `agora_record_evidence`（local_test passed）+ `agora_complete_workflow_step`（analysis） | evidence 落库；analysis **completed** → 推进 design |
| A5 | `agora_close_work` | session **closed**（生成 writeback 供人审阅） |
| 验证 | `/harness/get-project-status`（admin 视角） | delivery_readiness **ready**；quality **passing**；pending_approvals 0；evidence 可见 |

用户试用指引：`docs/development/agora-usage-manual.zh-CN.md`（两端操作 + URL + 排查表 + 术语）。

## 7. 自助黑盒续跑：A6/A7/B/C2/C3 PASS（2026-09-03，C4 运行中）

统一走真实本机栈（nginx 8443 + api），探测项目 `security-matrix`(4f8b8419) 与 `multi-role`(6c957064)，演示项目 agora-bb-demo 保持干净供用户试用。

### A6 上传分级 / 审批矩阵
- 1.1MB 超限 body → **413**（nginx）
- close-work development_update 含 AWS secret（`AKIA…`）→ **403 HIGH_RISK_UPLOAD_REQUIRES_GRANT**（reasons: source_or_document_excerpt, secret_rule_exception）
- close-work changed_files 含绝对路径 `/etc/passwd` → **422** value error "changed file path must be POSIX relative"
- complete-workflow-step 携带 artifacts → **400 PR1_UPLOAD_POLICY_REQUIRED**（PR1B 前摘要-only 边界）
- approve 尝试：agent / CI / human(personal) Bearer → 均 **403 APPROVAL_CREDENTIAL_REQUIRED**（需 reauth 的 Web 人类会话或审批 grant）；成功支路 = admin reauth Web 批准 200（§6 复验）

### A7 协议协商
- `Agora-Connector-Version: 0.0.5`（<0.1.0）→ **426 UPGRADE_REQUIRED**，detail 含 supported [1.0,1.1]/current 1.1/minimum_connector 0.1.0 + next_actions upgrade_connector
- `Agora-Protocol-Version: 1.0`（旧协议）→ 200 且响应携带 **deprecation** {legacy_protocol_version 1.0, current_protocol_version 1.1, remove_after PR1A}（明确升级提示）

### B 多角色（multi-role 项目）
- B1：建 3 个真实账号并激活：dev1(developer)/rev1(reviewer)/qa1(quality)，各自签发 agent 凭据；三人并行 start-work → 3 个不同 work item/session（intent 分别 analysis/implementation/test_generation）
- B2：dev1(developer) Web reauth 批准 → **403 PROJECT_ROLE_REQUIRED**（required owner/admin/reviewer, actual developer）；rev1(reviewer) Web reauth 批准 → **200**（proposal 13feab22 approved）；qa1 查询项目状态 → 200
- B3：改角色 dev1 developer→viewer 生效（members 列表可见）；rev1 token **rotate** 后旧 token 401/新 token 200；qa1 token **revoke** 后 401；qa1 **disable** 后 Web 登录 401 INVALID_CREDENTIALS

### C2 加密备份→恢复
- 安装每日 02:00 加密备份 cron（`scripts/install_backup_cron.sh`）→ RPO ≤24h
- 计时备份 ~0.7s（209KB .enc，轮转保留）；删除线上标记 evidence → 计时恢复至临时库 ~0.7s → 标记在恢复库存在(1)、线上仍缺失(0)（无 resurrect）；**RTO 秒级 ≪ 4h**

### C3 恢复演练
- worker 停止期间批准提案 → outbox `context_head_changed` 滞留 pending(attempts 0)；worker 重启后 ~3s 内排空为 completed(attempts 1，无 last_error)
- nginx/api/web 逐个重启：/ready 200、api healthy、web 响应正常；重启后 agent 鉴权调用 200

### C4 PR5-PERF（运行中）
- 50 并发 × 30 分钟直连 api:8000 /ready（绕开 nginx 20r/s 限流，perf_smoke 注释指定的正式做法）；结果待补（§8）。
