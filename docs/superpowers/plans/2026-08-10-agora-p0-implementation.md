# Agora P0 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Agora P0 end-to-end loop: Git project ingestion -> project knowledge indexing -> Agent ContextPack retrieval -> Skill execution -> Writeback review -> accepted knowledge re-index.

**Architecture:** Use a Python/FastAPI backend monorepo with clear package boundaries, a separate MCP adapter, Temporal-style worker entrypoints, and a minimal Next.js admin web. PostgreSQL is the source of truth; Qdrant/OpenSearch/Neo4j are derived indexes behind storage adapters so local tests can use fakes before real services are wired.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, official MCP SDK, LlamaIndex, Qdrant, OpenSearch, Neo4j, Redis, Temporal, Next.js, TypeScript, Docker Compose.

---

## Reference Specs

- This is a historical P0 implementation plan. Its original 2026-08-10 design references were removed after their durable concepts were consolidated into the canonical product and technical architecture on 2026-08-14; the deleted files remain available in Git history.
- Current product source: `docs/superpowers/specs/2026-08-14-agora-product-functional-design.zh-CN.md`
- Current architecture source: `docs/superpowers/specs/2026-08-14-agora-technical-architecture-design.zh-CN.md`

## Scope

P0 must prove this loop:

```text
Create project from Git
-> analyze repository
-> normalize Assets
-> build searchable indexes
-> Agent calls Harness through MCP
-> Harness returns ContextPack
-> Agent runs Skills
-> Agent prepares Writeback
-> Web reviewer accepts Writeback
-> Writeback becomes indexed Asset
```

P0 intentionally defers:

- Real task-system deep integration.
- Deep OpenAPI impact analysis.
- PR Bot.
- Skill auto-extraction.
- IDE-specific plugins.
- Complex permission UI.
- Production-grade RBAC.

## File Structure

Create this monorepo structure:

```text
apps/
  api/
    main.py
    dependencies.py
    routers/
      health.py
      projects.py
      assets.py
      harness.py
      skills.py
      sessions.py
      writebacks.py
  mcp/
    server.py
    tools.py
    schemas.py
  web/
    app/
      page.tsx
      projects/page.tsx
      projects/[projectId]/page.tsx
      projects/[projectId]/assets/page.tsx
      projects/[projectId]/skills/page.tsx
      projects/[projectId]/sessions/page.tsx
      projects/[projectId]/writebacks/page.tsx
    components/
    lib/
  workers/
    main.py
    workflows/
      initialize_project.py
    activities/
      git_sync.py
      normalize_assets.py
      build_indexes.py
      generate_context.py

packages/
  domain/
    enums.py
    schemas.py
    models.py
  core/
    database.py
    repositories/
    services/
  harness/
    service.py
    project_resolver.py
    task_resolver.py
    context_planner.py
    skill_orchestrator.py
    session_recorder.py
    memory_writeback.py
  knowledge/
    chunking.py
    context_engine.py
    retrieval.py
    indexing.py
    graph_builder.py
  integrations/
    git/
      connector.py
      analyzer.py
  llm/
    gateway.py
    fake_gateway.py
    structured_output.py
  storage/
    postgres/
    qdrant/
    opensearch/
    neo4j/
    redis/
  observability/
    logging.py

infra/
  docker-compose.yml
  env.example

tests/
  unit/
  integration/
  e2e/
```

## Chunk 1: Foundation

### Task 1: Create Monorepo Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `apps/api/main.py`
- Create: `apps/api/routers/health.py`
- Create: `apps/mcp/server.py`
- Create: `apps/workers/main.py`
- Create: `apps/web/package.json`
- Create: `apps/web/app/page.tsx`
- Create: `packages/domain/__init__.py`
- Create: `packages/core/__init__.py`
- Create: `packages/harness/__init__.py`
- Create: `packages/knowledge/__init__.py`
- Create: `packages/integrations/__init__.py`
- Create: `packages/llm/__init__.py`
- Create: `packages/storage/__init__.py`
- Create: `tests/unit/test_health.py`

- [ ] **Step 1: Write the health test**

Create `tests/unit/test_health.py`:

```python
from fastapi.testclient import TestClient

from apps.api.main import app


def test_health_endpoint_returns_ok():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_health.py -v`

Expected: FAIL because `apps.api.main` or `/health` does not exist yet.

- [ ] **Step 3: Implement FastAPI health endpoint**

Create `apps/api/routers/health.py`:

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

Create `apps/api/main.py`:

```python
from fastapi import FastAPI

from apps.api.routers.health import router as health_router

app = FastAPI(title="Agora API")
app.include_router(health_router)
```

- [ ] **Step 4: Add Python project config**

Create `pyproject.toml` with dependencies:

```toml
[project]
name = "agora"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn>=0.30.0",
  "pydantic>=2.8.0",
  "sqlalchemy>=2.0.0",
  "alembic>=1.13.0",
  "psycopg[binary]>=3.2.0",
  "pytest>=8.0.0",
  "httpx>=0.27.0",
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_health.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml README.md .env.example .gitignore apps packages tests
git commit -m "chore: add Agora monorepo skeleton"
```

