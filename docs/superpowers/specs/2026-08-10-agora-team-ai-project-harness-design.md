# Agora Team AI Project Harness Design

## Summary

Agora is a team-level AI project harness. It turns existing project assets into shared project understanding, exposes that understanding to AI agents, orchestrates reusable team skills, records AI work sessions, and writes useful results back into the project knowledge base.

Agora is not primarily a web knowledge base, a chat product, or a standalone MCP server. The core product is the harness layer behind AI agents.

The primary user experience is:

```text
Developer / QA / Product / PM works in their AI agent chat
-> Agent calls Agora automatically
-> Agora resolves project and task
-> Agora returns the smallest useful ContextPack
-> Agora orchestrates relevant Skills
-> Agent completes the work
-> Agora records and writes back reusable knowledge
```

Minimal Web exists only for project setup, connector configuration, analysis inspection, skill review, session inspection, and writeback approval.

## Goals

- Let different roles and different AI tools share one project understanding.
- Let AI agents get precise project context without users repeatedly explaining the project.
- Reduce token waste by giving agents layered, task-specific context packs.
- Turn repeated team workflows into reusable, versioned, reviewable skills.
- Make AI work results durable by writing summaries, risks, decisions, and test suggestions back into Agora.
- Support multi-project SaaS and private deployment from the start.
- Reuse mature infrastructure components instead of rebuilding RAG, vector search, graph storage, workflow engines, or MCP protocol support.

## Non-Goals

- Agora P0 will not be a full project management system.
- Agora P0 will not be a complex web dashboard or online IDE.
- Agora P0 will not require developers to use CLI as their main workflow.
- Agora P0 will not implement fine-grained permission UI.
- Agora P0 will not deeply integrate every possible tool such as Figma, Slack, Feishu, Teams, CI, monitoring, or test platforms.

## Product Principle

Developers should not need to say "use Agora" or run a terminal command. Their only normal interface is the AI agent conversation.

Agora should become the default project memory and workflow harness behind the agent.

## User Roles

### Developer

Primary entry: AI agent chat.

Example:

```text
Help me implement AG-128.
```

Agora should automatically resolve the current project, infer or resolve the task, produce relevant context, run impact/risk/test skills when appropriate, and prepare writeback after the agent finishes.

### QA

Primary entry: AI agent chat.

Example:

```text
Generate test points and regression scope for AG-128.
```

Agora combines requirement context, API context, code changes, historical bugs, and risk rules to produce structured test suggestions.

### Product Manager

Primary entry: AI agent chat.

Example:

```text
Check this requirement for ambiguity, conflicts, and missing acceptance criteria.
```

Agora searches historical requirements, decisions, APIs, and module context, then produces clarification questions and acceptance criteria.

### Project Manager

Primary entry: AI agent chat.

Example:

```text
Generate this week's project progress, risks, and blockers.
```

Agora summarizes tasks, PRs, sessions, writebacks, risks, and blockers.

### Newcomer

Primary entry: AI agent chat.

Example:

```text
I joined as a backend developer. Help me understand this project and plan my first three days.
```

Agora generates onboarding context from project, module, documentation, coding convention, and current iteration knowledge.

### Administrator

Primary entry: Minimal Web.

Administrators create projects, configure connectors, inspect synchronization state, and review initialization results.

### Skill Owner

Primary entry: Minimal Web.

Skill owners review AI-generated candidate skills, edit triggers and schemas, publish skills, and inspect skill runs.

## System Architecture

```text
AI Agent Chat
Codex / Cursor / Claude Code / Kimi / ChatGPT / Internal Agent
        |
Agent Adapter Layer
MCP / Plugin / API / Project Rules / PR Bot
        |
Agora Harness
Project Resolver / Task Resolver / Context Planner
Skill Orchestrator / Policy Engine / Session Recorder / Memory Writeback
        |
Runtime Layer
LangGraph / Temporal
        |
Knowledge Layer
LlamaIndex / PostgreSQL / Qdrant / OpenSearch / Neo4j / Redis
        |
Asset Connectors
Git / Docs / Task System / OpenAPI / PR / Commit
```

