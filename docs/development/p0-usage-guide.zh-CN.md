# Agora P0 试用操作手册

> 这是当前 P0/P1 旧运行路径的历史试用手册，不代表 P2 之后的目标产品流程。后续研发和真实黑盒验收以权威产品设计、技术架构和 P1-P9 Roadmap 为准。

这份文档用于本地验证 P0。当前 P0 支持三类入口：

- Web 管理页：创建项目、初始化本地仓库、查看项目资产和回写。
- Harness API：给 Agent 使用的项目上下文、事件记录、知识回写接口。
- MCP Server：让支持 MCP 的 AI 工具通过工具调用接入 Agora。

## 1. 启动后端 API

在仓库根目录执行：

```bash
cd /Users/daniel/Documents/Agora/.worktrees/agora-p0
.venv/bin/uvicorn apps.api.main:app --reload --port 8011
```

验证：

```bash
curl http://127.0.0.1:8011/health
```

预期返回：

```json
{"status":"ok"}
```

## 2. 启动 Web 管理页

新开一个终端：

```bash
cd /Users/daniel/Documents/Agora/.worktrees/agora-p0/apps/web
NEXT_PUBLIC_AGORA_API_URL=http://127.0.0.1:8011 npm run dev -- -p 3000
```

浏览器打开：

```text
http://127.0.0.1:3000/projects
```

## 3. 通过页面创建项目

在 `Projects` 页面填写：

- Organization：`local-org`
- Project name：`Payment Service`
- Slug：`payment-service`
- Git remote：`git@example.com:payment.git`

点击 `Create`。创建成功后会跳转到项目详情页。

## 4. 初始化项目知识

在项目详情页的 `Initialize from local repository` 表单里输入本地仓库路径。

如果先用 P0 自带样例测试，可以输入：

```text
/Users/daniel/Documents/Agora/.worktrees/agora-p0/tests/fixtures/sample_repo
```

点击 `Initialize` 后会跳转到 `Assets` 页面。能看到 `README.md`、模块信息、代码文件等资产，说明 Agora 已经把项目内容沉淀成共享知识资产。

真实项目测试时，把这个路径换成你的项目本地 clone 路径即可。

如果这个路径不存在，Agora 会使用项目的第一个 `Git remote` 自动执行 `git clone <git_remote> <repo_path>`，clone 成功后继续分析项目。

如果项目没有填写 `Git remote`，或者当前机器没有仓库访问权限，页面会显示错误原因。

## 5. AI 工具如何接入 Agora

P0 提供 stdio MCP Server。AI 工具启动这个 MCP Server 后，就可以调用 Agora 的工具。

MCP Server 命令：

```bash
cd /Users/daniel/Documents/Agora/.worktrees/agora-p0
AGORA_API_URL=http://127.0.0.1:8011 .venv/bin/python -m apps.mcp.server
```

在支持 MCP 的 AI 工具里新增一个 server，配置含义如下：

```json
{
  "name": "agora",
  "command": "/Users/daniel/Documents/Agora/.worktrees/agora-p0/.venv/bin/python",
  "args": ["-m", "apps.mcp.server"],
  "env": {
    "AGORA_API_URL": "http://127.0.0.1:8011"
  }
}
```

不同 AI 工具的 MCP 配置入口不完全一样，但核心都是这三个字段：

- `command`：Python 解释器路径。
- `args`：启动 Agora MCP server 的模块参数。
- `env.AGORA_API_URL`：Agora API 地址。
- `AGORA_DATABASE_URL`：可选数据库地址；默认是 `sqlite+pysqlite:///.agora/agora.db`。

本地重置数据：

```bash
rm .agora/agora.db
```

## 6. Agent 默认使用规则

给 AI 工具配置 Agora MCP 后，建议给 Agent 加一条项目规则：

```text
当我进行当前项目的需求分析、代码实现、测试、Review、总结或风险分析时，默认使用 Agora。
不要每次问我要不要用 Agora。
先调用 agora_start_work，再调用 agora_plan_context 获取项目上下文。
agora_start_work 可以通过用户消息里的项目名称/slug 匹配项目；如果当前工具能读取 git origin remote，也可以把 repo_remote 作为兜底传入。
如果 agora_plan_context 返回 source_refs，必须优先基于这些 Agora 上下文回答。
完成工作前调用 agora_prepare_writeback，把关键结论、实现总结、测试结果沉淀回 Agora。
最后调用 agora_close_work 关闭本次工作。
```

## 7. 在 AI 对话框里怎么测试

确保已经完成：

- API 已启动。
- Web 已创建项目。
- 项目已初始化。
- AI 工具已连接 Agora MCP。

然后在 AI 工具对话框输入：

```text
基于 Agora 分析 df-new-bigdata 项目的核心模块、主要业务流程和潜在风险。
```

预期 Agent 调用流程：

```text
agora_start_work
agora_plan_context
agora_prepare_writeback
agora_close_work
```

如果 Agent 正常调用 Agora，它应该能读到 `README.md`、退款模块、代码文件等项目上下文，而不是只靠当前聊天窗口内容回答。

如果 AI 工具运行在项目仓库目录里，也可以直接说：

```text
基于 Agora 分析这个项目的核心模块、主要业务流程和潜在风险。
```

Agent 应先获取当前仓库的 `git remote get-url origin`，再调用 Agora；如果没法读取 remote，也应至少把用户消息传给 `agora_start_work`，让 Agora 按项目名/slug 解析。

## 8. 查看 Agent 回写结果

Agent 调用 `agora_prepare_writeback` 后，回写会进入草稿状态。

查看：

```text
http://127.0.0.1:3000/projects/{project_id}/writebacks
```

P0 当前 Web 可以查看回写。接受回写暂时通过 API：

```bash
curl -X POST http://127.0.0.1:8011/projects/{project_id}/writebacks/{writeback_id}/accept
```

接受后，这条内容会变成项目资产，并进入 Agora 检索索引。后续 Agent 再问相关问题时，就能读到这次沉淀的知识。

## 9. 不接 AI 工具时的快速自测

如果你只是想确认 P0 主流程能跑通：

```bash
cd /Users/daniel/Documents/Agora/.worktrees/agora-p0
.venv/bin/python scripts/run_p0_demo.py
```

这个脚本会自动跑完：

```text
创建项目 -> 初始化资产 -> 获取上下文 -> 技能输出 -> 准备回写 -> 接受回写 -> 再次检索
```

## 10. P0 边界

P0 已经可以验证团队 AI 项目知识闭环，但还不是生产级 SaaS：

- Git 初始化优先使用本地仓库路径；如果路径不存在，P0 可以使用项目第一个 Git remote 自动 clone。
- P0 还没有做远程 Git 凭证托管、定时 pull、分支选择。
- 数据库默认是本地文件 SQLite：`.agora/agora.db`，服务重启后项目和资产会保留。
- 索引当前使用 Fake Qdrant/OpenSearch 实现，适合验证流程，不适合生产检索规模。
- Web 是必要管理页，不是完整产品后台。
- 权限、组织隔离、审计、部署运维还没有进入 P0。
