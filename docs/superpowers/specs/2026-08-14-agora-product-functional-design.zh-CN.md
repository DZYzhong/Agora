# Agora 产品功能设计

> 文档状态：当前产品设计单一事实源
>
> 更新时间：2026-08-14
>
> 适用范围：P2-P9 产品设计、技术设计、研发计划和黑盒验收
>
> 配套原型：`docs/prototypes/agora-real-team-workflow-prototype.html`

## 1. 产品定义

Agora 是软件研发团队的 AI Project Harness。

它运行在团队成员使用的 AI 工具背后，为不同角色和不同 AI 工具提供一致、可信、可追溯的项目上下文，执行项目工作流程，沉淀可复用 Skill，记录任务过程，并将有价值的项目经验治理成团队资产。

Agora 的核心价值不是“存更多资料”，而是让 AI 工具在正确的项目、正确的任务、正确的流程和正确的上下文下工作。

典型体验：

```text
开发者 / 质量人员 / 项目经理在自己的 AI 工具中工作
-> AI 工具自动调用 Agora Harness
-> Agora 解析项目和工作项
-> Agora 返回最小必要 ContextBundle、流程和 Skill
-> AI 工具在本地读取代码并辅助完成任务
-> Agora 记录流程、证据和人工确认
-> AI 工具提交 ContextProposal 和 SkillCandidate
-> 负责人在 Web UI 审批并形成新的团队资产
```

Agora Web UI 是治理、审批、审计和可视化入口，不是开发者的主要工作界面。

## 2. 最终目标

### 2.1 共享可信项目认知

同一个项目中的开发人员 A、B、C，无论使用 Codex、Cursor、Claude Code 或内部 AI 工具，都应获得同一条经过治理的项目上下文主线。

团队上下文必须：

- 有明确版本。
- 能说明覆盖哪个仓库和代码版本。
- 每个关键事实可追溯到来源。
- 能被评审、拒绝、修订和回滚。
- 不被单个开发者的临时工作区直接覆盖。

### 2.2 降低重复分析和 token 成本

Agora 不向 AI 工具一次性返回整个知识库。Harness 根据角色、任务意图、工作阶段和 token budget 生成最小必要 ContextBundle，AI 工具按需展开来源。

### 2.3 规范 AI 工具工作方式

项目可以配置轻量、标准和高风险工作流。AI 工具按照项目流程完成分析、设计、评审、开发、自测和交付，并在需要人工判断的地方暂停等待确认。

默认标准流程在每一步都要求开发者或指定角色在 AI 工具中审查产物；只有经过批准的轻量 WorkflowVersion 才能减少人工节点。

### 2.4 沉淀项目和团队经验

任务中的决策、风险、测试方法、问题处理经验和重复做法可以形成：

- ContextProposal。
- WorkArtifact。
- QualityEvidence。
- SkillCandidate。
- 经过批准的 ContextRevision 和 SkillVersion。

### 2.5 降低人员能力差异的影响

Agora 通过共享上下文、项目流程、检查清单、质量证据和 Skill，让不同经验水平的人员获得更一致的工作起点和交付标准。

### 2.6 低感知自动化

开发者不需要打开 Agora 检查上下文，也不需要记住一组 Agora 命令。AI 工具应自动完成项目解析、freshness 判断、上下文准备、过程记录和任务收尾。

只有项目不确定、敏感内容上传、人工审批、上下文冲突和高风险质量问题才打断用户。

## 3. 产品边界

### 3.1 Agora 负责

- 项目和仓库身份。
- 工作项、工作会话和项目流程。
- 上下文版本、来源、freshness、评审和合并。
- Skill 生命周期和运行记录。
- 任务产物、测试证据和质量状态。
- 团队权限、审批策略和审计。
- 为 AI 工具提供稳定的 Harness 接口。

### 3.2 AI 工具负责

- 访问本地源码、文档和 Git 工作区。
- 使用用户已经配置的模型理解本地项目。
- 根据 Agora 返回的结构和策略生成上下文候选。
- 辅助分析、设计、编码、测试和总结。
- 在 AI 工具中发起人工确认。

