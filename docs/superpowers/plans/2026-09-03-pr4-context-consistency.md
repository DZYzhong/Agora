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
| B1（进行中）| freshness/冲突主链路**审计与补测**：CONFLICT-2（接受后旧 baseline 第二提案 409 needs_rebase 不静默覆盖）已补并通过（11 passed）；待补：FRESH 迁移矩阵、重放/force-push 显式用例、多来源优先级 | 逐条核销入档 |
| B2 | PostgreSQL FTS 适配层设计 + 迁移（tsvector 列 + GIN）与 rebuild-from-assets 的 PG 路径 | 迁移 0019 + PG 检索单测（SQLite 回退保持测试绿） |
| B3 | 检索端点切换到 PG 路径（keyword/context 查询） | tsc/build/pytest + PG 冒烟 |
| B4 | 加密离线队列评估（需真实形态，可能挂起） | 决策记录 |

## 3. B1 场景对照表（初稿，B1 执行时逐条核销）

- FRESH-1 提交后 head 更新 → fresh
- FRESH-2 远端有新 commit 未见 → potentially_stale
- FRESH-3 无任何信号/空流 → unknown
- FRESH-4 多来源优先级（观察 commit > 提案预期等）
- CONFLICT-1 expected_head 不匹配 → 拒绝（不覆盖）
- CONFLICT-2 两并发提交同一 expected head → 仅一个成功（CAS）
- CONFLICT-3 force-push/重放 → 稳定错误状态（不静默）
- CONFLICT-4 多分支隔离

## 4. 依赖与顺序

- B1 不依赖 schema 变更；B2 需迁移 0019 + PG 部署（fingerprint 会变，沿用既有流程）。
- B3 依赖 B2 稳定；B4 挂起评估。
- 真实身份黑盒与多分支真实工具上传仍挂用户/真实环境。
