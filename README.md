# ChangeProof

ChangeProof is an evidence-backed database change risk agent. It analyzes application and SQL migration changes, validates risk hypotheses with deterministic tools, and shows how remediation changes the risk score.

> Prove a change is safe before it ships.

## MVP scope

- GitHub pull requests and repositories
- PostgreSQL SQL migrations
- Application-to-schema dependency analysis
- Disposable Docker validation environments
- Evidence-linked deterministic risk scoring
- Remediation and re-validation

The current Phase 1 establishes the runnable web, API, and database foundation. Analysis capabilities are added incrementally so every phase stays testable.

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

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for native setup, tests, and project conventions. Architecture and product flow are documented in [docs/architecture.md](docs/architecture.md).

## Status

Phase 1: project bootstrap. See [DEVLOG.md](DEVLOG.md) for verified results and the next implementation target.