## Mature Component Strategy

Agora should reuse mature components by default.

| Concern | Component |
| --- | --- |
| RAG, ingestion, chunking, retrieval pipeline | LlamaIndex |
| Agent/harness state machine | LangGraph |
| Durable background workflows | Temporal |
| Main business data | PostgreSQL |
| Vector retrieval | Qdrant |
| Keyword and hybrid search | OpenSearch |
| Project knowledge graph | Neo4j |
| Cache and short-lived state | Redis |
| MCP protocol support | Official MCP SDK |
| Model routing and governance | LLM Gateway |

Agora should self-build:

- Harness lifecycle.
- ContextPack strategy.
- Skill registry and runner semantics.
- Project asset semantic model.
- TaskSession recording.
- Memory writeback.
- Agent integration protocol.

## Core Services

### Agent Adapter Service

Responsibilities:

- Expose MCP tools.
- Expose agent-facing API.
- Adapt plugin or project-rule integrations.
- Authenticate scoped agent access.
- Convert agent requests into harness calls.

This service must not implement core business logic or directly query databases.

### Harness Service

Agora's core product layer.

Responsibilities:

- Resolve project.
- Resolve task.
- Plan context.
- Orchestrate skills.
- Apply workflow policy.
- Record session events.
- Prepare and close writeback.

Harness workflows can be represented with LangGraph.

### Core API Service

Responsibilities:

- Manage organizations, projects, connector configs, assets, asset relations, context packs, skills, skill runs, sessions, writebacks, and audit logs.
- Serve Minimal Web and internal services.

### Ingestion Worker

Responsibilities:

- Sync Git, docs, task systems, OpenAPI specs, PRs, and commits.
- Normalize external data into Asset records.

Long-running syncs should use Temporal.

### Knowledge Worker

Responsibilities:

- Chunk assets.
- Generate summaries and embeddings.
- Write to Qdrant and OpenSearch.
- Build Neo4j graph relations.
- Generate or refresh ContextPacks.

### Skill Worker

Responsibilities:

- Run skills.
- Validate structured outputs.
- Record SkillRun results.
- Extract candidate skills from repeated project workflows and assets.

### Minimal Web

Responsibilities:

- Project setup.
- Connector configuration.
- Initialization report.
- Asset browsing.
- Skill review and management.
- Session inspection.
- Writeback review.

## Harness Lifecycle

Agents call high-level harness tools, not low-level knowledge stores.

```text
start_work
-> resolve_project / resolve_task
-> plan_context
-> fetch_context_ref
-> run_skill
-> record_event
-> prepare_writeback
-> close_work
```

### MCP Tools

P0 should expose these MCP tools:

- `agora_start_work`
- `agora_plan_context`
- `agora_fetch_context_ref`
- `agora_run_skill`
- `agora_record_event`
- `agora_prepare_writeback`
- `agora_close_work`
- `agora_search_knowledge`

`agora_search_knowledge` is a fallback exploration tool. The main path should be harness-guided.

### Agent Default Rule

Each connected agent should receive a default rule:

```text
For project-related analysis, implementation, testing, review, summary, or risk work:
1. Start with agora_start_work unless the user explicitly asks not to use Agora.
2. Before proposing implementation, call agora_plan_context.
3. Run required skills returned by Agora.
4. For core module, API, or test-impacting changes, run relevant impact/risk/test skills.
5. Before finishing, call agora_prepare_writeback.
6. Close the session after user confirmation or when the task is blocked.
```

## ContextPack Strategy

ContextPack is the smallest useful project understanding package for a task. It is not a raw search result list.

Requirements:

- Small.
- Relevant.
- Fresh.
- Traceable.
- Layered.
- Token-budget aware.

### Levels

