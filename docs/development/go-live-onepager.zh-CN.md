# Agora 上线速览（一页纸，2026-09-03）

> 状态：**生产就绪基线达成**（本机全栈 + 全部自动验证），只差"真实环境/黑盒"按此页执行。代码：`codex/agora-p0` @ `6674906`（远端已同步）；schema `20260902_0019`。

## 1. 三句话
- 治理+身份+审批+检索+监控+备份全部就绪，测试 550（SQLite）+7（PG）绿，`verify_production.sh` 全项 PASS。
- 新服务器：照 `docs/development/deployment-manual.zh-CN.md`（组件版本+前置+步骤）→ 部署后跑 `verify_production.sh`。
- 黑盒：照 `docs/development/blackbox-checklist.zh-CN.md` A1→E2，结果回填 readiness 报告。

## 2. 常用命令（本机）
```bash
scripts/deploy_local.sh --smoke          # 一键冒烟
scripts/verify_production.sh             # 生产验收（7 项）
scripts/backup_db.sh                     # 加密备份（AGORA_BACKUP_PASSPHRASE）
scripts/install_backup_cron.sh           # 每日 02:00 自动备份
scripts/perf_smoke.py                    # 性能基线
```
Web `http://127.0.0.1:3000`（admin）· API TLS `https://127.0.0.1:8443` · 监控 `http://127.0.0.1:9091`

## 3. 交付物索引
- 部署手册 / 运行手册（含事故与端口冲突 §12）/ 黑盒检查单 / 运维指标与告警 / 生产就绪报告（证据矩阵）/ 差距与放行前清单
- 计划：PR4（FTS 已上线）、PR3（B0–B5 + UI）、UI 重设计（侧边栏+深色+双语）

## 4. 仍待你/环境
真实 AI 黑盒（检查单 A/B）· DR 干净主机 + RPO/RTO（检查单 C）· Alertmanager 接收人 · 备份离主机复制 · 托管/IP 证书（如要）。
