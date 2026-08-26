# P6 Quality and Project Status 黑盒验证步骤

目标：验证 Agora 能让 AI 工具记录真实研发任务的质量证据，并让项目经理/质量人员通过 AI 工具和 Web UI 看到一致的项目状态、质量状态、阻塞项和待审批事项。

## 验证边界

- 用户只通过 AI 工具和 Web 页面完成验证。
- 不要求用户手动调用 HTTP API。
- AI 工具使用 Agora MCP/Harness 能力：`agora_start_work`、`agora_prepare_context`、`agora_complete_workflow_step`、`agora_record_evidence`、`agora_get_quality_status`、`agora_get_project_status`、`agora_submit_skill_candidate`。
- Web UI 用于查看项目状态、质量证据、阻塞项和待审批事项。
- Agora 不能把 AI 总结或流程进度当成测试通过证据；没有证据就是 `unverified`，失败证据就是 `failing`。

## 前置条件

1. Agora API 和 Web 已启动。
2. AI 工具已接入 Agora MCP。
3. 已存在一个项目，例如“支付服务”或“订单履约服务”。
4. 本地有一个真实软件研发项目目录，任务内容贴近研发团队日常工作。

## 步骤 1：AI 工具开始第一个任务并记录通过证据

在 AI 工具中输入：

```text
请通过 Agora 开始一个任务：AG-901 账单导出稳定性检查。
项目使用当前本地仓库。请完成分析步骤，然后运行和账单导出相关的本地测试。
测试完成后，把测试结果作为 Agora 质量证据记录进去。
```

期望：

- AI 工具调用 `agora_start_work`，返回 WorkItem 和 WorkSession。
- AI 工具调用 `agora_prepare_context`，基于 Agora 返回的共享项目上下文开展分析。
- 如果项目已有 approved SkillVersion，`agora_prepare_context` 返回的 `capability_pins.skill_version_ids` 应包含实际使用的 SkillVersion。
- AI 工具调用 `agora_complete_workflow_step` 保存分析产物。
- AI 工具在本地项目里真实运行测试。
- AI 工具调用 `agora_record_evidence`。
- 证据字段应类似：
  - `evidence_type = local_test`
  - `source = ai_tool`
  - `status = passed`
  - `command` 是实际执行的测试命令
  - `output_summary` 是测试摘要

## 步骤 2：AI 工具查询第一个任务质量状态

在 AI 工具中输入：

```text
请查询刚才 AG-901 的 Agora 质量状态。只根据已经记录的质量证据回答，不要根据你的总结推断通过。
```

期望：

- AI 工具调用 `agora_get_quality_status`。
- 返回 `quality_state = passing`。
- 返回的 `evidence` 中能看到刚才记录的 `local_test`。
- `unverified_claims` 为空。

## 步骤 3：AI 工具开始第二个任务并记录失败证据

在 AI 工具中输入：

```text
请通过 Agora 开始一个任务：AG-902 退款回调幂等性修复。
项目使用当前本地仓库。请完成分析步骤，然后运行退款回调相关测试。
如果测试失败，请把失败结果如实记录为 Agora 质量证据，不要改写成通过。
```

期望：

- AI 工具调用 `agora_start_work`。
- AI 工具调用 `agora_prepare_context`。
- AI 工具调用 `agora_complete_workflow_step`。
- AI 工具真实运行相关测试。
- 如果本地测试确实失败，AI 工具调用 `agora_record_evidence`，且 `status = failed`。

## 步骤 4：AI 工具查询第二个任务质量状态

在 AI 工具中输入：

```text
请查询 AG-902 的 Agora 质量状态，并说明是否允许声明交付质量通过。
```

期望：

- AI 工具调用 `agora_get_quality_status`。
- 返回 `quality_state = failing`。
- `counts.failed >= 1`。
- `next_actions` 包含修复失败质量证据的提示。
- AI 工具不能声明该任务质量通过。

## 步骤 5：AI 工具创建一个待审批 SkillCandidate

在 AI 工具中输入：

```text
请把 AG-901 账单导出稳定性检查中的发布前测试检查经验沉淀为 Agora SkillCandidate。
名称：Billing Stability Review
Slug：billing-stability-review
触发词：billing, export, stability
说明：发布账单导出相关需求前，必须检查本地测试、失败用例、回滚方案和监控负责人。
```

期望：

- AI 工具调用 `agora_submit_skill_candidate`。
- 返回 `next_actions[0].type = human_review_skill_candidate`。
- 该 Skill 在 Web 中处于待审状态。

## 步骤 6：项目经理通过 AI 工具查询项目状态

在 AI 工具中输入：

```text
请通过 Agora 查询当前项目状态，重点说明 WorkItem 数量、质量分布、交付就绪状态、阻塞项和待审批事项。
```

期望：

- AI 工具调用 `agora_get_project_status`。
- 返回 `work_item_counts.total >= 2`。
- 返回 `quality_counts`，其中至少包含一个 `passing`，如果 AG-902 测试失败则至少包含一个 `failing`。
- 返回 `delivery_readiness.state`：
  - 有失败质量证据时为 `blocked`。
  - 没有证据的 WorkItem 不应显示为 ready。
- 返回 `blockers`，失败任务应出现 `FAILING_QUALITY_EVIDENCE`。
- 返回 `pending_approvals.skill_candidates >= 1`。

## 步骤 7：Web UI 查看项目状态

打开 Web：

```text
http://127.0.0.1:3000/projects
```

操作：

1. 进入刚才使用的项目。
2. 点击 `Project status`。
3. 查看 `Delivery readiness`、`Quality evidence`、`Quality dimensions`、`Pending approvals`、`Blockers`、`Work item quality`、`Latest evidence`。

期望：

- Web 页面展示的 WorkItem 数量与 AI 工具查询一致。
- Web 页面展示的质量分布与 AI 工具查询一致。
- `Latest evidence` 能看到 AG-901 或 AG-902 的测试命令、状态和结论。
- 有失败证据时，`Blockers` 能看到对应 WorkItem。
- `Pending approvals` 能看到刚才提交的 SkillCandidate 数量。

## 步骤 8：验证无证据任务不会被声明通过

在 AI 工具中输入：

```text
请通过 Agora 开始一个任务：AG-903 登录超时提示优化。
这次先不要运行测试，也不要记录质量证据。随后查询这个任务的质量状态。
```

期望：

- AI 工具调用 `agora_start_work`。
- AI 工具调用 `agora_get_quality_status`。
- 返回 `quality_state = unverified`。
- 返回 `gaps[0].code = NO_QUALITY_EVIDENCE`。
- 返回 `unverified_claims`，说明 Agora 不会根据 AI 总结或流程进度推断质量通过。

## 通过标准

- AI 工具能记录通过、失败和缺失三类质量状态。
- 失败证据不会被后续 AI 总结覆盖成通过。
- 无质量证据的 WorkItem 显示为 `unverified`。
- 项目状态能聚合 WorkItem、质量分布、交付就绪状态、阻塞项和待审批事项。
- Web 项目状态页与 AI 工具查询结果一致。
- 已批准 SkillVersion 被上下文返回时，`capability_pins.skill_version_ids` 能保留可审计的能力版本。
- 用户不需要手动调用任何 HTTP API。