| Level | Purpose | Typical Size |
| --- | --- | --- |
| L0 Session Brief | Project/task/intent summary and constraints | 1k-2k tokens |
| L1 Working Context | Requirements, modules, APIs, risks, decisions, relevant code paths | 4k-8k tokens |
| L2 Deep Context | Full referenced snippets or expanded assets | On demand |

### Retrieval Pipeline

```text
OpenSearch keyword search
+ Qdrant semantic retrieval
+ Neo4j graph traversal
+ LlamaIndex rerank/summarize
-> Harness compression by intent and token budget
-> Traceable ContextPack
```

Every key fact in a ContextPack should cite source references such as task, doc, file, API, PR, or writeback.

## Skill System

A Skill is a reusable, executable, versioned, reviewable team workflow package.

### Scopes

- System Skill.
- Organization Skill.
- Project Skill.

### Lifecycle

```text
candidate -> draft -> approved -> deprecated
```

AI may generate candidate skills. AI must not publish approved skills without human review.

### Initial Skills

P0 system skills:

- `task-context-summary`
- `impact-analysis`
- `test-case-generation`
- `risk-check`
- `knowledge-writeback`

Later system skills:

- `requirement-clarification`
- `pr-review`
- `newcomer-onboarding`
- `weekly-report`

Skill outputs must be structured so they can be used by PR comments, reports, writebacks, future skills, and dashboards.

## Data Model

Core objects:

- Organization.
- Project.
- ConnectorConfig.
- Asset.
- AssetRelation.
- ContextPack.
- Skill.
- SkillRun.
- TaskSession.
- Writeback.
- AuditLog.

Core loop:

```text
Git / Docs / Task / OpenAPI -> Asset
Asset -> Index / Graph
Index / Graph -> ContextPack
ContextPack + Skill -> Agent Work
Agent Work -> Writeback
Accepted Writeback -> Asset
```

### Asset

Assets normalize all project sources.

Examples:

- `code_file`
- `doc`
- `module`
- `task`
- `api_spec`
- `commit`
- `pull_request`
- `decision`
- `meeting_note`
- `writeback`

### TaskSession

Every agent work session records:

- Project.
- Task or free-form intent.
- Agent type.
- ContextPacks used.
- Skills run.
- Important events.
- Outputs.
- Writebacks.
- Status.

### Writeback

Writeback types:

- `development_summary`
- `test_suggestion`
- `risk_note`
- `decision_record`
- `module_note`
- `api_change_note`
- `task_update`
- `pr_summary`
- `skill_candidate`

Writebacks start as drafts unless policy allows automatic acceptance. Accepted writebacks become Assets and are re-indexed.

## Project Initialization Flow

Administrator creates a project in Minimal Web and configures at least Git.

Workflow:

```text
validate_connectors
-> sync_git_repository
-> sync_docs
-> sync_tasks
-> sync_openapi
-> parse_assets
-> build_indexes
-> build_asset_graph
-> generate_project_context
-> extract_skill_candidates
-> generate_initial_report
```

P0 requires Git. Docs, task systems, and OpenAPI may start as optional or mocked integrations.

Initialization should produce:

- Project summary.
- Technology stack.
- Module map.
- Core directories.
- Testing structure.
- Main documents.
- Initial ContextPacks.
- Candidate skills when available.

## Minimal Web Scope

Pages:

- Projects.
- Create project and connectors.
- Initialization report.
- Assets.
- Skills.
- Sessions.
- Writebacks.
- Settings.

Minimal Web must not become the developer's daily working interface.

## PR Bot Fallback

PR Bot is not the main entry. It is a safety net.

Triggers:

- PR created.
- PR updated.
- PR marked ready for review.

Workflow:

```text
Resolve project and task
-> Read diff and changed files
-> Plan context
-> Run impact-analysis / test-case-generation / risk-check
-> Comment on PR
-> Create Writeback draft
-> Link to existing TaskSession when possible
```

The bot should avoid noisy repeated comments. It should update or collapse previous analysis when possible.

## Governance Minimum

