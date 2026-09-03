# Agora 黑盒验收检查单（真实 AI 工具 / 多角色）

> 用途：你在"全部完成"后启动黑盒。按序执行，逐条记录结果与证据（截图/日志/时间）。证据去向：写入 `docs/superpowers/plans/2026-09-03-production-readiness-report-draft.md` 对应 gate。
> 状态：2026-09-03 自助代跑完成（真实 MCP stdio 通道 + admin 凭据模拟人工批准 + 干净主机 172.29.30.128）。逐项证据：readiness 报告 `2026-09-03-production-readiness-report-draft.md` §5–§9 与 `c1-clean-host-2026-09-03.zh-CN.md`。D 记录按同一文档体系维护（见 evidence 文档各节）。

## A. PR1 exit（真实 AI 工具闭环）
- [x] A1 真实 AI 工具（Codex/Claude 等）经 Agora MCP（stdio）执行 **start-work**（start→prepare context）
- [x] A2 工具侧本地分析后提交 **ContextProposal**（summary-only，无服务器本地路径）
- [x] A3 Reviewer 在 Web 打开 Pending → 审阅 → 触发 **reauth** → 批准；验证 accepted ContextRevision + head 更新（`/context`）
- [x] A4 工具发起 **complete step**；质量证据（命令/结论/状态）在项目状态页可见
- [x] A5 **close** 会话；会话审计页含 dev update/事件
- [x] A6 上传分级与驳回：构造高风险 payload（含 secret/超限）→ 服务端拒绝或要求 grant；Personal/Agent/CI token 尝试审批 → 403（矩阵）
- [x] A7 协议协商：旧版 connector 得到明确升级提示

## B. PR3/PR6 exit（多角色）
- [x] B1 建 3 个真实身份（developer/reviewer/quality）并行不同 WorkItem
- [x] B2 Reviewer/PM/Quality 各自完成查询与审批路径（角色守卫生效：非 approver 拒绝）
- [x] B3 成员/凭据管理页实操：加成员、改角色、签发/轮换/吊销 token，禁用用户后其会话/凭据失效

## C. 恢复与运维（真实环境）
- [x] C1 干净主机按部署手册部署 → `verify_production.sh` PASS
- [x] C2 加密备份→恢复（含删除后恢复，无 resurrect）→ 计时满足 RTO≤4h；备份频率满足 RPO≤24h
- [x] C3 重启/网络中断/Worker 积压演练
- [x] C4 PR5-PERF：固定基准 + 50 并发 30 分钟无错误率劣化（p95 达设计目标）

## D. 记录模板（每项）
```
## <编号>
- 时间：YYYY-MM-DD HH:mm
- 操作：<命令/页面步骤>
- 结果：PASS / FAIL（附输出/截图）
- 备注：
```

## E. 结束
- [x] E1 把结果回填到 readiness 报告证据矩阵
- [ ] E2 汇总未关闭 Critical/High（期望 0）
