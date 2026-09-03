# 生产能力差距清单（2026-09-03，证据版）

> 目标：用户要求"整体干完、具备生产能力后再做黑盒"。本文件把"本机可自动完成"与"卡用户/真实环境"分开，逐条给证据与动作。判定条款出处：`docs/superpowers/specs/2026-08-28-agora-production-readiness-design.zh-CN.md` §11-13。

## 1. 已完成并有证据（本机自动验证）

| 项 | 证据 |
|---|---|
| 本机生产部署（compose 全栈 + PG 0018 + nginx TLS + worker + /ready） | `/ready` 200；api/nginx/postgres healthy；commit 链至 `6ddae6e` |
| PR1A/1B/1C 自动验证 | 审批拒绝矩阵、上传策略、CSRF/会话/reauth、审计、限流/脱敏、依赖审计 0（`test_*` 全绿） |
| PR2 自动项 | migrate 单次、worker 租约/重试/死信、/ready 503 语义、TLS 反代、加密备份 CLI（`backup-sqlite`） |
| PR3 自动项 | 成员/角色 API、Token 生命周期、disable 传播、**RBAC 41 行矩阵自动化**、B4 身份 UI（537 passed） |
| UI/治理面 | 21 页双语设计系统全量铺开，旧 styles 摘除 |
| 跨后端 schema 一致 | PG↔SQLite fingerprint 相同（0018），PG 专属回归 4 passed |

## 2. 可自动完成（本文件驱动，按序执行）

- **A2 PR5 安全响应头 + 攻击场景回归**：API/nginx 补 `X-Content-Type-Options`、`X-Frame-Options`、`Referrer-Policy`、`Content-Security-Policy`(frame-ancestors)、`Permissions-Policy`；契约测试断言。
- **A1 PR4 起步**：盘点冲突/CAS/freshness 主链路测试覆盖（现有 `test_context_governance_api.py` 等），产出 PR4 执行计划；首批评测缺口（含 PostgreSQL FTS 替换 Fake 索引的适配/重建路径设计，实施量评估）。
- **A3 PR2-DR 本机可做部分**：`pg_dump` 加密 → scratch PG 恢复 → schema/ready 校验证据；记录"干净主机演练/RPO/RTO 需真实环境"。
- **A4 生产就绪状态报告草稿（PR6 前身）**：镜像 digest、schema revision、证据矩阵索引（对应 §13 表）——逐项标注 passed/pending 与证据 id。
- **PR5 运维文档**：升级/回滚/备份/恢复手册已在本机运行手册 §4/§3，补齐事件处理小节。

## 3. 卡用户/真实环境（黑盒前你必须提供，我不假装完成）

| 项 | 说明 |
|---|---|
| **真实 AI 工具黑盒（PR1-3 exit）** | 你即将做：Codex/Claude 走 start→complete→close + Web 审批 |
| **PR2-DR 干净主机恢复演练** | 需第二台干净主机；RPO≤24h/RTO≤4h 实测 |
| **运维托管 TLS 证书** | 替换本机自签（需域名/证书） |
| **PR6 多角色真实黑盒 + 放行签字** | 3 开发者并行 + Reviewer/PM/Quality 角色流程 |
| **PR4 "加密离线队列"** | 设计项，依赖真实使用形态，随 PR4 主链路后评估 |
| **push origin** | 分支领先 origin 209 提交；需你确认目标分支后推送 |

## 4. 建议顺序

A2（小，先做）→ A1 PR4 计划与首批 → A3 备份恢复证据 → A4/PR5 文档与状态报告 → 交付黑盒前置清单给你。