Even if P0 does not show complex permissions in the UI, the backend must support governance foundations:

- All records carry `org_id` and `project_id`.
- All Qdrant, OpenSearch, and Neo4j records carry tenant/project metadata.
- Connector credentials are encrypted.
- Agent tokens are scoped.
- Writeback review exists.
- Secret and PII scanning run before indexing sensitive content.
- Audit logs record project creation, connector configuration, agent access, ContextPack generation, skill runs, writebacks, and skill publishing.
- LLM calls go through LLM Gateway.

Suggested secret scanning tools:

- gitleaks.
- trufflehog.
- detect-secrets.

## Deployment

Agora should support:

- SaaS multi-tenant deployment.
- Private single-tenant deployment.
- Local development with Docker Compose.

Production baseline:

- API service.
- Agent Adapter/MCP service.
- Worker service.
- Minimal Web.
- PostgreSQL.
- Qdrant.
- OpenSearch.
- Neo4j.
- Redis.
- Temporal.
- Object storage.
- Vault/KMS.
- LLM Gateway.

Observability:

- OpenTelemetry.
- Prometheus/Grafana.
- Sentry or equivalent error tracking.
- Worker and sync run logs.
- LLM cost and token metrics.

## Recommended Technology Stack

- Backend: Python + FastAPI.
- Agent workflow: LangGraph.
- Durable workflow: Temporal.
- RAG/indexing: LlamaIndex.
- Main DB: PostgreSQL.
- Vector DB: Qdrant.
- Search: OpenSearch.
- Graph DB: Neo4j.
- Cache: Redis.
- MCP: official MCP SDK.
- Web: Next.js + TypeScript.
- Infra: Docker Compose + Helm.

## Repository Structure

```text
agora/
  apps/
    api/
    mcp/
    web/
    workers/
  packages/
    domain/
    core/
    harness/
    knowledge/
    integrations/
    llm/
    storage/
    observability/
  infra/
  docs/
  tests/
```

Early runtime processes:

- `api`
- `mcp`
- `worker`
- `web`

The codebase can remain a monorepo while preserving service and package boundaries.

## P0 Scope

P0 proves the core loop:

```text
Existing Git project
-> Automatic analysis
-> Agent gets default project context
-> Skill runs
-> Work result is written back
-> New knowledge is reusable later
```

### P0 Must Include

- Project creation.
- Git connector.
- Git initialization analysis.
- Asset model and storage.
- Qdrant and OpenSearch indexes.
- Basic Neo4j graph.
- L0/L1 ContextPack.
- Harness API.
- MCP Adapter.
- TaskSession.
- Built-in Skill Runner.
- Writeback draft, accept, and re-index.
- Minimal Web core pages.

### P0 Can Defer

- Real task-system deep integration.
- Deep OpenAPI impact analysis.
- PR Bot.
- Skill auto-extraction.
- PM weekly report.
- Full newcomer onboarding.
- IDE-specific plugin.
- Complex permission UI.

## P0 Acceptance Scenario

1. Admin creates a project from a Git repository in Minimal Web.
2. Agora syncs and analyzes the project.
3. Web shows project summary, modules, and assets.
4. Developer says in an AI agent: "Analyze how to implement refund failure retry."
5. Agent automatically calls Agora through MCP.
6. Agora returns a ContextPack.
7. Agent runs impact analysis and test suggestion skills.
8. Agent outputs an implementation recommendation.
9. Agent prepares development summary and test suggestion writebacks.
10. Web reviewer accepts the writebacks.
11. Accepted writebacks become Assets and are re-indexed.
12. A later similar question can retrieve the accepted writeback.

## P0 User Stories

### Admin Creates a Project

As an administrator, I can create an Agora project from a Git repository so that Agora can analyze an existing codebase.

Acceptance criteria:

- Admin can enter project name, Git remote, credential reference, and default branch.
- Agora validates the connector before starting initialization.
- Agora records sync status and visible errors.
- After initialization, Minimal Web shows project summary, module summary, and asset counts.