### Task 2: Add Local Infrastructure Compose

**Files:**
- Create: `infra/docker-compose.yml`
- Create: `infra/env.example`
- Modify: `README.md`

- [ ] **Step 1: Add Docker Compose services**

Create `infra/docker-compose.yml` with services:

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: agora
      POSTGRES_PASSWORD: agora
      POSTGRES_DB: agora
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"

  opensearch:
    image: opensearchproject/opensearch:2
    environment:
      discovery.type: single-node
      plugins.security.disabled: "true"
      OPENSEARCH_INITIAL_ADMIN_PASSWORD: "AgoraLocal123!"
    ports:
      - "9200:9200"

  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/agora-local
    ports:
      - "7474:7474"
      - "7687:7687"
```

- [ ] **Step 2: Document local startup**

Update `README.md` with:

````markdown
## Local Development

```bash
docker compose -f infra/docker-compose.yml up -d
uvicorn apps.api.main:app --reload
pytest
```
````

- [ ] **Step 3: Validate compose config**

Run: `docker compose -f infra/docker-compose.yml config`

Expected: command exits 0 and prints normalized compose config.

- [ ] **Step 4: Commit**

```bash
git add infra README.md
git commit -m "chore: add local infrastructure compose"
```

## Chunk 2: Core Domain and API

### Task 3: Define Domain Schemas and Enums

**Files:**
- Create: `packages/domain/enums.py`
- Create: `packages/domain/schemas.py`
- Test: `tests/unit/domain/test_schemas.py`

- [ ] **Step 1: Write schema tests**

Create `tests/unit/domain/test_schemas.py`:

```python
from packages.domain.enums import AssetType, WritebackStatus
from packages.domain.schemas import ProjectCreate, WritebackCreate


def test_project_create_requires_name_and_org():
    payload = ProjectCreate(org_id="org_1", name="Payment", slug="payment")

    assert payload.org_id == "org_1"
    assert payload.slug == "payment"


def test_writeback_defaults_to_draft():
    payload = WritebackCreate(
        org_id="org_1",
        project_id="proj_1",
        type="development_summary",
        title="AG-128 summary",
        content="Implemented refund retry.",
    )

    assert payload.status == WritebackStatus.DRAFT
    assert payload.type == "development_summary"


def test_asset_type_contains_code_file():
    assert AssetType.CODE_FILE == "code_file"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/unit/domain/test_schemas.py -v`

Expected: FAIL because schemas do not exist.

- [ ] **Step 3: Implement enums**

Create `packages/domain/enums.py`:

```python
from enum import StrEnum


class AssetType(StrEnum):
    CODE_FILE = "code_file"
    DOC = "doc"
    MODULE = "module"
    COMMIT = "commit"
    WRITEBACK = "writeback"


class AssetSource(StrEnum):
    GIT = "git"
    AGENT = "agent"
    MANUAL = "manual"


class SkillStatus(StrEnum):
    CANDIDATE = "candidate"
    DRAFT = "draft"
    APPROVED = "approved"
    DEPRECATED = "deprecated"


class SessionStatus(StrEnum):
    STARTED = "started"
    CONTEXT_READY = "context_ready"
    WORKING = "working"
    REVIEWING = "reviewing"
    CLOSED = "closed"
    FAILED = "failed"


class WritebackStatus(StrEnum):
    DRAFT = "draft"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
```

- [ ] **Step 4: Implement Pydantic schemas**

Create `packages/domain/schemas.py`:

```python
from pydantic import BaseModel, Field

from packages.domain.enums import WritebackStatus


class ProjectCreate(BaseModel):
    org_id: str
    name: str
    slug: str
    description: str | None = None
    git_remotes: list[str] = Field(default_factory=list)
    default_branch: str | None = None


class ProjectRead(ProjectCreate):
    id: str


class AssetCreate(BaseModel):
    org_id: str
    project_id: str
    type: str
    source: str
    source_uri: str
    title: str
    content: str
    summary: str | None = None
    metadata: dict = Field(default_factory=dict)
    content_hash: str | None = None


class ContextPackRead(BaseModel):
    id: str
    org_id: str
    project_id: str
    level: str
    summary: str
    key_facts: list[dict] = Field(default_factory=list)
    source_refs: list[dict] = Field(default_factory=list)


class WritebackCreate(BaseModel):
    org_id: str
    project_id: str
    type: str
    title: str
    content: str
    session_id: str | None = None
    asset_refs: list[str] = Field(default_factory=list)
    status: WritebackStatus = WritebackStatus.DRAFT
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/unit/domain/test_schemas.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/domain tests/unit/domain
git commit -m "feat: define core domain schemas"
```

### Task 4: Add SQLAlchemy Models and Repositories

**Files:**
- Create: `packages/core/database.py`
- Create: `packages/core/models.py`
- Create: `packages/core/repositories/projects.py`
- Create: `packages/core/repositories/assets.py`
- Create: `packages/core/repositories/sessions.py`
- Create: `packages/core/repositories/writebacks.py`
- Test: `tests/unit/core/test_repositories.py`

- [ ] **Step 1: Write repository tests using SQLite**

Create `tests/unit/core/test_repositories.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.core.database import Base
from packages.core.repositories.assets import AssetRepository
from packages.core.repositories.projects import ProjectRepository


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_project_repository_creates_project():
    session = make_session()
    repo = ProjectRepository(session)

    project = repo.create(org_id="org_1", name="Payment", slug="payment", git_remotes=["git@example.com:payment.git"])

    assert project.id
    assert project.org_id == "org_1"
    assert project.git_remotes == ["git@example.com:payment.git"]


