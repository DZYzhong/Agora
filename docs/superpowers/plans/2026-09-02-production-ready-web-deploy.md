# Agora 生产就绪与 Web 整改执行清单（本机部署）

> 开始时间：2026-09-02 18:10
>
> 目标：让 Agora 在**本机**具备生产能力——业务闭环打通（含 Web 审批）、知识可看可审、治理界面可用，交付可一键部署的 compose + 引导 + 验证脚本。
>
> 执行原则：每项改动遵循项目流程（计划先行、pytest 全绿、Change-Id 提交、docs: record）；每块完成后跑全量验证。

## 范围边界

- ✅ 本清单覆盖：代码收尾、Web UI 整改、本机部署交付（全部可在我当前环境自动化验证 + 交付脚本/文档）。
- ⏳ 需真实环境（标注为"挂起"）：DR 干净主机演练、RPO≤24h/RTO≤4h 实测、运维 TLS 证书、真实 AI 工具（Codex 等）黑盒、PR3-PR6 完整产品化。这些不阻塞本机生产能力，但阻塞"正式生产放行"。

---

## Chunk A：业务闭环修复（先做，阻塞一切使用）

### A1. 修复 Web 审批闭环（P0，最高优先）

现状：PR1B/PR1C 后审批端点要求已重新认证的 Web 会话或一次性 grant；Web 审批路由仍用 `AGORA_WEB_HUMAN_TOKEN` bearer → 生产环境 403 `APPROVAL_CREDENTIAL_REQUIRED`。

- [ ] A1.1 Web `lib/api.ts` 增加会话版审批调用（cookie + CSRF + 可选 grant_id）
- [ ] A1.2 上下文提案 approve：Web 审批前校验/引导登录 → 需要时 reauth（密码弹窗页）→ 自动签发一次性 grant → 带 grant 审批
- [ ] A1.3 技能 approve：同上
- [ ] A1.4 无会话/未 reauth 时引导登录，错误信息友好
- [ ] A1.5 集成测试：Web 会话流程（登录→reauth→grant→approve 全链路 API 级验证）+ web-config 契约测试
- [ ] 提交：`feat: close web approval loop with session grants`

### A2. 主 UI 认证打通

- [ ] A2.1 Web 会话路由可用时优先 cookie session；保留 `AGORA_WEB_HUMAN_TOKEN` 作为降级（开发）
- [ ] A2.2 Nav 显示当前登录用户 + "Sign out"；未登录访问治理页时引导登录（不静默空表）
- [ ] A2.3 验证：web 构建 + tsc + 相关测试
- [ ] 提交：`feat: wire cookie sessions into the governance ui`

## Chunk B：Web 可视化与功能整改（按你确认的问题）

### B1. 项目知识总览页

- [ ] B1.1 新增 `/projects/[projectId]/knowledge` 页：统计卡（asset 数/类型分布、accepted context revisions、approved skills、accepted writebacks）+ "最近沉淀"时间线
- [ ] B1.2 项目首页加入口卡片
- [ ] B1.3 web-config 契约测试
- [ ] 提交：`feat: add project knowledge overview page`

### B2. Context 版本时间线（知识演化可视化）

- [ ] B2.1 Context 页 streams 增加"查看版本历史"：revision 链按 parent→child 展示（版本、commit、来源锚点数、审批人/时间、head 标记）
- [ ] B2.2 版本详情可看内容与来源锚点（复用现有 source 查看能力）
- [ ] B2.3 契约测试 + 视觉走查
- [ ] 提交：`feat: visualize context revision history`

### B3. 审批待办聚合队列

- [ ] B3.1 项目级"待我处理"面板：待批 context proposals、待批 skill candidates、等待人工确认的工作流步骤（数据已有 pending 计数，需可点击队列）
- [ ] B3.2 Status 页 pending 计数 → 可点击跳转到具体待批列表
- [ ] B3.3 契约测试
- [ ] 提交：`feat: add pending approval queue views`

### B4. 工作流 stepper 可视化