### Agent Resolves Project Automatically

As a developer, I can ask my AI agent to work on the current repository without saying "use Agora".

Acceptance criteria:

- Agent can call `agora_start_work` with repo metadata.
- Harness resolves the current project from Git remote.
- If the project cannot be resolved, Harness returns a clarification request instead of guessing.
- A TaskSession is created for the work.

### Agent Receives Task Context

As an AI agent, I can request a context plan for the current work so that I receive useful project context without loading the whole project.

Acceptance criteria:

- `agora_plan_context` returns L0 or L1 ContextPack.
- ContextPack includes summary, key facts, relevant modules, relevant code paths, risks, suggested skills, and source refs.
- ContextPack respects a token budget.
- At least one source reference can be expanded with `agora_fetch_context_ref`.

### Agent Runs Skills

As an AI agent, I can run standard project skills so that repeated team workflows produce structured outputs.

Acceptance criteria:

- `impact-analysis`, `test-case-generation`, `risk-check`, and `knowledge-writeback` can run through `agora_run_skill`.
- Skill outputs are validated against output schemas.
- SkillRun records include session, inputs, context used, outputs, status, and warnings.

### Knowledge Is Written Back

As a team, we can turn useful AI work output into durable project knowledge.

Acceptance criteria:

- `agora_prepare_writeback` creates a draft Writeback.
- Minimal Web can list and inspect draft writebacks.
- Reviewer can accept a writeback.
- Accepted writeback becomes an Asset.
- Accepted writeback is indexed and retrievable by a later ContextPack or search.

## Key Tradeoffs and Risks

### Harness Over Raw Tool Exposure

Decision: Agent calls Harness-level tools instead of Qdrant, OpenSearch, Neo4j, or Asset CRUD APIs directly.

Reason: This keeps agent behavior stable, reduces token waste, centralizes policy, and makes writeback auditable.

Risk: Some advanced exploration may need lower-level access. Mitigation: expose `agora_search_knowledge` as a fallback, and add admin/debug APIs outside the agent main path.

### Rich Infrastructure in P0

Decision: Use PostgreSQL, Qdrant, OpenSearch, Neo4j, Redis, Temporal, LlamaIndex, and LangGraph from the start.

Reason: Agora is infrastructure-heavy by nature, and late replacement of storage/search/workflow foundations would be expensive.

Risk: Local setup and operations are heavier. Mitigation: provide Docker Compose for local/demo, Helm for production, and keep P0 graph/search relation sets minimal.

### Agent-First User Experience

Decision: Developers use their AI agent chat as the primary interface.

Reason: This matches the actual developer workflow and avoids forcing a new daily tool.

Risk: Different agents support different integration mechanisms. Mitigation: keep Agent Adapter separate and support MCP first, while leaving room for plugins, APIs, and project-rule adapters.

### Draft Writeback by Default

Decision: Agent-generated knowledge starts as draft unless policy explicitly allows automatic acceptance.

Reason: Agora should not silently convert AI guesses into official project knowledge.

Risk: Review may become a bottleneck. Mitigation: allow low-risk types such as development summaries to be auto-accepted later by project policy.

### P0 Git-First Scope

Decision: P0 requires Git and defers deep task-system and OpenAPI integrations.

Reason: Git is the most universal project asset source and is enough to prove the core harness loop.

Risk: Without task-system data, task context is weaker. Mitigation: support free-form task intent and keep ConnectorConfig/API extension points ready for task systems.

## Open Questions

- Which AI agents are the first supported targets: Codex, Cursor, Claude Code, Kimi, ChatGPT, or an internal agent?
- Which Git providers must be supported first: GitHub, GitLab, Gitee, self-hosted GitLab?
- Which model providers must the LLM Gateway support first?
- Should P0 require Neo4j from day one, or should the graph adapter be present with a minimal relation set?
- Should Writeback default to draft for every type, or auto-accept low-risk summaries?
