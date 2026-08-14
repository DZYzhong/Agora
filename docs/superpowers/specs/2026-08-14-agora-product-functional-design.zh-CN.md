# Agora 产品功能设计

## 1. 产品定位

Agora 是软件研发团队的低感知 AI 协作记忆层。它不是 AI 工具本身，也不是客户代码的默认扫描器，而是团队项目上下文、任务过程、技能包、团队经验、项目资产和审计治理的共享中心。

开发者、质量人员、项目经理主要通过各自的 AI 工具接入 Agora。Agora Web UI 主要面向项目经理、技术负责人、质量人员和管理员，用于可视化、审批、治理、审计和团队资产管理。

## 2. 产品目标

### 2.1 团队共享一致上下文

同一个项目中，开发人员 A、B、C 处理不同任务时，应共享同一套经过治理的项目上下文、开发流程、技能包和团队经验，减少 AI 工具对项目理解不一致造成的跑偏。

### 2.2 降低 AI token 和重复分析成本

一个项目的上下文由 AI 工具在本地分析后上传 Agora。后续其他开发者复用已批准上下文，避免每次打开项目都重新全量分析代码和文档。

### 2.3 规范 AI 工具工作方式

每个项目可以配置自己的开发流程，例如分析、设计、评审、开发、自测、上传。AI 工具在任务中按流程引导用户，并在每一步生成固定产物。

### 2.4 沉淀团队资产

任务过程、上下文更新、测试经验、风险结论、开发规范、候选 skill 都应沉淀到 Agora。经过审批后成为团队可复用资产。

### 2.5 降低对个人能力差异的依赖

通过统一上下文、固定流程、技能包、评审和质量审计，使不同经验水平的成员在 AI 工具辅助下更稳定地完成任务。

## 3. 用户角色

## 3.1 开发人员

开发人员在 AI 工具、IDE、Terminal 中完成日常任务，原则上不需要主动打开 Agora Web UI。

主要诉求：

- 开始任务时自动获得项目上下文。
- AI 工具知道当前任务应遵循哪些流程。
- 每一步有清晰产物要求和人工确认节点。
- 开发结束后自动整理上下文更新和候选经验。
- 不需要手动判断 Agora 上下文是否最新。

关键操作：

- 在 AI 工具中开始任务。
- 审查 AI 生成的分析、设计、评审、自测文档。
- 确认是否上传任务产物、ContextUpdate、候选 skill。

## 3.2 AI 工具

AI 工具是开发人员、质量人员、项目经理使用 Agora 的主要入口。

主要职责：

- 识别本地项目和 Git 状态。
- 识别任务名称或要求用户补充。
- 向 Agora 解析项目身份。
- 检查上下文 freshness。
- 获取已批准 ContextPack、项目流程和 skill。
- 本地扫描代码和文档，生成 ContextPack 或 ContextUpdate。
- 引导任务流程并生成每一步文档。
- 上传任务过程、文档、上下文更新、候选 skill。

## 3.3 项目经理 / 技术负责人

项目经理和技术负责人是 Agora Web UI 的核心用户。

主要诉求：

- 知道项目当前 AI 上下文是否可信、是否过期。
- 审核任务上传的 ContextUpdate 是否可合并。
- 审批候选 skill 是否入库。
- 配置项目开发流程和文档要求。
- 查看项目任务状态、团队资产和审计历史。

关键操作：

- 审批或拒绝 ContextPack / ContextUpdate。
- 审批或废弃 skill。
- 配置项目流程模板。
- 查看任务看板、质量风险、团队资产。

## 3.4 质量人员

质量人员可以通过 AI 工具或 Web UI 了解质量情况。

主要诉求：

- 查看项目整体质量状态。
- 查看每个任务的质量状态。
- 获取风险、测试覆盖、自测证据、回归建议。
- 审计任务是否按流程产出文档。

## 3.5 管理员

管理员负责组织、权限、项目配置、集成配置和系统治理。

