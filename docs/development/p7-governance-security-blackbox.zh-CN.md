# P7 Governance and Security 黑盒验证步骤

目标：验证 Agora 的团队治理边界能阻止 AI 凭证和普通成员审批团队知识，并能在 Web `Security audit` 中审计审批允许和拒绝原因。

## 验证边界

- 用户只通过 AI 工具和 Web 页面完成验证。
- 不要求用户手动调用 HTTP API。
- AI 凭证不能审批 ContextProposal 或 SkillCandidate。
- 普通项目成员不能审批团队知识；只有 owner、admin、reviewer 可以审批。
- 敏感审批动作必须记录 actor、credential kind、action、target、decision 和 reason。

## 前置条件

1. Agora API 和 Web 已启动。
2. AI 工具已接入 Agora MCP，使用 agent token。
3. Web 使用 human token。
4. 已存在一个项目。

## 步骤 1：AI 工具提交待审上下文或 Skill

在 AI 工具中输入：

```text
请通过 Agora 为当前项目提交一个待审批的 ContextProposal 或 SkillCandidate。
内容可以是一次真实任务中的上下文总结或团队经验沉淀。
提交后不要审批，让 Web 人工审批。
```

期望：

- AI 工具可以提交待审对象。
- 待审对象状态为 `submitted` 或 `candidate`。

## 步骤 2：验证 AI 凭证不能审批

在 AI 工具中输入：

```text
请尝试审批刚才提交的待审对象。
如果 Agora 拒绝，请原样说明错误码。
```

期望：

- Agora 返回 403。
- 错误码为 `HUMAN_CREDENTIAL_REQUIRED`。
- AI 工具说明 AI 凭证不能审批团队知识。

## 步骤 3：验证 Web 人工审批可以通过

打开 Web：

```text
http://127.0.0.1:3000/projects
```

操作：

1. 进入项目。
2. 如果验证 ContextProposal，进入 `Context`，打开 proposal detail，点击审批。
3. 如果验证 SkillCandidate，进入 `Skills`，使用 `Publish approved version` 发布。

期望：

- owner/admin/reviewer 人工凭证可以审批。
- 审批后的对象变为 approved。
- ContextApproval 或 SkillVersion 保留审批人信息。

## 步骤 4：查看 Security audit

回到项目主页，点击 `Security audit`。

期望：

- 能看到 AI 凭证审批被拒绝的审计事件。
- `actor_credential_kind = agent`。
- `decision = deny`。
- `reason = HUMAN_CREDENTIAL_REQUIRED`。
- 能看到人工审批允许的审计事件。
- `decision = allow`。
- `reason = PROJECT_APPROVER`。

## 步骤 5：普通成员审批被拒绝

如果测试环境里准备了普通 member 人工账号，用该账号打开 Web 并尝试审批同类对象。

期望：

- Agora 返回 403。
- 错误码为 `PROJECT_ROLE_REQUIRED`。
- `Security audit` 出现一条 `decision = deny`、`reason = PROJECT_ROLE_REQUIRED` 的事件。

## 通过标准

- AI 凭证不能审批 ContextProposal 或 SkillCandidate。
- 普通 member 不能审批团队知识。
- owner/admin/reviewer 可以审批。
- Web `Security audit` 能看到审批允许和拒绝的原因。
- 审计记录不暴露 bearer token 原文，只显示 actor、credential kind 和诊断级信息。
- 用户不需要手动调用任何 HTTP API。
