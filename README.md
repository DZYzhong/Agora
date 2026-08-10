# Agora

Agora is a team AI project harness.

## Local Development

```bash
docker compose -f infra/docker-compose.yml up -d
pytest
uvicorn apps.api.main:app --reload
```