主要操作：

- 管理组织和成员。
- 配置 AI 工具接入凭证。
- 配置项目权限。
- 配置审批规则和审计保留策略。

## 4. 核心对象模型

## 4.1 Project

项目是 Agora 管理上下文和团队资产的根对象。

关键字段：

- 项目名称。
- 项目标识。
- 代码仓库身份，例如 remote URL、repo fingerprint。
- 默认分支。
- 所属组织。
- 当前上下文状态。
- 当前流程模板。
- 当前主上下文版本。

## 4.2 LocalWorkspaceIdentity

AI 工具从本地项目采集的身份信息。

字段：

- local_path。
- git_remote。
- branch。
- commit_sha。
- dirty_workspace。
- repo_root_fingerprint。
- detected_project_name。

该对象只用于项目解析和 freshness 判断。Agora 不需要读取客户本地源码。

## 4.3 ContextPack

项目上下文包，是团队共享项目理解的主要载体。

内容包括：

- 项目概览。
- 业务域和核心模块。
- 关键代码路径和文档路径。
- 技术栈。
- 关键流程。
- 风险点。
- 测试策略。
- source_refs。
- 生成工具和生成时间。
- 基线 commit。
- 审批状态。

状态：

- draft。
- pending_review。
- accepted。
- rejected。
- deprecated。

## 4.4 ContextUpdate

任务完成后对项目上下文的增量更新。

内容包括：

- 本任务改变了哪些模块。
- 新增或修正了哪些业务理解。
- 新增测试经验。
- 新增风险或约束。
- 影响的 source_refs。
- 关联任务、session、commit。

ContextUpdate 需要由项目经理或技术负责人评审后合并到项目 ContextPack。

## 4.5 Skill

团队可复用工作方法或 AI 工具策略。

来源：

- 项目经理手工创建。
- 管理员通过 AI 工具生成。
- 开发人员任务中总结候选 skill。
- 多次 accepted writeback 提炼。

状态：

- candidate。
- draft。
- approved。
- deprecated。

内容：

- 名称。
- 触发条件。
- 适用项目或组织范围。
- 输入要求。
- 操作步骤。
- 输出格式。
- 风险和限制。
- 版本历史。

## 4.6 WorkflowTemplate

项目开发流程模板。

一个典型流程：

- 分析。
- 设计。
- 评审。
- 开发。
- 自测。
- 上传。

每一步定义：

- 步骤名称。
- 目标。
- 必填文档。
- AI 工具提示要求。
- 人工审查点。
- 完成条件。
- 是否允许跳过。

## 4.7 TaskSession

一次任务执行过程。

内容：

- 任务名称。
- 任务来源。
- 执行人员。
- 使用的 AI 工具。
- 使用的 ContextPack 和 skill。
- 流程步骤状态。
- 每步产物。
- 事件时间线。
- 自测结果。
- 上传的 ContextUpdate。
- 候选 skill。

## 4.8 WorkArtifact

任务过程产物。

类型：

- 分析文档。
- 设计文档。
- 评审记录。
- 开发变更说明。
- 自测报告。
- 上传/交付说明。
- 质量分析报告。

每个产物应同时支持：

- 保存到项目本地。
- 上传 Agora。
- 与任务 session 关联。
- 被项目经理或质量人员审计。

## 5. 核心业务流程

## 5.1 开发者开始任务

1. 开发者在 AI 工具中打开本地项目。
2. AI 工具采集 LocalWorkspaceIdentity。
3. AI 工具请求 Agora 解析项目。
4. Agora 返回项目、上下文状态、流程模板、可用 skill。
5. 如果任务名称无法自动识别，AI 工具询问开发者。
6. Agora 创建 TaskSession。
7. AI 工具按项目流程开始任务。

## 5.2 上下文获取和生成

