# PR3 起步计划：团队身份与授权（2026-09-03 kickoff）

> 定位：`docs/superpowers/plans/2026-08-28-agora-production-readiness-implementation.md` Chunk 3 的执行计划（起步批次）。PR3 exit gate：`PR3-RBAC-*` principal×action 矩阵 100% 通过 + 真实身份完成角色黑盒。

## 1. 差距分析（相对 PR3 Outcomes）

| PR3 Outcome | 现状 | 差距 |
|---|---|---|
| Admin 管理用户/组织/项目成员 | 用户增删/激活/重置有 API；org membership 存在 | **项目成员管理 API/UI 缺失**；成员角色不可在 UI 调整 |
| Developer/Reviewer/PM/Quality/Admin/Viewer 产品角色 | 仅 org admin/member 与 project owner/member 二元 | 角色模型未产品化 |
| Personal/Agent/CI Token 生命周期（签发/scope/过期/轮换/吊销） | env bootstrap 建 agent/ci/human；activation/reset 单次凭据；revoke 端点存在 | **无签发 API/UI、无 scope/expiry 模型、无轮换流程**（UI 层） |
| Disabled 用户立即失效 | `disable` 端点存在 | 需核对 disable 是否立即使会话/凭据/approval grant 全失效（含 WebSession 校验路径） |
| 敏感身份/角色/凭据操作全审计 | SecurityAuditEvent 已建 | 补齐缺失 action 审计点 |

## 2. 角色矩阵草案（首批规格输出）

- 组织级：`owner`（bootstrap）、`admin`、`member`（现状已有）。
- 项目级产品角色（映射到现有表字段的受控枚举）：`admin`（项目负责人）、`reviewer`、`pm`、`quality`、`developer`、`viewer`。
- 首批 RBAC 矩阵覆盖动作：项目成员管理（admin）、审批（admin/reviewer/quality? 按产品设计确认）、用户管理（org admin）、只读（viewer）——矩阵以表格写入本计划附档并随 B1 落成测试参数。

## 3. 批次与验收

| 批次 | 内容 | 验收 |
|---|---|---|
| B0（本批=起步） | 差距清单 + 角色矩阵规格 + 现状测试盘点（disable 传播路径、revoke 语义、审计缺口） | 本计划文档 + 盘点结论记录 |
| B1 | 项目/组织成员管理 API（加成员/改角色/移除）+ 角色枚举迁移 | pytest 绿 + RBAC 单测 |
| B2（已完成 2026-09-03）| API token 生命周期：签发（human/agent/ci + label + expires_at）/列出（隐藏明文）/轮换（吊销旧+发新）+ 审计 | `tests/integration/api/test_credentials_api.py` 5 passed + 迁移 0018（credentials.label）|
| B3 | disable/enable 全链失效（web session、credentials、approval grants）+ 回归 | pytest 绿 |
| B4 | 用户/成员管理 UI（与 Web UI 重设计批次协同） | tsc/build + web-config 契约 |
| B5 | principal×action 矩阵自动化 + docs: record + roadmap | PR3-RBAC-* 绿 |

## 4. 依赖与顺序

- 依赖 C1（首页/用户页清理）与 UI 重设计评审结论（B4 样式基线）。
- 本机可完整自动化 B1-B3/B5；B4 依赖 UI 评审通过；真实多身份黑盒仍需用户配合。

## 5. B0 现状盘点结论（2026-09-03 完成）

代码走查（`auth_admin.set_user_enabled/revoke_credential`、`auth_session.resolve_session_principal`、`approval_grants.require_approval_capability`、`IdentityRepository`）：

| 项 | 现状 | PR3 差距 |
|---|---|---|
| Disable 后凭据 | disable 立即 `revoke_user_credentials`（human/agent/ci/activation/reset 全部 revoked）+ 置 disabled + 审计 `user.disable`（含吊销数） | ✅ 已满足 |
| Disable 后 Web 会话 | `resolve_session_principal` 发现 user 非 active → 吊销会话并拒绝；下一请求即失效 | ✅ 已满足（惰性吊销+即时拒绝） |
| Disable 后审批 grant | grant 需以本人 web_session 主体消费；用户禁用后主体解析失败 → grant 实际不可用 | ⚠️ 行为正确但**未显式吊销 grant 行**、无审计；建议 B1/B3 补显式吊销+审计 |
| 凭据吊销（单条） | org admin `revoke_credential` + 审计 `credential.revoke`；endpoint 已有 | ✅ 已满足（UI 缺，B2/B4） |
| 成员/角色管理 | 仅 bootstrap/org admin 二元；project_memberships 有 role 字段但无管理 API/UI | ❌ B1 核心 |
| Token 生命周期（签发/scope/过期/轮换） | 仅 env bootstrap + activation/reset 单次凭据 | ❌ B2 核心 |
| RBAC principal×action 矩阵自动化 | 部分（审批拒绝矩阵测试存在） | ❌ B5 补全 |
| 审计覆盖面 | user.disable/enable、credential.revoke/reset_issue、user.create、审批决策等已审计 | ⚠️ 补 grant 吊销/签发、成员变更审计（B1/B2） |

**B0 结论**：disable 传播主线已达标（凭据即时吊销、会话惰性吊销+拒绝、grant 因主体不可达而失效）；PR3 首批代码批次 = B1（组织/项目成员管理 API + 角色受控枚举 + 显式 grant 吊销与成员变更审计），随后 B2 token 生命周期、B5 矩阵自动化。
