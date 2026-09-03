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
