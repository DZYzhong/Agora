# P5 Skill Governance 黑盒验证步骤

目标：验证 Agora 能把一次真实任务中的团队经验沉淀成 SkillCandidate，由人在 Web 中审查发布成不可变 SkillVersion，并让后续 AI 工具自动拿到并使用这个 approved SkillVersion。

## 验证边界

- 用户只通过 AI 工具和 Web 页面完成验证。
- 不要求用户手动调用 HTTP API。
- AI 工具使用 Agora MCP/Harness 能力：`agora_start_work`、`agora_complete_workflow_step`、`agora_submit_skill_candidate`、`agora_prepare_context`。
- Web UI 只负责审查、编辑、发布、查看证据和审计。

## 前置条件

1. Agora API 和 Web 已启动。
2. AI 工具已接入 Agora MCP。
3. 已存在一个项目，例如“支付服务”或“订单履约服务”。
4. 本地有一个真实软件研发项目目录，任务内容贴近研发团队日常工作。

## 步骤 1：AI 工具开始真实任务

在 AI 工具中输入：

```text
请通过 Agora 开始一个任务：AG-751 发布前风险检查经验沉淀。
项目使用当前本地仓库，任务目标是检查一个即将发布的需求是否具备测试证据、回滚方案、配置开关和监控负责人。
```

期望：

- AI 工具调用 `agora_start_work`。
- 返回 WorkItem 和 WorkSession。
- 下一步提示准备上下文或推进 workflow。

## 步骤 2：AI 工具完成分析步骤并上传证据

在 AI 工具中继续输入：

```text
请分析这个发布检查任务，并把分析结论作为 analysis_note 通过 Agora 完成 analysis 步骤。
分析结论必须包括：风险说明、测试证据、回滚方案、配置开关、监控负责人。
```

期望：

- AI 工具调用 `agora_complete_workflow_step`。
- 返回 artifact id。
- Web WorkItem 详情页的 `Workflow audit` 能看到该 analysis artifact。

## 步骤 3：AI 工具提交 SkillCandidate

在 AI 工具中继续输入：

```text
请把刚才的发布检查经验沉淀成 Agora SkillCandidate。
Skill 名称：Release Readiness Review
Slug：release-readiness-review
触发词：release, rollback, monitoring
说明：检查风险说明、测试证据、回滚方案、配置开关、监控负责人。
请关联刚才的 analysis artifact 作为证据。
```

期望：

- AI 工具调用 `agora_submit_skill_candidate`。
- 返回 `next_actions[0].type = human_review_skill_candidate`。
- Skill 状态为 `candidate`。

## 步骤 4：人在 Web 中审查并发布 SkillVersion

打开 Web：

```text
http://127.0.0.1:3000/projects
```

进入项目，再进入 `Skills` 页面。

操作：

1. 找到 `Release Readiness Review`。
2. 确认 Evidence 区域能看到刚才的 analysis artifact。
3. 在 `Publish approved version` 表单中确认或修改：
   - Version：`1.0.0`
   - Triggers：`release, rollback, monitoring`
   - Instructions：检查风险说明、测试证据、回滚方案、配置开关、监控负责人。
   - Risk constraints：缺少测试证据时必须标记为风险。
4. 点击 `Publish approved version`。

期望：

- 页面刷新后该 Skill 状态为 `approved`。
- `Current version` 显示 `1.0.0 · approved`。
- 页面显示 `SkillVersion <id>`。
- Evidence 仍然保留。

## 步骤 5：后续 AI 任务自动获得 approved SkillVersion

在 AI 工具中新开一个相关任务：

```text
请通过 Agora 开始一个任务：AG-752 检查本次 release 回滚风险。
然后准备上下文，查询：release 回滚风险检查。
```

期望：

- AI 工具调用 `agora_start_work`。
- AI 工具调用 `agora_prepare_context`。
- `prepare_context` 返回的 ContextBundle 中包含：
  - `skills[0].slug = release-readiness-review`
  - `skills[0].version = 1.0.0`
  - `skills[0].instructions` 为 Web 发布时确认的说明。
  - `capability_pins.skill_version_ids` 包含该 SkillVersion id。
- AI 工具应基于该 SkillVersion 的 instructions 和 risk_constraints 开展发布检查。

## 步骤 6：Web 审计验证

回到 Web：

1. 打开 `Skills` 页面。
2. 找到 `Release Readiness Review`。
3. 点击或执行一次 `Run`。
4. 查看 `Skill runs`。

期望：

- Skill run 记录显示 `SkillVersion <id>`，不是 `not pinned`。
- 该 id 与 `Current version` 的 SkillVersion id 一致。

## 通过标准

- AI 工具能从真实 WorkSession 提交 SkillCandidate。
- Web 能展示证据并由人发布 approved SkillVersion。
- 后续 AI 工具调用 `agora_prepare_context` 时自动收到相关 SkillVersion。
- SkillRun 和 WorkSession 保留使用的 SkillVersion pin。
- 用户不需要手动调用任何 HTTP API。