def test_asset_repository_creates_asset():
    session = make_session()
    project = ProjectRepository(session).create(org_id="org_1", name="Payment", slug="payment")
    asset = AssetRepository(session).create(
        org_id="org_1",
        project_id=project.id,
        type="doc",
        source="git",
        source_uri="README.md",
        title="README",
        content="Payment service",
    )

    assert asset.project_id == project.id
    assert asset.title == "README"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/unit/core/test_repositories.py -v`

Expected: FAIL because database models do not exist.

- [ ] **Step 3: Implement database base and models**

Create models for:

- `ProjectModel`
- `AssetModel`
- `ContextPackModel`
- `SkillModel`
- `SkillRunModel`
- `TaskSessionModel`
- `SessionEventModel`
- `WritebackModel`

Use UUID strings generated by `uuid.uuid4().hex`.

Store JSON fields with SQLAlchemy `JSON`.

- [ ] **Step 4: Implement repositories**

Each repository should accept a SQLAlchemy session and expose minimal methods:

- `create`
- `get`
- `list_by_project`
- `find_by_git_remote` for projects.
- `accept` for writebacks.

- [ ] **Step 5: Run repository tests**

Run: `pytest tests/unit/core/test_repositories.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/core tests/unit/core
git commit -m "feat: add core persistence repositories"
```

### Task 5: Add Core API Routers

**Files:**
- Modify: `apps/api/main.py`
- Create: `apps/api/dependencies.py`
- Create: `apps/api/routers/projects.py`
- Create: `apps/api/routers/assets.py`
- Create: `apps/api/routers/sessions.py`
- Create: `apps/api/routers/writebacks.py`
- Test: `tests/integration/api/test_projects_api.py`

- [ ] **Step 1: Write API tests**

Create `tests/integration/api/test_projects_api.py`:

```python
from fastapi.testclient import TestClient

from apps.api.main import app


