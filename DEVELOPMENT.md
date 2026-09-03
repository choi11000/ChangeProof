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

The disposable PostgreSQL sandbox service runs on port `5433`:

```bash
docker compose --profile sandbox up -d sandbox-postgres
```

Run real PostgreSQL sandbox integration tests:

```bash
cd apps/api
pytest -m sandbox
```

Execute an isolated experiment via API:

```bash
curl -X POST http://localhost:8000/api/v1/experiments/execute \
  -H "Content-Type: application/json" \
  -d '{"fixture_id":"risky-saas/drop-legacy-status"}'
```

Verify an allowlisted remediation by authoritatively rerunning the before/after pair:

```bash
curl -X POST http://localhost:8000/api/v1/proofs/remediation \
  -H "Content-Type: application/json" \
  -d '{"fixture_id":"risky-saas/drop-legacy-status"}'
```

The request cannot submit verdicts, digests, SQLSTATEs, or prior run results. A real `PROVEN_FIXED` acceptance requires the sandbox PostgreSQL service; mocks do not satisfy the runtime gate.

## Git workflow

Create a focused branch from `main`, use Conventional Commits, run relevant checks, update `DEVLOG.md`, review `git diff`, and commit one meaningful change. Never commit `.env` or credentials.
