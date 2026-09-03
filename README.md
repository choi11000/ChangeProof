# ChangeProof

ChangeProof is an evidence-backed database change risk agent. It turns real pull-request changes into structured facts, reproducible experiments, observed evidence, and verified remediation.

> Prove a change is safe before it ships.

## MVP scope

- GitHub pull requests and repositories
- PostgreSQL SQL migrations
- Application-to-schema dependency analysis
- Disposable Docker validation environments
- Evidence-linked deterministic risk scoring
- Remediation and re-validation

The current stacked development branch ingests a GitHub pull request, classifies changed files, parses SQL migrations at the exact PR revision, discovers cross-layer application source references against the full repository snapshot at `head_sha`, and presents deterministic impact evidence.

## Quick start

Prerequisites: Docker Desktop with Compose v2.

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Web: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

No API keys are required for the bootstrap. Add keys only to the local `.env`; never commit them.

## GitHub PR analysis

Public repositories can be analyzed without authentication until GitHub's anonymous rate limit is reached. Set `GITHUB_TOKEN` only in `.env` for authenticated read-only requests or private repositories.

```http
POST /api/v1/analyses/github-pr
Content-Type: application/json

{
  "repository": "https://github.com/owner/repository",
  "pull_request": 42
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

See [DEVLOG.md](DEVLOG.md) for verified results and branch dependencies.
