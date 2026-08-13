# Agora

Agora is a team AI project harness.

## Local Development

```bash
python -m venv .venv
.venv/bin/pip install -e .
docker compose -f infra/docker-compose.yml up -d
.venv/bin/pytest
.venv/bin/uvicorn apps.api.main:app --reload
```

## Persistence

Agora uses `AGORA_DATABASE_URL` for runtime persistence. Local development defaults to
`sqlite+pysqlite:///.agora/agora.db`; Postgres can be enabled with a URL such as
`postgresql+psycopg://agora:agora@localhost:5432/agora`.

```bash
.venv/bin/alembic upgrade head
.venv/bin/python -m scripts.agora_admin rebuild-indexes --database-url sqlite+pysqlite:///.agora/agora.db
.venv/bin/python -m scripts.agora_admin reset-local --database-url sqlite+pysqlite:///.agora/agora.db --yes
```

## Web

```bash
cd apps/web
npm install
npm run build
```

## P0 Demo

```bash
.venv/bin/python scripts/run_p0_demo.py
```