### 3.3 Agora 默认不负责

- 作为开发者日常聊天或编码界面。
- 默认拉取、托管或扫描客户源码。
- 替代 Git、CI、需求系统或项目管理系统。
- 在没有代码访问能力的情况下假装完成源码分析。
- 绕过人工或项目策略直接发布 AI 生成的团队知识。
- 强制所有任务使用同样重量的流程。

服务端仓库导入可以保留为显式授权的辅助能力，但不是客户主流程，也不能作为真实黑盒验收的替代路径。

## 4. 产品原则

### 4.1 Agent-first

开发、测试、产品和项目管理角色主要通过自己的 AI 工具使用 Agora。

### 4.2 Harness-first

AI 工具调用任务级 Harness 能力，不直接操作数据库、向量库或内部领域 CRUD。

### 4.3 Customer-local source

客户源码和未提交变更默认留在本地工作区或 CI runner。Agora 接收经过策略控制的结构化上下文、来源锚点、产物和证据。

### 4.4 Context is not search results

团队上下文是经过组织、压缩、引用和治理的项目认知，不是关键词结果列表或源码拼接。

### 4.5 Progressive disclosure

默认返回 L0/L1 工作上下文，源码片段和大型文档通过 source reference 按需展开。

### 4.6 Human-in-control

AI 可以生成候选内容，但关键流程确认、上下文主线更新、Skill 发布和高风险豁免必须遵循人工审批策略。

### 4.7 Immutable accepted knowledge

已批准的 ContextRevision、WorkflowVersion 和 SkillVersion 不原地修改。修订通过新版本完成，历史记录可审计和回滚。

### 4.8 Quiet automation

能自动完成且风险可控的操作在后台完成；需要人判断时才提示，并说明原因、影响和建议动作。

### 4.9 Vendor-neutral

Agora 协议不依赖某一个 AI 工具或模型供应商。不同工具只要具备最小文件、Git 和工具调用能力即可接入。

## 5. 用户角色

## 5.1 开发人员

主入口：AI 工具、IDE 和 Terminal。

开发人员需要：

- 自动获得当前任务所需项目上下文。
- 知道项目流程、技术约束和已批准 Skill。
- 在 AI 工具中审核分析、设计、代码和自测结果。
- 不手动管理 Agora freshness 和同步状态。
- 在任务结束时低成本沉淀经验。

## 5.2 质量人员

主入口：AI 工具；Web UI 用于审计和质量看板。

质量人员需要：

- 获取项目和工作项的质量状态。
- 查看测试证据、未覆盖风险和回归范围。
- 检查任务是否遵循项目流程。
- 提交质量结论或要求补充证据。

## 5.3 产品或需求角色

主入口：AI 工具。

该角色可以利用项目上下文检查需求歧义、历史约束、影响范围和验收条件，但不直接审批技术上下文。

## 5.4 项目经理

主入口：AI 工具和 Agora Web UI。

项目经理负责：

- 查看 WorkItem 而不是零散 Session。
- 查看任务阶段、负责人、阻塞和待审批事项。
- 配置或选择项目流程。
- 监督过程完整性和交付状态。
- 审批其职责范围内的流程、状态和团队资产。

项目经理不必独自承担所有技术事实审核。项目可以要求技术负责人或 Context Steward 审批技术上下文。

## 5.5 技术负责人 / Context Steward

主入口：AI 工具和 Agora Web UI。

负责：

- 审核 ContextProposal 和 ContextRevision。
- 处理并发更新和上下文冲突。
- 维护技术流程、质量门槛和项目 Skill。
- 判断高风险技术产物是否可以通过。

## 5.6 管理员

负责组织、成员、项目、AI 工具凭证、集成、权限、审批策略、数据保留和审计配置。

## 5.7 AI 工具

AI 工具是 Agora 的主要执行客户端，而不是被审计的“用户角色替代品”。它代表经过认证的真实用户执行本地分析和 Harness 流程，并记录工具、模型和版本信息。

## 6. 核心产品对象

## 6.1 Organization 和 Membership

