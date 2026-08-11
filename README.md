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