1. AI 工具向 Agora 请求当前项目上下文。
2. Agora 判断状态：
   - fresh：返回 accepted ContextPack。
   - missing：要求 AI 工具本地生成首个 ContextPack。
   - stale：要求 AI 工具本地生成 ContextUpdate。
   - ahead：提示本地代码落后。
   - dirty_workspace：允许生成 session 临时上下文，但不更新团队主上下文。
3. AI 工具读取本地代码和文档。
4. AI 工具生成上下文。
5. AI 工具上传 ContextPack 或 ContextUpdate。
6. Agora 保存为 pending_review。
7. 项目经理或技术负责人审核。
8. 审核通过后成为团队共享上下文。

## 5.3 任务流程执行

以“分析、设计、评审、开发、自测、上传”为例：

### 分析

AI 工具基于项目上下文、任务描述、本地代码生成任务分析文档。

产物：

- 需求理解。
- 影响范围。
- 相关模块。
- 风险初判。
- 需要确认的问题。

人工节点：

- 开发者确认分析是否正确。

### 设计

AI 工具生成实现方案。

产物：

- 技术方案。
- 数据流或调用链。
- 变更文件计划。
- 测试计划。
- 回滚或兼容策略。

人工节点：

- 开发者或技术负责人确认方案。

### 评审

AI 工具根据项目规范和 skill 检查设计。

产物：

- 评审意见。
- 风险清单。
- 待修正项。

人工节点：

- 开发者确认是否继续开发。

### 开发

AI 工具辅助修改本地代码。

产物：

- 变更摘要。
- 变更文件。
- 关键实现说明。

人工节点：

- 开发者审查代码。

### 自测

AI 工具运行或指导运行测试。

产物：

- 测试命令。
- 测试结果。
- 未覆盖风险。
- 回归建议。

人工节点：

- 开发者确认自测是否通过。

### 上传

开发者或 AI 工具整理并上传任务结果。

产物：

- 任务总结。
- ContextUpdate。
- 候选 skill。
- WorkArtifact 集合。

人工节点：

- 开发者确认上传内容。
- 项目经理后续在 Web UI 审核合并。

## 5.4 ContextUpdate 审核合并

1. 项目经理打开 Web UI。
2. 查看待审核 ContextUpdate。
3. 对比当前 accepted ContextPack。
4. 查看 source_refs、任务产物、自测证据。
5. 选择：
   - accept and merge。
   - request changes。
   - reject。
6. Agora 记录审批事件。
7. 合并后的上下文成为新的 ContextPack version。

## 5.5 Skill 审批入库

1. 开发人员在 AI 工具中要求总结候选 skill。
2. AI 工具生成 skill candidate。
3. 上传 Agora。
4. 项目经理或技术负责人在 Web UI 审核。
5. 审批通过后成为 approved skill。
6. 后续任务中 AI 工具按触发条件自动使用。

## 5.6 质量人员查询质量状态

1. 质量人员在 AI 工具中询问项目或任务质量状态。
2. AI 工具向 Agora 查询：
   - 任务流程完成情况。
   - 自测记录。
   - 风险清单。
   - 评审结论。
   - 上下文更新状态。
3. AI 工具生成质量摘要。
4. 质量人员可进一步要求生成测试建议或风险报告。

## 5.7 项目经理查询任务状态

1. 项目经理在 AI 工具中询问项目状态。
2. AI 工具向 Agora 查询：
   - 任务列表。
   - 各任务阶段。
   - 阻塞点。
   - 待审批事项。
   - 上下文 freshness。
   - 候选 skill。
3. AI 工具生成项目状态摘要。
4. Web UI 提供可视化看板和审批入口。

## 6. Web UI 功能模块

## 6.1 项目总览

面向项目经理和技术负责人。

展示：

- 项目上下文状态。
- 当前 accepted ContextPack。
- stale / missing / conflict 提示。
- 活跃任务数量。
- 待审批 ContextUpdate。
- 待审批 skill。
- 质量风险摘要。
- 团队资产数量。

## 6.2 上下文治理

功能：