定义团队边界、成员身份和组织级角色。

## 6.2 Project 和 RepositoryIdentity

`Project` 是 Agora 团队资产的根对象。

`RepositoryIdentity` 表示项目关联的规范化仓库身份，包括 provider、host、namespace、repository、默认分支和不含凭证的 canonical remote。

同一项目可以关联多个仓库，但首个版本可以限制一个主仓库。

## 6.3 LocalWorkspaceObservation

AI 工具在本地采集的工作区观察：

- repository identity。
- branch。
- commit SHA。
- clean / dirty。
- commit relationship。
- changed path 摘要。
- 工具生成的匿名 workspace fingerprint。

本地绝对路径默认不上传 Agora。Git remote 中的用户名、密码和 token 必须在客户端清理。

## 6.4 WorkItem

WorkItem 是项目经理关注的真实任务对象。

包含：

- 标题和描述。
- 来源和外部任务编号。
- 当前负责人和参与者。
- 当前阶段、状态和风险等级。
- 使用的 WorkflowVersion。
- 关联分支、提交、PR。
- 多个 WorkSession。
- ContextProposal、SkillCandidate 和质量证据。

一个 WorkItem 可以跨多人、跨多次 AI 工具会话完成。

每个 WorkItem 只有一个负责整体进度的 WorkflowExecution。WorkItem 阶段由该流程、阻塞和审批状态派生；WorkSession 贡献步骤尝试、产物和证据，但不能各自覆盖项目经理看到的任务阶段。

## 6.5 WorkSession

WorkSession 是一个用户通过一个 AI 工具执行 WorkItem 的一次工作会话。

记录：

- 用户和 AI 工具。
- pinned ContextRevision、WorkflowVersion 和 SkillVersion。
- 会话事件和调用轨迹。
- 当前参与的流程步骤尝试。
- 人工确认。
- 任务产物和测试证据。
- 同步和关闭状态。

## 6.6 WorkflowDefinition 和 WorkflowVersion

WorkflowDefinition 表示一个逻辑流程；WorkflowVersion 是不可变版本。

每一步可以定义：

- 目标和提示要求。
- 必填产物。
- 完成规则。
- 人工确认角色。
- 是否允许跳过或豁免。
- 失败后可执行动作。

项目可以提供轻量、标准、高风险等不同流程配置。

## 6.7 ContextStream 和 ContextRevision

ContextStream 是项目某个上下文通道，例如默认分支 `main` 的主上下文。

ContextRevision 是不可变的已版本化项目认知，内容包括：

- 项目概览和技术栈。
- 业务域、模块和关键流程。
- 重要代码路径和文档路径。
- 决策、约束、风险和测试策略。
- 结构化 source anchors。
- 覆盖的仓库、分支和 commit。
- 生成来源和审批记录。

每个 ContextStream 只有一个当前 accepted head，但保留完整历史。

## 6.8 ContextProposal

AI 工具提交的上下文候选变更，类型包括：

- `initial`：首次建立项目上下文。
- `refresh`：代码版本变化后的上下文刷新。
- `task_update`：工作项结束后的增量经验。
- `correction`：修正错误事实。

ContextProposal 基于明确的 ContextRevision。审批时如果 accepted head 已变化，Proposal 进入 `needs_rebase`，不能覆盖新版本。

Proposal 必须声明目标 ContextStream 和 branch。feature branch 未合并前只能进入对应 branch stream 或保持 session-local；证明 commit 已进入目标 branch 后，才能生成或 rebase 默认分支 refresh Proposal。

## 6.9 ContextBundle

Harness 为当前用户、WorkItem 和工作阶段准备的最小必要上下文。

分层：

- L0 Session Brief：项目、任务、关键约束和下一步。
- L1 Working Context：相关模块、流程、风险、决策、Skill 和质量要求。
- L2 Deep References：按需获取的源码锚点、文档或历史产物。

ContextBundle 是临时的任务视图，不等同于团队 ContextRevision。

Token budget 约束完整的 L0/L1 序列化内容，包括事实、流程要求、Skill 摘要和 source-ref metadata。L2 source ref 每次展开使用单独预算。

