# 计划：知识引导式工程对话闭环（context-first project loop）

> 日期：2026-09-04 ｜ 分支：`codex/agora-p0`
> 目标：把"会话级手工闭环"升级为产品化的**知识引导式工程对话**：
> 工程对话先查 Agora 项目知识+skill → 无上下文则提示生成 → AI 读本地代码生成上下文并反哺 →
> 人工批准成为已接受知识 → 后续对话可检索复用 → 开发中按需更新。

## 背景与差距（对照用户场景）

| 场景 | 现状 |
|---|---|
| 对话先查项目知识/skill | 需先 `start-work` 起会话才有 bundle；skill 已内联 instructions |
| 无上下文提示 | 有信号（level=empty / analyze_local_project），无产品化引导 |
| AI 生成并反哺 | 提案→批准→accepted ContextRevision ✅ |
| 后续**查回**已接受知识 | ❌ plan_context 只检索 assets，revision 内容不可检索/取回 |

## 改动设计

### A. 已接受修订内容 → 可检索知识资产（核心）
- 批准通过（`approve_context_proposal` 内 `create_context_revision` 后）把 head revision
  序列化为资产 **upsert**（每项目/流一个 `source="context_revision:<stream_id>"` 的 head 知识资产，
  type=`context_revision`）：content=revision 结构化内容（JSON 序列化 + summary/key_facts），
  使 keyword/vector 检索与 `fetch_context_ref`、Web 知识页可用；旧资产随每次批准替换（不堆积）。
- 依赖：`assets.search_tsv` 为生成列则插入即入索引（需核对 0019 定义）；SQLite Fake 的
  list_assets 路径已覆盖；PG 走 search_tsv。
- 不动 schema/迁移。

### B. 只读轻量入口 `agora_lookup_project_context`
- 目的：工程对话**开头**查询项目知识+skill，不创建 work item/session。
- 入参：`repo_remote` 或 `project_slug/name`（复用 start_work 的项目解析）+ `query` + `token_budget`。
- 返回：project、`has_accepted_context`、head_revision_id、知识候选（asset_id/title/preview）、
  applicable_skills（含 instructions）、`recommended_action`（use_accepted_context /
  generate_context / analyze_local_project）、`next_actions`。
- 服务端：`/harness/lookup-project-context`（成员守卫）+ harness 服务方法 + registry 新工具
  （canonical 12→13，manifest 自动跟随）；不写 session/事件。

### C. 产品化引导
- Web 项目上下文页：无 accepted head 且无资产时显示显式 CTA"本项目暂无上下文：让 AI 按
  lookup→生成→提案 流程补齐"。
- 文档：使用手册新增"知识引导式工程对话（标准循环）"章节 + agent 提示模板。

## 测试与验证
- 单测/集成：registry 工具集更新、lookup 解析与空/有知识分支、批准后 head 资产可检索、
  PG 回归；web-config 源断言。
- 真栈验证（本机）：批准→资产可检索；lookup 返回知识/skill/空提示三态。

## 不做什么（本计划范围外）
- 向量嵌入真实化、跨项目知识、长对话记忆、skill 治理增强。
