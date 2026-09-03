# Development

## Prerequisites

- Git 2.40+
- Python 3.11+
- Node.js 22 LTS with npm
- Docker Desktop / Docker Engine with Compose v2

## Environment

Copy `.env.example` to `.env`. The checked-in values are local-development defaults; secrets remain blank.

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