## 6.10 WorkArtifact

任务过程文档，例如分析、设计、评审、变更摘要、自测、交付说明和质量报告。

产物应支持：

- 保存到项目本地。
- 上传内容或只上传路径/hash。
- 关联 WorkItem、WorkSession 和 WorkflowStepRun。
- 记录生成工具和人工确认。

## 6.11 QualityEvidence

结构化质量证据，例如测试命令、CI run、测试结果、覆盖范围、失败信息、评审结论和未覆盖风险。

质量视图应优先展示证据，不把 AI 摘要当作已验证事实。

## 6.12 Skill 和 SkillVersion

Skill 是团队可复用工作方法；SkillVersion 是不可变的已发布版本。

Skill 来源：

- 项目负责人维护。
- 管理员通过 AI 工具生成。
- 开发人员任务中提交 SkillCandidate。
- 多次已批准任务经验中提炼。

SkillCandidate 不能未经授权直接成为 approved SkillVersion。

## 6.13 Approval 和 AuditEvent

Approval 记录审批对象、策略、审批人、意见和结果。

AuditEvent 记录关键命令和状态变化。普通数据库审计提供可追溯性；需要防篡改时可以使用 hash chain 或外部审计存储。

## 7. 端到端使用流程

## 7.1 项目接入

1. 管理员或项目经理创建 Project。
2. 配置规范化 RepositoryIdentity、默认分支、成员和审批策略。
3. 选择或生成 WorkflowVersion。
4. 配置允许上传的内容、敏感路径和源码片段策略。
5. 不要求 Agora 服务端克隆客户仓库。

## 7.2 开发者开始工作

1. 开发者在本地项目中向 AI 工具描述任务。
2. Local Connector 采集并清理 LocalWorkspaceObservation。
3. AI 工具自动调用 `agora_start_work`。
4. Harness 解析 Project，并匹配或创建 WorkItem。
5. 无法可靠识别任务时，AI 工具只询问一个必要问题。
6. Agora 创建 WorkSession，并固定 ContextRevision、WorkflowVersion 和 SkillVersion。
7. Harness 返回上下文状态、ContextBundle 计划、流程当前步骤和建议动作。

## 7.3 获取或生成上下文

### 上下文可用

Harness 根据任务意图和 token budget 返回 ContextBundle。AI 工具只在需要时展开 source reference。

### 上下文缺失

1. AI 工具读取本地代码和文档。
2. 使用 Agora 定义的结构化 schema 生成 initial ContextProposal。
3. 开发者确认允许上传的内容。
4. Agora 保存 pending review Proposal。
5. 技术负责人审批后生成 accepted ContextRevision。

### 上下文可能过期

1. Harness 返回代码关系、工作区状态和上下文覆盖状态。
2. AI 工具仅分析当前 ContextRevision 到本地 revision 的相关变化。
3. 生成 refresh ContextProposal。
4. 当前任务可以使用带来源标识的 session-local context 继续工作。
5. 团队 ContextStream 在审批前保持不变。

### Dirty workspace

未提交变更可以用于当前 WorkSession，但默认不能进入团队 ContextStream。任务关闭后，只有关联到明确 commit/PR 的内容才可提交为团队上下文候选。

## 7.4 自动 freshness

Agora 使用双通道感知代码变化：

- Pull：AI 工具在 start、continue 和 close 时上报 LocalWorkspaceObservation。
- Push：Git webhook 或 CI 在 push、merge、tag 时上报 RevisionSignal。

收到新 revision 后：

1. Agora 标记相关 ContextStream 为 `potentially_stale`。
2. 记录哪些 WorkSession 和 ContextProposal 仍基于旧 head。
3. 具备本地代码访问权的 AI 工具或 CI Agent 生成 refresh Proposal。
4. 审批合并后生成新的 ContextRevision。
5. 其他 AI 工具在下一次 Harness 调用时自动收到新 head。

Agora 无法在没有源码访问权的情况下自行生成真实刷新内容；它负责自动检测、协调生成、治理合并和分发结果。

