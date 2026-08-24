# P2 真实 AI 工具黑盒验证

本文档用于验证 P2：AI 工具通过 Agora MCP 接入项目上下文，Web 只做可视化和审计，不再提供“测试器”或“模拟 AI 工具上传”的产品入口。

## 1. 准备环境

先准备生产式本地 token。不要设置 `AGORA_TEST_AUTH_BYPASS`。

```bash
export AGORA_BOOTSTRAP_HUMAN_TOKEN=p2-local-human-token
export AGORA_BOOTSTRAP_AGENT_TOKEN=p2-local-agent-token
export AGORA_BOOTSTRAP_ORG_ID=local-org
export AGORA_DATABASE_URL=sqlite+pysqlite:///.agora/p2-blackbox/agora.db
```

生成黑盒项目、真实本地 repo 和 Web/API 环境文件：

```bash
.venv/bin/python scripts/prepare_p2_blackbox.py --root .agora/p2-blackbox --database-url "$AGORA_DATABASE_URL"
source .agora/p2-blackbox/p2-blackbox.env
```

脚本只会创建项目和初始化资产，不会预创建 WorkSession、ContextPack 或 AI 工具结果。

## 2. 启动服务

API：

```bash
.venv/bin/uvicorn apps.api.main:app --host 127.0.0.1 --port 8011
```

Web：

```bash
cd apps/web
NEXT_PUBLIC_AGORA_API_URL=http://127.0.0.1:8011 AGORA_WEB_HUMAN_TOKEN="$AGORA_WEB_HUMAN_TOKEN" npm run dev -- -p 3000
```

MCP/AI 工具侧需要使用 `AGORA_AGENT_TOKEN` 指向同一个 API。

## 3. AI 工具黑盒操作

在 AI 工具里打开 `.agora/p2-blackbox/payments-core` 仓库，然后让 AI 工具执行一个真实研发任务：

```text
请接入 Agora 项目上下文，开始 PAY-241：支付状态流转审计。先获取项目上下文；如果 Agora 提示需要本地分析，请读取当前仓库代码和 docs 后上传上下文。完成分析、设计、自测记录，并关闭本次工作。
```

验收时不要手工调用 HTTP API。允许 AI 工具通过 MCP 调用：

- `agora_start_work`
- `agora_prepare_context`
- `agora_fetch_context_ref`
- `agora_close_work`

## 4. Web 黑盒操作

打开 `http://127.0.0.1:3000/projects`。

检查：

- 能看到 `Payments Core` 项目。
- 进入项目后能看到 `Work items`、`Context`、`Sessions` 入口。
- `Work items` 中出现 `PAY-241`，状态、会话数量、上下文状态可见。
- 进入 WorkItem detail 后能看到 WorkSession、latest context state、nullable capability pins。
- 进入 `Context` 后页面是只读 `Context state`，不能看到 `Context Tester` 或 `Run context query`。
- 进入 `Sessions` 和 Session detail 后能回跳到对应 WorkItem。

## 5. 通过标准

- AI 工具能自动通过本地 repo identity 解析到项目；歧义时才需要用户回答。
- Agora 服务端 start-work 请求不包含本地绝对路径、Git 凭据或源码内容。
- 缺上下文时，Agora 要求 AI 工具分析本地项目；不是 Agora 服务端扫描本地仓库生成上下文。
- 上下文是 provisional，P3 前不能声称 accepted ContextRevision。
- 同一个 idempotency key 重试返回同一个 WorkSession；换 payload 返回冲突。
- Web 能展示任务、会话和上下文状态，不提供辅助测试入口。