def test_create_project_api():
    client = TestClient(app)

    response = client.post(
        "/projects",
        json={"org_id": "org_1", "name": "Payment", "slug": "payment", "git_remotes": ["git@example.com:payment.git"]},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["name"] == "Payment"
```

- [ ] **Step 2: Run API test to verify failure**

Run: `pytest tests/integration/api/test_projects_api.py -v`

Expected: FAIL because routes do not exist.

- [ ] **Step 3: Add dependency-managed test database**

Implement `apps/api/dependencies.py` with an in-memory SQLite default for tests and env-driven database URL for runtime.

- [ ] **Step 4: Implement project router**

Expose:

- `POST /projects`
- `GET /projects/{project_id}`
- `GET /projects`

- [ ] **Step 5: Wire routers in main app**

Update `apps/api/main.py` to include routers.

- [ ] **Step 6: Run API tests**

Run: `pytest tests/integration/api/test_projects_api.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/api tests/integration/api
git commit -m "feat: expose core project API"
```

## Chunk 3: Git Ingestion

### Task 6: Implement Git Connector and Repository Analyzer

**Files:**
- Create: `packages/integrations/git/connector.py`
- Create: `packages/integrations/git/analyzer.py`
- Test: `tests/unit/integrations/test_git_analyzer.py`
- Fixture: `tests/fixtures/sample_repo/README.md`
- Fixture: `tests/fixtures/sample_repo/package.json`
- Fixture: `tests/fixtures/sample_repo/src/refund/service.ts`
- Fixture: `tests/fixtures/sample_repo/tests/refund.test.ts`

- [ ] **Step 1: Create sample repo fixture**

Create fixture files:

`tests/fixtures/sample_repo/README.md`:

```markdown
# Payment Service

Handles payment, refund, and reconciliation flows.
```

`tests/fixtures/sample_repo/package.json`:

```json
{"name": "payment-service", "dependencies": {"fastify": "^4.0.0"}}
```

`tests/fixtures/sample_repo/src/refund/service.ts`:

```typescript
export function refund(orderId: string) {
  return { orderId, status: "refund_requested" };
}
```

`tests/fixtures/sample_repo/tests/refund.test.ts`:

```typescript
import { refund } from "../src/refund/service";
```

- [ ] **Step 2: Write analyzer tests**

Create `tests/unit/integrations/test_git_analyzer.py`:

```python
from pathlib import Path

from packages.integrations.git.analyzer import analyze_repository


def test_analyze_repository_detects_readme_modules_and_tests():
    result = analyze_repository(Path("tests/fixtures/sample_repo"))

    assert result.project_summary.startswith("Payment Service")
    assert "src/refund" in result.modules
    assert result.test_paths == ["tests/refund.test.ts"]
    assert "package.json" in result.dependency_files
```

- [ ] **Step 3: Run test to verify failure**

Run: `pytest tests/unit/integrations/test_git_analyzer.py -v`

Expected: FAIL because analyzer does not exist.

- [ ] **Step 4: Implement analyzer**

Implement `analyze_repository(path: Path) -> RepositoryAnalysis` that:

- Reads README first heading and first paragraph.
- Finds top-level source modules under `src/*`.
- Finds test files under `tests/`.
- Finds dependency files from a known list.
- Returns relative POSIX paths.

- [ ] **Step 5: Run analyzer test**

Run: `pytest tests/unit/integrations/test_git_analyzer.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/integrations tests/fixtures tests/unit/integrations
git commit -m "feat: analyze Git repository structure"
```

### Task 7: Normalize Git Analysis into Assets

**Files:**
- Create: `packages/knowledge/ingestion.py`
- Test: `tests/unit/knowledge/test_ingestion.py`

- [ ] **Step 1: Write ingestion test**

Create `tests/unit/knowledge/test_ingestion.py`:

```python
from pathlib import Path

from packages.integrations.git.analyzer import analyze_repository
from packages.knowledge.ingestion import assets_from_repository_analysis


def test_repository_analysis_generates_assets():
    analysis = analyze_repository(Path("tests/fixtures/sample_repo"))

    assets = assets_from_repository_analysis(
        org_id="org_1",
        project_id="proj_1",
        repo_path=Path("tests/fixtures/sample_repo"),
        analysis=analysis,
    )

    titles = {asset.title for asset in assets}
    assert "README.md" in titles
    assert "src/refund" in titles
    assert any(asset.type == "module" for asset in assets)
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/unit/knowledge/test_ingestion.py -v`

Expected: FAIL because `assets_from_repository_analysis` does not exist.

- [ ] **Step 3: Implement asset normalization**

Convert:

- README and docs into `doc` assets.
- `src/*` directories into `module` assets.
- Source files into `code_file` assets.
- Dependency files into `doc` or `dependency_manifest` metadata.

- [ ] **Step 4: Run ingestion test**

Run: `pytest tests/unit/knowledge/test_ingestion.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/knowledge tests/unit/knowledge
git commit -m "feat: normalize Git analysis into assets"
```

### Task 8: Add Initialize Project Workflow Facade

**Files:**
- Create: `apps/workers/workflows/initialize_project.py`
- Create: `apps/workers/activities/git_sync.py`
- Create: `apps/workers/activities/normalize_assets.py`
- Test: `tests/integration/workers/test_initialize_project.py`

- [ ] **Step 1: Write workflow facade test**

Create `tests/integration/workers/test_initialize_project.py`:

```python
from pathlib import Path

from apps.workers.workflows.initialize_project import initialize_project_from_local_repo


def test_initialize_project_from_local_repo_creates_assets():
    result = initialize_project_from_local_repo(
        org_id="org_1",
        project_id="proj_1",
        repo_path=Path("tests/fixtures/sample_repo"),
    )

    assert result.asset_count > 0
    assert "src/refund" in result.modules
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/integration/workers/test_initialize_project.py -v`

Expected: FAIL because workflow facade does not exist.

- [ ] **Step 3: Implement synchronous facade**

Implement a synchronous local facade first. Do not wire real Temporal until the domain path is stable.

`initialize_project_from_local_repo` should:

- Analyze repository.
- Normalize assets.
- Return `InitializeProjectResult(asset_count, modules, warnings)`.

- [ ] **Step 4: Run workflow facade test**

Run: `pytest tests/integration/workers/test_initialize_project.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/workers tests/integration/workers
git commit -m "feat: add project initialization workflow facade"
```

## Chunk 4: Knowledge Indexing and ContextPack

### Task 9: Add Chunking and Fake Index Stores

**Files:**
- Create: `packages/knowledge/chunking.py`
- Create: `packages/storage/qdrant/fake.py`
- Create: `packages/storage/opensearch/fake.py`
- Create: `packages/storage/neo4j/fake.py`
- Test: `tests/unit/knowledge/test_indexing.py`

- [ ] **Step 1: Write indexing tests**

Create `tests/unit/knowledge/test_indexing.py`:

```python
from packages.domain.schemas import AssetCreate
from packages.knowledge.chunking import chunk_asset
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex


def test_chunk_asset_splits_content_with_source_metadata():
    asset = AssetCreate(
        org_id="org_1",
        project_id="proj_1",
        type="doc",
        source="git",
        source_uri="README.md",
        title="README",
        content="Payment service\n\nRefund module handles refund retry.",
    )

    chunks = chunk_asset(asset)

    assert chunks
    assert chunks[0].source_uri == "README.md"


def test_fake_indexes_return_project_scoped_results():
    asset = AssetCreate(
        org_id="org_1",
        project_id="proj_1",
        type="doc",
        source="git",
        source_uri="README.md",
        title="README",
        content="Refund retry policy",
    )
    keyword = FakeKeywordIndex()
    vector = FakeVectorIndex()

    keyword.index_asset(asset_id="asset_1", asset=asset)
    vector.index_asset(asset_id="asset_1", asset=asset)

    assert keyword.search(org_id="org_1", project_id="proj_1", query="refund")
    assert vector.search(org_id="org_1", project_id="proj_1", query="retry")
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/unit/knowledge/test_indexing.py -v`

Expected: FAIL because chunking and fake indexes do not exist.

- [ ] **Step 3: Implement chunking and fake stores**

Keep fake stores deterministic:

- Keyword fake uses case-insensitive substring scoring.
- Vector fake can use token overlap scoring.
- Both require `org_id` and `project_id` filters.

- [ ] **Step 4: Run indexing tests**

Run: `pytest tests/unit/knowledge/test_indexing.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/knowledge packages/storage tests/unit/knowledge
git commit -m "feat: add project knowledge indexing fakes"
```

### Task 10: Implement Retrieval Merge and Context Engine

**Files:**
- Create: `packages/knowledge/retrieval.py`
- Create: `packages/knowledge/context_engine.py`
- Test: `tests/unit/knowledge/test_context_engine.py`

- [ ] **Step 1: Write context engine test**

Create `tests/unit/knowledge/test_context_engine.py`:

```python
from packages.domain.schemas import AssetCreate
from packages.knowledge.context_engine import ContextEngine
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex


def test_context_engine_generates_traceable_context_pack():
    asset = AssetCreate(
        org_id="org_1",
        project_id="proj_1",
        type="doc",
        source="git",
        source_uri="docs/refund.md",
        title="Refund Design",
        content="Refund retry must be idempotent and capped.",
    )
    keyword = FakeKeywordIndex()
    vector = FakeVectorIndex()
    keyword.index_asset("asset_1", asset)
    vector.index_asset("asset_1", asset)

    engine = ContextEngine(keyword_index=keyword, vector_index=vector)
    context = engine.plan_context(
        org_id="org_1",
        project_id="proj_1",
        intent="implementation",
        query="refund retry",
        token_budget=1000,
    )

    assert context.summary
    assert context.source_refs[0]["asset_id"] == "asset_1"
    assert "refund" in context.summary.lower()
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/unit/knowledge/test_context_engine.py -v`

Expected: FAIL because context engine does not exist.

- [ ] **Step 3: Implement retrieval merge**

Implement:

- `SearchCandidate`
- `merge_candidates`
- dedupe by `asset_id`
- score by max score + source boost.

- [ ] **Step 4: Implement ContextEngine**

`ContextEngine.plan_context` should:

- Query keyword and vector indexes.
- Merge candidates.
- Build summary from top results.
- Include source refs.
- Respect approximate token budget by truncating content.

- [ ] **Step 5: Run context engine test**

Run: `pytest tests/unit/knowledge/test_context_engine.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/knowledge tests/unit/knowledge
git commit -m "feat: generate traceable context packs"
```

## Chunk 5: Harness and MCP

### Task 11: Implement Harness Service

**Files:**
- Create: `packages/harness/service.py`
- Create: `packages/harness/project_resolver.py`
- Create: `packages/harness/task_resolver.py`
- Create: `packages/harness/context_planner.py`
- Create: `packages/harness/session_recorder.py`
- Test: `tests/unit/harness/test_harness_service.py`

- [ ] **Step 1: Write harness service test**

Create `tests/unit/harness/test_harness_service.py`:

```python
from packages.harness.service import HarnessService


def test_start_work_resolves_project_by_remote(fake_core, fake_context_engine):
    project = fake_core.create_project(org_id="org_1", name="Payment", slug="payment", git_remotes=["git@example.com:payment.git"])
    harness = HarnessService(core=fake_core, context_engine=fake_context_engine)

    result = harness.start_work(
        user_message="帮我做 AG-128",
        repo_remote="git@example.com:payment.git",
        agent_type="codex",
    )

    assert result.project.id == project.id
    assert result.session_id
    assert result.next_action == "plan_context"
```

- [ ] **Step 2: Add fake core fixture**

Create test fixtures in `tests/unit/harness/conftest.py`:

- `fake_core`
- `fake_context_engine`

Keep fakes in tests unless reusable by multiple packages.

- [ ] **Step 3: Run harness test to verify failure**

Run: `pytest tests/unit/harness/test_harness_service.py -v`

Expected: FAIL because harness does not exist.

- [ ] **Step 4: Implement ProjectResolver**

Resolve project by exact git remote match. If no project is found, return a clarification result instead of guessing.

- [ ] **Step 5: Implement TaskResolver**

Extract task IDs with regex like `[A-Z]+-\d+`. If none found, create a free-form task intent.

- [ ] **Step 6: Implement HarnessService**

Methods:

- `start_work`
- `plan_context`
- `record_event`
- `close_work`

Use fake or repository-backed core depending on test setup.

- [ ] **Step 7: Run harness tests**

Run: `pytest tests/unit/harness/test_harness_service.py -v`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add packages/harness tests/unit/harness
git commit -m "feat: add harness work lifecycle"
```

### Task 12: Expose Harness API Router

**Files:**
- Create: `apps/api/routers/harness.py`
- Modify: `apps/api/main.py`
- Test: `tests/integration/api/test_harness_api.py`

- [ ] **Step 1: Write API test**

Create `tests/integration/api/test_harness_api.py`:

```python
from fastapi.testclient import TestClient

from apps.api.main import app


def test_start_work_endpoint_returns_session():
    client = TestClient(app)
    project = client.post(
        "/projects",
        json={"org_id": "org_1", "name": "Payment", "slug": "payment", "git_remotes": ["git@example.com:payment.git"]},
    ).json()

    response = client.post(
        "/harness/start-work",
        json={"user_message": "帮我做 AG-128", "repo_remote": "git@example.com:payment.git", "agent_type": "codex"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"]
    assert body["project"]["id"] == project["id"]
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/integration/api/test_harness_api.py -v`

Expected: FAIL because route does not exist.

- [ ] **Step 3: Implement harness router**

Routes:

- `POST /harness/start-work`
- `POST /harness/plan-context`
- `POST /harness/record-event`
- `POST /harness/close-work`

- [ ] **Step 4: Run API test**

Run: `pytest tests/integration/api/test_harness_api.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api tests/integration/api
git commit -m "feat: expose harness API"
```

### Task 13: Implement MCP Tool Adapter

**Files:**
- Create: `apps/mcp/schemas.py`
- Create: `apps/mcp/tools.py`
- Modify: `apps/mcp/server.py`
- Test: `tests/unit/mcp/test_tools.py`

- [ ] **Step 1: Write MCP tool unit tests**

Create `tests/unit/mcp/test_tools.py`:

```python
from apps.mcp.tools import AgoraMcpTools


def test_mcp_start_work_delegates_to_harness(fake_harness):
    tools = AgoraMcpTools(harness=fake_harness)

    result = tools.agora_start_work(
        user_message="帮我做 AG-128",
        repo_remote="git@example.com:payment.git",
        agent_type="codex",
    )

    assert result["session_id"] == "sess_1"
    assert fake_harness.started
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/unit/mcp/test_tools.py -v`

Expected: FAIL because MCP tools do not exist.

- [ ] **Step 3: Implement MCP schemas and tool class**

Methods:

- `agora_start_work`
- `agora_plan_context`
- `agora_fetch_context_ref`
- `agora_run_skill`
- `agora_record_event`
- `agora_prepare_writeback`
- `agora_close_work`
- `agora_search_knowledge`

Each method delegates to Harness or Core services. Do not implement business logic here.

- [ ] **Step 4: Implement server entrypoint**

Use the official MCP SDK if available in environment. If not, create an adapter boundary with explicit future-work comments and keep unit tests against `AgoraMcpTools`.

- [ ] **Step 5: Run MCP tests**

Run: `pytest tests/unit/mcp/test_tools.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/mcp tests/unit/mcp
git commit -m "feat: add MCP harness tools"
```

## Chunk 6: Skills and Writeback

### Task 14: Implement Skill Registry and Runner

**Files:**
- Create: `packages/harness/skill_orchestrator.py`
- Create: `packages/core/services/skills.py`
- Create: `packages/llm/fake_gateway.py`
- Test: `tests/unit/harness/test_skill_runner.py`

- [ ] **Step 1: Write skill runner test**

Create `tests/unit/harness/test_skill_runner.py`:

```python
from packages.harness.skill_orchestrator import SkillOrchestrator
from packages.llm.fake_gateway import FakeLlmGateway


def test_impact_analysis_skill_returns_structured_output(fake_core):
    fake_core.create_skill(slug="impact-analysis", status="approved")
    orchestrator = SkillOrchestrator(core=fake_core, llm=FakeLlmGateway())

    result = orchestrator.run_skill(
        session_id="sess_1",
        skill_slug="impact-analysis",
        input={"task": "refund retry"},
        context={"summary": "Refund retry touches refund-service."},
    )

    assert result.skill_run_id
    assert "risks" in result.output
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/unit/harness/test_skill_runner.py -v`

Expected: FAIL because skill orchestrator does not exist.

- [ ] **Step 3: Implement built-in skill definitions**

System skills:

- `task-context-summary`
- `impact-analysis`
- `test-case-generation`
- `risk-check`
- `knowledge-writeback`

Store definitions in code for P0. Later migrations can persist them.

- [ ] **Step 4: Implement FakeLlmGateway**

Fake responses must be deterministic and schema-shaped for tests.

- [ ] **Step 5: Implement SkillOrchestrator**

Responsibilities:

- Load skill.
- Check approved status.
- Validate input shape minimally.
- Call LLM gateway.
- Validate output is a dict.
- Save SkillRun.

- [ ] **Step 6: Run skill tests**

Run: `pytest tests/unit/harness/test_skill_runner.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add packages/harness packages/core/services packages/llm tests/unit/harness
git commit -m "feat: run built-in harness skills"
```

### Task 15: Implement Writeback Draft, Accept, and Re-index

**Files:**
- Create: `packages/harness/memory_writeback.py`
- Create: `packages/core/services/writebacks.py`
- Create: `apps/api/routers/writebacks.py`
- Test: `tests/integration/test_writeback_reindex.py`

- [ ] **Step 1: Write writeback re-index test**

Create `tests/integration/test_writeback_reindex.py`:

```python
from packages.harness.memory_writeback import MemoryWritebackService
from packages.knowledge.context_engine import ContextEngine
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex


def test_accepted_writeback_becomes_retrievable(fake_core):
    keyword = FakeKeywordIndex()
    vector = FakeVectorIndex()
    service = MemoryWritebackService(core=fake_core, keyword_index=keyword, vector_index=vector)

    writeback = service.prepare_writeback(
        org_id="org_1",
        project_id="proj_1",
        session_id="sess_1",
        type="development_summary",
        title="Refund retry summary",
        content="Refund retry must cap retries and preserve idempotency.",
    )
    service.accept_writeback(writeback.id)

    context = ContextEngine(keyword_index=keyword, vector_index=vector).plan_context(
        org_id="org_1",
        project_id="proj_1",
        intent="implementation",
        query="refund retry idempotency",
        token_budget=1000,
    )

    assert "idempotency" in context.summary.lower()
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/integration/test_writeback_reindex.py -v`

Expected: FAIL because writeback service does not exist.

- [ ] **Step 3: Implement MemoryWritebackService**

Methods:

- `prepare_writeback`
- `accept_writeback`
- `reject_writeback`

Accepting a writeback must:

- Change status to accepted.
- Create an Asset of type `writeback`.
- Index the asset into fake keyword and vector stores.

- [ ] **Step 4: Add API routes**

Routes:

- `GET /projects/{project_id}/writebacks`
- `POST /writebacks/{writeback_id}/accept`
- `POST /writebacks/{writeback_id}/reject`

- [ ] **Step 5: Run writeback tests**

Run: `pytest tests/integration/test_writeback_reindex.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/harness packages/core/services apps/api/routers/writebacks.py tests/integration
git commit -m "feat: persist and re-index accepted writebacks"
```

## Chunk 7: Minimal Web

### Task 16: Build Minimal Web Shell

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/app/layout.tsx`
- Modify: `apps/web/app/page.tsx`
- Create: `apps/web/lib/api.ts`
- Create: `apps/web/components/Nav.tsx`

- [ ] **Step 1: Add Next.js package config**

Create `apps/web/package.json`:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "typescript": "^5.5.0",
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0"
  }
}
```

- [ ] **Step 2: Implement layout and nav**

Create simple navigation for:

- Projects.
- Assets.
- Skills.
- Sessions.
- Writebacks.

- [ ] **Step 3: Implement API helper**

`apps/web/lib/api.ts` should read `NEXT_PUBLIC_AGORA_API_URL`.

- [ ] **Step 4: Run build**

Run: `cd apps/web && npm install && npm run build`

Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add apps/web
git commit -m "feat: add minimal web shell"
```

### Task 17: Build Project and Review Pages

**Files:**
- Create: `apps/web/app/projects/page.tsx`
- Create: `apps/web/app/projects/[projectId]/page.tsx`
- Create: `apps/web/app/projects/[projectId]/assets/page.tsx`
- Create: `apps/web/app/projects/[projectId]/skills/page.tsx`
- Create: `apps/web/app/projects/[projectId]/sessions/page.tsx`
- Create: `apps/web/app/projects/[projectId]/writebacks/page.tsx`

- [ ] **Step 1: Implement Projects page**

Show:

- Project name.
- Sync status placeholder.
- Asset count placeholder.
- Recent sessions placeholder.

- [ ] **Step 2: Implement project detail page**

Show initialization summary sections:

- Summary.
- Modules.
- Tech stack.
- Warnings.

- [ ] **Step 3: Implement Assets page**

Show asset list with type, title, source URI.

- [ ] **Step 4: Implement Skills page**

Show built-in skills and status.

- [ ] **Step 5: Implement Sessions page**

Show sessions and events.

- [ ] **Step 6: Implement Writebacks page**

Show draft writebacks with accept/reject actions.

- [ ] **Step 7: Run build**

Run: `cd apps/web && npm run build`

Expected: build succeeds.

- [ ] **Step 8: Commit**

```bash
git add apps/web
git commit -m "feat: add minimal Agora admin pages"
```

## Chunk 8: End-to-End Demo

### Task 18: Add E2E P0 Demo Test

**Files:**
- Create: `tests/e2e/test_p0_loop.py`
- Create: `scripts/run_p0_demo.py`

- [ ] **Step 1: Write E2E test**

Create `tests/e2e/test_p0_loop.py`:

```python
from pathlib import Path

from apps.workers.workflows.initialize_project import initialize_project_from_local_repo
from packages.harness.service import HarnessService
from packages.harness.memory_writeback import MemoryWritebackService
from packages.knowledge.context_engine import ContextEngine
from packages.storage.opensearch.fake import FakeKeywordIndex
from packages.storage.qdrant.fake import FakeVectorIndex


def test_p0_loop(fake_core):
    keyword = FakeKeywordIndex()
    vector = FakeVectorIndex()

    project = fake_core.create_project(
        org_id="org_1",
        name="Payment",
        slug="payment",
        git_remotes=["git@example.com:payment.git"],
    )
    init = initialize_project_from_local_repo(
        org_id="org_1",
        project_id=project.id,
        repo_path=Path("tests/fixtures/sample_repo"),
    )
    for asset in init.assets:
        stored = fake_core.create_asset(**asset.model_dump())
        keyword.index_asset(stored.id, asset)
        vector.index_asset(stored.id, asset)

    context_engine = ContextEngine(keyword_index=keyword, vector_index=vector)
    harness = HarnessService(core=fake_core, context_engine=context_engine)

    started = harness.start_work(
        user_message="分析如何实现退款失败重试",
        repo_remote="git@example.com:payment.git",
        agent_type="codex",
    )
    context = harness.plan_context(session_id=started.session_id, token_budget=1000)

    assert context.summary
    assert context.source_refs

    writeback_service = MemoryWritebackService(core=fake_core, keyword_index=keyword, vector_index=vector)
    writeback = writeback_service.prepare_writeback(
        org_id="org_1",
        project_id=project.id,
        session_id=started.session_id,
        type="development_summary",
        title="退款失败重试总结",
        content="退款失败重试需要限制次数并保持幂等。",
    )
    writeback_service.accept_writeback(writeback.id)

    later = context_engine.plan_context(
        org_id="org_1",
        project_id=project.id,
        intent="implementation",
        query="退款失败重试 幂等",
        token_budget=1000,
    )
    assert "幂等" in later.summary
```

- [ ] **Step 2: Run E2E test to verify failure**

Run: `pytest tests/e2e/test_p0_loop.py -v`

Expected: FAIL until all prior chunks are implemented.

- [ ] **Step 3: Fix integration gaps**

Only fix integration issues in existing modules. Do not add new feature scope.

- [ ] **Step 4: Run full backend test suite**

Run: `pytest -v`

Expected: PASS.

- [ ] **Step 5: Add demo script**

Create `scripts/run_p0_demo.py` that runs the same flow and prints:

- project initialized.
- context summary.
- skill output.
- writeback accepted.
- later retrieval summary.

- [ ] **Step 6: Run demo script**

Run: `python scripts/run_p0_demo.py`

Expected: script prints all five demo checkpoints.

- [ ] **Step 7: Commit**

```bash
git add tests/e2e scripts
git commit -m "test: add Agora P0 end-to-end demo"
```

## Chunk 9: Verification and Documentation

### Task 19: Add Developer Documentation

**Files:**
- Modify: `README.md`
- Create: `docs/development/p0-demo.md`
- Create: `docs/development/mcp-agent-setup.md`

- [ ] **Step 1: Document backend setup**

Update `README.md` with:

- Python install.
- Docker Compose.
- API startup.
- Worker startup placeholder.
- MCP startup.
- Web startup.
- Test commands.

- [ ] **Step 2: Document P0 demo**

Create `docs/development/p0-demo.md`:

- Purpose.
- Fixture repo.
- Commands.
- Expected output.
- Troubleshooting.

- [ ] **Step 3: Document MCP agent setup**

Create `docs/development/mcp-agent-setup.md`:

- MCP tools list.
- Agent default rule.
- Example prompt: "帮我分析退款失败重试怎么做".
- Expected tool call flow.

- [ ] **Step 4: Run docs link sanity check**

Run: `rg "PLACEHOLDER|FIXME" README.md docs/development`

Expected: no unresolved placeholder or FIXME text unless deliberately documented as future work.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/development
git commit -m "docs: document Agora P0 development flow"
```

### Task 20: Final Verification

**Files:**
- No new files expected.

- [ ] **Step 1: Run backend tests**

Run: `pytest -v`

Expected: PASS.

- [ ] **Step 2: Validate compose**

Run: `docker compose -f infra/docker-compose.yml config`

Expected: PASS.

- [ ] **Step 3: Build web**

Run: `cd apps/web && npm run build`

Expected: PASS.

- [ ] **Step 4: Run P0 demo**

Run: `python scripts/run_p0_demo.py`

Expected: PASS and prints P0 checkpoints.

- [ ] **Step 5: Check git status**

Run: `git status --short`

Expected: no unexpected untracked or modified files.

- [ ] **Step 6: Commit final fixes if needed**

Only commit if previous verification required code or docs changes.

```bash
git add .
git commit -m "chore: finalize Agora P0 verification"
```

## Execution Notes

- Keep developers' main workflow Agent-first. Do not add CLI as a required developer path.
- Keep MCP tools high-level and Harness-oriented. Do not expose Qdrant/OpenSearch/Neo4j directly to agents.
- PostgreSQL/Core data is source of truth. Search and graph stores are derived indexes.
- Fakes are acceptable for early tests, but module boundaries must match the real components.
- Every accepted Writeback must become an Asset and be re-indexed.
- Each chunk should leave the repo in a passing state.