- [ ] B4.1 work-item 详情把 workflow steps 渲染为步骤条（完成/当前/等待 + 各步骤产物与确认）
- [ ] B4.2 视觉（纯 CSS/SVG，不引大库）
- [ ] 提交：`feat: visualize workflow step progression`

### B5. Assets 内容查看与来源接入

- [ ] B5.1 Assets 页每行可展开/跳转查看正文（复用 context/source 页能力）
- [ ] B5.2 按类型/来源聚合筛选
- [ ] 提交：`feat: browse asset contents and group by source`

### B6. 会话实时看板（进行中会话）

- [ ] B6.1 项目首页/Sessions 页顶部显示"进行中会话"卡片（agent、意图、当前状态、最近事件）
- [ ] B6.2 契约测试
- [ ] 提交：`feat: show in-flight agent sessions`

## Chunk C：代码收尾（生产残留清理）

### C1. 移除服务端本地初始化残留

- [ ] C1.1 删除 `initialize-local` / `initialization-jobs` API 与 web 关联代码路径（保留运行时策略拒绝即可的，直接删干净）；迁移相关测试
- [ ] C1.2 删除 `prepare_p2_blackbox.py` 等仅本地路径依赖脚本或标注仅测试用
- [ ] 提交：`refactor: remove server-local initialization remnants`

### C2. Compose 精简与真实化

- [ ] C2.1 移除运行时未接入的 qdrant/opensearch/neo4j 容器（MEDIUM-1 收敛）；如保留则注明仅供未来接入
- [ ] C2.2 nginx 反代作为 API/Web 统一入口的 compose 契约（外部只暴露 443/80）
- [ ] 提交：`chore: slim compose to deployed services`

## Chunk D：本机部署交付（最终目标：本机具备生产能力）

### D1. 一键部署脚本与引导

- [ ] D1.1 `scripts/deploy_local.sh`（或等价）：生成自签证书 → `docker compose up -d --build` → 等待 healthy → `bootstrap-admin` 创建 Admin → 输出访问地址/账号指引
- [ ] D1.2 `.env.production.example`：production 环境变量齐全（DB URL、tokens、origins、backup passphrase）
- [ ] D1.3 部署后 smoke：`/ready`、登录、建项目、（可在脚本内用 API 冒烟）

### D2. 本机生产运行手册

- [ ] D2.1 `docs/development/local-production-runbook.zh-CN.md`：启动、Admin 引导、创建用户（激活 token 交付）、Web 审批流、备份/恢复、升级（migrate）、worker 运维、日志/指标查看
- [ ] D2.2 P9/PR 黑盒文档与本手册互链

### D3. 最终验收

- [ ] D3.1 全量 pytest 绿 + `tsc --noEmit` + `next build` + `pip check` + 依赖审计 0
- [ ] D3.2 若本机有 docker：真实 `docker compose up` + 部署 smoke 通过；若无 docker：交付脚本与文档，标注"需本机执行 docker up"（诚实记录）
- [ ] D3.3 roadmap 状态更新：本机生产能力达成；PR1-PR6 exit、DR/RPO/RTO、真实 AI 黑盒仍挂起
- [ ] 提交：`docs: record local production readiness`

---

## 挂起项（不阻塞本机生产能力，需真实环境/你配合）

- 真实 AI 工具（Codex/Cursor/Claude Code）PR1 黑盒：start→complete→close + Web 审批
- DR 干净主机恢复演练 + RPO≤24h / RTO≤4h 实测
- 运维托管 TLS 证书（替换本机自签）
- PR3（完整角色矩阵/Token 生命周期）、PR4（PostgreSQL FTS/加密离线队列）、PR5（告警/性能）、PR6（正式发布报告）——建议本机跑通并稳定后逐阶段推进

## 执行顺序总览

A1→A2→B1→B2→B3→B4→B5→B6→C1→C2→D1→D2→D3
（A1 是硬依赖；B/C/D 内部按序；每块独立可提交可验证）
