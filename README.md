# ChangeProof

ChangeProof is an evidence-backed database change risk agent. It turns real pull-request changes into structured facts, reproducible experiments, observed evidence, and verified remediation.

> Don't predict the failure. Reproduce it before production.

## MVP scope

- GitHub pull requests and repositories
- PostgreSQL SQL migrations
- Application-to-schema dependency analysis
- Ephemeral PostgreSQL experiment execution in isolated schemas
- Deterministic SQLSTATE attribution and verdict verification (`PROVEN_FAIL` / `PROVEN_PASS`)
- Evidence-linked failure proof
- Remediation and re-validation (Phase 7)

The current stacked development branch ingests a GitHub pull request, classifies changed files, parses SQL migrations at the exact PR revision, discovers cross-layer application source references across the repository tree at `head_sha`, derives evidence-grounded failure hypotheses, compiles safe experiment plans, and executes controlled synthetic fixtures in isolated PostgreSQL schemas to reproduce failures and capture concrete SQLSTATE evidence.

## Quick start

Prerequisites: Docker Desktop with Compose v2.

```bash
cp .env.example .env
docker compose up --build
```

To enable the isolated PostgreSQL sandbox for live experiment execution:

```bash
docker compose --profile sandbox up -d sandbox-postgres
```

Open:

- Web: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

No API keys are required for the bootstrap. Add keys only to the local `.env`; never commit them.

## GitHub PR analysis & Experiment Execution

Public repositories can be analyzed without authentication until GitHub's anonymous rate limit is reached. Set `GITHUB_TOKEN` only in `.env` for authenticated read-only requests or private repositories.

```http
POST /api/v1/analyses/github-pr
Content-Type: application/json

{
  "repository": "https://github.com/owner/repository",
  "pull_request": 42
}
```

To execute a controlled experiment fixture in isolated PostgreSQL:

```http
POST /api/v1/experiments/execute
Content-Type: application/json

{
  "fixture_id": "risky-saas/drop-legacy-status"
}
```

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for native setup, tests, and project conventions. Architecture and product flow are documented in [docs/architecture.md](docs/architecture.md).

## Status

| Phase | Status |
| --- | --- |
| 1 — Service bootstrap | On `main`; complete |
| 2 — SQL migration parser | Complete on `feature/sql-change-parser`; not merged to `main` |
| 3 — GitHub PR intake | Complete on stacked `feature/github-pr-intake`; not merged to `main` |
| 4 — Dependency discovery | Complete on stacked `feature/dependency-discovery`; not merged to `main` |
| 5 — Failure hypothesis & experiment planning | Complete on stacked `feature/failure-experiment-planning`; not merged to `main` |
| 6 — Ephemeral PostgreSQL experiment execution | Complete on stacked `feature/postgres-experiment-execution`; not merged to `main` |

See [DEVLOG.md](DEVLOG.md) for verified results and branch dependencies.
