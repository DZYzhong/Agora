# PR4 执行计划：上下文一致性与真实检索（2026-09-03 kickoff）

> 上游：`docs/superpowers/specs/2026-08-28-agora-production-readiness-design.zh-CN.md` §11 PR4。
> 试运行门槛引用：**PR1/PR2/PR3 exit + PR4 上下文并发与 freshness 主链路通过**（FTS 属真实检索，排在主链路后）。

## 1. 现状盘点（2026-09-03 代码走查）

| PR4 outcome | 现状 | 证据 |
|---|---|---|
| Connector 上传清洗后 obs/proposal | ✅ 已有 | upload_policy + harness（PR1C） |
| Accepted ContextRevision 记录 commit baseline / expected head | ✅ 已有 | context governance（p3） |
| RevisionSignal 自动 fresh/potentially_stale/unknown | ⚠️ 逻辑在 runtime/services | 需盘点状态迁移并审计测试名 |
| 签名/多分支/多来源优先级/乱序/重放/force-push/potentially_stale 测试 | ⚠️ 部分 | `test_context_governance_api.py` 等；待逐条对照 |
| 并发 proposal 冲突不静默覆盖 | ⚠️ 有 expected-head CAS | 缺**显式并发覆盖**测试（两 uow 同时提交同 head） |
| PostgreSQL FTS 取代 Fake 运行时索引并可重建 | ❌ 未做 | 运行时仍注入 `FakeKeywordIndex/FakeVectorIndex`；`rebuild_indexes_from_assets` 只重建 Fake |
| 加密离线队列 | ❌ 设计项 | 依赖真实使用形态，后置 |

## 2. 批次

| 批次 | 内容 | 验收 |
|---|---|---|
| B0（本批=kickoff） | 本盘点 + 计划 | 本文档 |
| B1（基本完成）| freshness/冲突主链路**审计与补测**：FRESH 矩阵单测补齐（fresh `rev_1` / potentially_stale / missing + 预算错误）；CONFLICT-1（旧 baseline→needs_rebase 409）既有；CONFLICT-2（接受后第二提案不静默覆盖）新增（`b1022ea`）；重放/force-push 等价归入 CONFLICT-1 的 needs_rebase 语义（补测见后续若发现缺口） | 核销记录见 §3 更新 |
| B2（已完成 2026-09-03）| PostgreSQL FTS 适配层 + 迁移 0019（PG-only generated tsvector + GIN）+ 检索/rebuild + 指纹白名单排除 | `3babef9`；PG 单测含检索排序与 fingerprint；live 已迁移 |
| B3（替换可行性已证，运行时切换后置）| 运行时检索端点仍走进程内 Fake 索引；已加 **Fake vs PG FTS 顶命中等价性**证据（`test_p2_postgres` parity，6 passed）；全量切换需与 vector 检索决策一起评审（Fake vector 无 PG 对应） | parity 绿 |
| B4 | 加密离线队列评估（需真实形态，可能挂起） | 决策记录 |

## 3. B1 场景对照表（初稿，B1 执行时逐条核销）

- FRESH-1 提交后 head 更新 → fresh
- FRESH-2 远端有新 commit 未见 → potentially_stale
- FRESH-3 无任何信号/空流 → unknown
- FRESH-4 多来源优先级（观察 commit > 提案预期等）
- CONFLICT-1 expected_head 不匹配 → 拒绝（不覆盖）✅ 既有测试（stale→needs_rebase 409）
- CONFLICT-2 两并发提交同一 expected head → 仅一个成功（CAS）✅ 新增（`b1022ea`）
- CONFLICT-3 force-push/重放 → 稳定错误状态（不静默）✅ 语义同 CONFLICT-1（head 校验），显式用例挂起若发现缺口
- CONFLICT-4 多分支隔离 ✅ 既有治理测试（分支不匹配 400/独立 stream）

### B2 设计约束（2026-09-03 记录）

PostgreSQL FTS 直接在 assets 表加 tsvector/GIN 会使 PG 实际 schema 多出列与索引，而 canonical 指纹由 SQLite 重放生成 → **跨后端 fingerprint 不再一致**。可选方案：
1. 指纹按后端生成（PG canonical 在 PG 上重放/或对 FTS 工件做排除列表）——需 schema_manager 架构调整（评审后实施）；
2. FTS 建在**独立 schema/表**并纳入（方案 1 的子集）；
3. 维持 Fake 索引 + 记录"真实检索未达 PR4 outcome"，作为正式放行差异项上报。
**结论：B2 属架构级变更，先出设计决策（推荐方案 1 + 排除列表最小改），不在一轮内强塞。**

## 4. 依赖与顺序

- B1 不依赖 schema 变更；B2 需迁移 0019 + PG 部署（fingerprint 会变，沿用既有流程）。
- B3 依赖 B2 稳定；B4 挂起评估。
- 真实身份黑盒与多分支真实工具上传仍挂用户/真实环境。