## 7.5 项目工作流

标准流程可以是：

```text
analysis -> design -> review -> implementation -> self_test -> delivery
```

每一步：

1. Harness 返回当前目标、所需上下文、适用 Skill 和必填产物。
2. AI 工具在本地完成工作并生成产物。
3. 开发者在 AI 工具中检查需要人工确认的内容。
4. 产物保存到本地并按项目策略同步 Agora。
5. Harness 校验完成条件并进入下一步。

标准流程默认每一步都有人在 AI 工具中审查。低风险任务可以使用经过项目批准的轻量流程；高风险任务可以要求技术负责人和质量人员共同确认。

## 7.6 任务收尾和知识沉淀

1. AI 工具汇总代码变化、决策、测试、风险和遗留项。
2. Harness 校验必填步骤和 QualityEvidence。
3. AI 工具提交 task_update ContextProposal。
4. AI 工具可以提交 SkillCandidate。
5. WorkItem 进入待交付或待审批状态。
6. 负责人在 Web UI 审核上下文和 Skill。
7. 审核通过后形成新的 ContextRevision 或 SkillVersion。

## 7.7 项目经理工作流

项目经理通过 AI 工具或 Web UI 获取：

- WorkItem 状态和阶段。
- 负责人、参与者和阻塞。
- 流程完成度和缺失产物。
- 待审批 ContextProposal 和 SkillCandidate。
- 项目上下文 freshness。
- 高风险质量问题。

项目状态基于 WorkItem 聚合，不以 WorkSession 数量代替任务进度。

## 7.8 质量人员工作流

质量人员查询项目或 WorkItem 时，Agora 返回结构化 QualityEvidence、流程状态、风险和上下文变化。AI 工具可以基于这些证据生成测试建议，但必须区分事实、AI 推断和未验证结论。

## 8. AI 工具产品能力

开发者正常使用时，AI 工具应自动调用以下高层能力：

- 开始或恢复工作。
- 准备任务上下文。
- 按需展开来源。
- 完成工作流步骤并同步产物。
- 记录测试和质量证据。
- 提交上下文候选和 SkillCandidate。
- 关闭工作会话。

项目经理和质量人员还可以：

- 查询项目和 WorkItem 状态。
- 查询质量状态。
- 查询待审批事项。

底层上传、freshness 计算和项目解析可以有调试 API，但不要求普通用户直接调用。

## 9. Web UI 信息架构

## 9.1 项目驾驶舱

- ContextStream 状态和当前 revision。
- 活跃、阻塞和待审批 WorkItem。
- 质量风险和缺失证据。
- 待审批 ContextProposal 和 SkillCandidate。

## 9.2 工作项与流程

- WorkItem 列表、负责人、阶段和风险。
- 关联 WorkSession。
- WorkflowStepRun、产物和人工确认。
- 关联 commit、PR、ContextProposal 和 SkillCandidate。

## 9.3 上下文治理

- ContextStream 和 revision 历史。
- Proposal 队列和差异对比。
- source anchors 和生成元数据。
- accept、request changes、reject 和 rebase。

## 9.4 Skill 治理

- SkillCandidate 审批。
- SkillVersion 发布和废弃。
- 触发条件、适用范围和运行历史。

## 9.5 质量视图

- 项目和 WorkItem 的 QualityEvidence。
- 测试状态、失败和未覆盖风险。
- 流程合规情况和质量趋势。

## 9.6 团队资产和审计

- 项目文档、任务产物、决策和经验。
- 审批历史、AI 工具调用和关键状态变化。

## 9.7 团队、策略和集成

- 成员、角色和项目权限。
- 上传和敏感内容策略。
- Workflow 和审批策略。
- Git、CI、任务系统和 AI 工具接入状态。

## 10. 自动化和打断策略

### 默认静默完成

- 项目解析结果唯一。
- accepted ContextRevision 可直接复用。
- 低风险只读上下文获取。
- 过程事件和非敏感 metadata 同步。
- 幂等重试和断网恢复。

### 必须提示用户

