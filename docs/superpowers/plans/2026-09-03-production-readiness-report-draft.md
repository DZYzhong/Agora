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
