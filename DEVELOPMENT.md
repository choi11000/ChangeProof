# Development

## Prerequisites

- Git 2.40+
- Python 3.11+
- Node.js 22 LTS with npm
- Docker Desktop / Docker Engine with Compose v2

## Environment

Copy `.env.example` to `.env`. The checked-in values are local-development defaults; secrets remain blank.

`GITHUB_TOKEN` is optional for public repositories and recommended to avoid the anonymous API rate limit. Private repository analysis requires a token with the narrowest read-only repository access possible. Never place a real token in source, tests, logs, or committed documentation.

## API

```bash
cd apps/api
python -m venv .venv
.venv/Scripts/activate
python -m pip install -e ".[dev]"
pytest
ruff check .
uvicorn app.main:app --reload
```

Analyze a pull request after the API starts:

```bash
curl -X POST http://localhost:8000/api/v1/analyses/github-pr \
  -H "Content-Type: application/json" \
  -d '{"repository":"owner/repository","pull_request":42}'
```

On Linux/macOS, activate with `source .venv/bin/activate`.

## Web

```bash
cd apps/web
npm ci
npm run lint
npm run typecheck
npm test
npm run dev
```

## Containers

```bash
docker compose config
docker compose up --build
```

The disposable PostgreSQL service is opt-in for future validators:

```bash
docker compose --profile sandbox up sandbox-postgres
```

## Git workflow

Create a focused branch from `main`, use Conventional Commits, run relevant checks, update `DEVLOG.md`, review `git diff`, and commit one meaningful change. Never commit `.env` or credentials.