- 项目或 WorkItem 无法可靠识别。
- 上传可能包含敏感内容。
- 当前步骤要求人工确认。
- ContextProposal 与当前 head 冲突。
- 高风险任务缺少必须证据。
- 用户操作会影响团队共享知识。

## 11. 权限和审批

权限以经过认证的用户、组织成员关系和项目角色为基础。AI 工具使用用户授权的 scoped credential，不能通过请求参数自行声明组织身份。

项目可以分别配置：

- ContextProposal 审批角色和人数。
- SkillCandidate 审批角色。
- WorkflowVersion 发布权限。
- 高风险步骤确认角色。
- 低风险自动接受策略。

技术上下文默认由技术负责人或 Context Steward 审批；项目经理负责项目状态和流程治理，也可以在具备相应项目角色时参与审批。

## 12. 异常和降级体验

- Agora 暂时不可用：AI 工具允许继续本地工作，但明确标记团队上下文未验证，并在本地排队待同步产物。
- 上下文冲突：不覆盖 accepted head，创建 needs_rebase Proposal。
- 工作流服务失败：保留本地产物和幂等键，恢复后继续同一 WorkSession。
- AI 输出不符合 schema：要求 AI 工具修正，不将无效内容写入治理队列。
- 搜索索引不可用：回退到 accepted revision 的结构化内容和数据库检索。

## 13. 产品成功指标

- 开发者无需打开 Web UI 即可使用团队上下文和流程。
- 开始任务时自动解析 Project 和 WorkItem 的成功率可度量。
- 相同任务下 ContextBundle 相比全量分析明显减少 token。
- accepted ContextRevision 有完整来源和版本血缘。
- 多人并发更新不会静默覆盖团队上下文。
- 项目经理可以从 WorkItem 看到真实进度和阻塞。
- 质量结论可以追溯到测试或评审证据。
- SkillCandidate 可以经过审批成为可复用 SkillVersion。
- 断网和重试不会创建重复任务、产物或上下文版本。

## 14. 完整黑盒验收场景

完整黑盒必须使用真实 AI 工具、真实本地软件项目和真实 Agora 服务：

1. 管理员在 Web UI 创建项目、成员、流程和审批策略。
2. 开发者 A 在 AI 工具中打开本地项目并描述真实任务。
3. AI 工具自动解析 Project 和 WorkItem。
4. 项目缺少上下文时，AI 工具本地分析并提交 initial ContextProposal。
5. 技术负责人在 Web UI 审批，形成首个 accepted ContextRevision。
6. 开发者 B 开始另一个任务，AI 工具自动复用团队上下文和 Skill。
7. AI 工具按 WorkflowVersion 生成产物并要求人工确认。
8. 开发者完成代码和真实自测，QualityEvidence 同步 Agora。
9. AI 工具关闭 WorkSession 并提交 task_update ContextProposal 和 SkillCandidate。
10. 负责人在 Web UI 审批并生成新版本。
11. Git push 或 CI 上报新 revision，Agora 自动更新 freshness 状态。
12. 开发者 C 再次开始工作时自动获得新的 ContextRevision。
13. 项目经理通过 AI 工具或 Web UI 查看 WorkItem 状态和阻塞。
14. 质量人员通过 AI 工具获取有证据支撑的质量状态。

以下不算完整黑盒验收：

- 只在 Web UI 手动调用辅助查询。
- 使用 fake LLM、fake index 或测试 fixture 代替真实 AI 工具路径。
- 由 Agora 服务端读取本地路径来假装模拟客户 AI 工具。
- 只验证 API 返回，不验证角色实际工作结果。

## 15. 当前范围决策

- 采用 Agent-first、Harness-first 产品方向。
- 客户源码默认留在本地或 CI runner。
- Web UI 聚焦治理、审批、审计和状态可视化。
- WorkItem 与 WorkSession 分离。
- ContextRevision、WorkflowVersion、SkillVersion 不可变。
- Freshness 使用多维状态和 Pull + Push 双通道信号。
- 项目上下文生成主要由客户已有 AI 工具完成。
- P2-P9 实现顺序以统一 Roadmap 为准。