- 查看 ContextPack 版本。
- 查看 ContextUpdate 队列。
- 对比版本差异。
- 查看 source_refs。
- 审批、拒绝、要求修改。
- 查看上下文生成来源和 AI 工具信息。

## 6.3 任务流程审计

功能：

- 查看任务列表。
- 查看任务当前阶段。
- 查看每步产物。
- 查看人工确认记录。
- 查看自测结果。
- 查看上传的 ContextUpdate 和候选 skill。

## 6.4 Skill 管理

功能：

- 查看 approved skill。
- 查看 candidate skill。
- 审批、编辑、废弃。
- 查看 skill 使用历史。
- 查看触发条件和适用范围。

## 6.5 质量视图

功能：

- 项目质量摘要。
- 任务质量状态。
- 测试覆盖和风险。
- 待补充自测。
- 高风险模块。

## 6.6 团队资产

功能：

- 项目文档。
- 团队经验。
- 任务产物。
- writeback。
- 风险和测试经验。

## 6.7 团队和权限

功能：

- 成员管理。
- 角色管理。
- 项目权限。
- 审批权限。
- 审计日志。

## 7. AI 工具接入功能

AI 工具侧需要支持以下 Agora 能力：

## 7.1 项目解析

输入：

- local_path。
- git remote。
- branch。
- commit。
- workspace 状态。

输出：

- project_id。
- project_name。
- context_status。
- workflow_template。
- available_skills。
- required_user_questions。

## 7.2 上下文 freshness check

输出状态：

- fresh。
- missing。
- stale。
- ahead。
- dirty_workspace。
- conflict。

## 7.3 获取团队上下文

AI 工具获取：

- accepted ContextPack。
- source_refs。
- relevant skills。
- task workflow。
- project constraints。

## 7.4 上传上下文

AI 工具上传：

- ContextPack。
- ContextUpdate。
- source_refs。
- generation metadata。
- related task/session。

## 7.5 上传任务产物

AI 工具上传：

- 分析文档。
- 设计文档。
- 评审文档。
- 开发总结。
- 自测报告。
- 上传说明。

## 7.6 上传候选 skill

AI 工具上传：

- skill candidate。
- 触发条件。
- 适用范围。
- 生成依据。
- 关联任务。

## 8. 审批和人工介入

人工介入分两类：

## 8.1 AI 工具内的人审

开发人员在任务执行过程中审查：

- 分析是否正确。
- 设计是否可行。
- 评审意见是否处理。
- 代码是否可接受。
- 自测是否充分。
- 上传内容是否准确。

## 8.2 Web UI 的治理审批

项目经理或技术负责人审查：

- ContextUpdate 是否合并。
- ContextPack 是否 accepted。
- candidate skill 是否入库。
- 任务产物是否符合流程。
- 高风险变更是否需要补充处理。

## 9. 产品原型页面清单

第一版原型应包含：

1. 项目经理驾驶舱。
2. 上下文治理。
3. 任务流程审计。
4. Skill 审批。
5. 质量视图。
6. AI 工具接入状态。

开发者日常视角可在原型中通过“AI 工具侧面板”呈现，而不是把开发者设计成 Web UI 主操作者。

## 10. 黑盒验收口径

完整黑盒验收必须包含：

1. 开发者在 AI 工具中打开本地项目。
2. AI 工具自动解析项目和任务。
3. AI 工具从 Agora 获取项目上下文、流程、skill。
4. 若上下文缺失或过期，AI 工具本地分析并上传。
5. AI 工具按项目流程生成每一步产物。
6. 开发者在 AI 工具中确认关键节点。
7. 任务完成后 AI 工具上传 ContextUpdate 和候选 skill。
8. 项目经理在 Web UI 审批 ContextUpdate。
9. 项目经理在 Web UI 审批 candidate skill。
10. 质量人员或项目经理通过 AI 工具获取项目/任务状态。

只在 Web UI 中手动跑一个辅助查询，不算完整黑盒验收。
