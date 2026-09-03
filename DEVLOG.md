# Development Log

## 2026-09-03

### Added

- Git repository and focused project-bootstrap branch
- Next.js and Tailwind CSS landing page with a pull request analysis form
- FastAPI service with typed health endpoint
- Persistent and disposable PostgreSQL Compose services
- Container definitions, environment template, and secret-safe ignore rules
- API and frontend smoke tests
- Local development, architecture, and architecture decision documentation

### Decisions

- PostgreSQL is the only MVP database target.
- The agent will use an explicit Python state machine instead of an orchestration framework.
- Migration validation will run against an isolated disposable database.
- Next.js 16 and Python 3.11+ are the supported application baselines.

### Tests

- API: `pytest` PASS (2 tests, 100% coverage)
- API: `ruff check .` PASS
- Web: ESLint PASS
- Web: TypeScript type check PASS
- Web: Vitest PASS (1 test)
- Web: Next.js production build PASS
- Web: npm audit PASS (0 vulnerabilities)
- Browser smoke test PASS (form controls visible/enabled, no console errors)
- Compose YAML parse PASS; Docker runtime validation unavailable because Docker is not installed on this host

### Git

Branch: `feature/project-bootstrap`

Commit: `c64e3b8 feat: bootstrap ChangeProof development environment`

## 2026-09-03 — SQL migration analysis

### Added

- Typed PostgreSQL SQL change contracts
- sqlglot-backed deterministic migration parser
- CREATE/DROP table and index parsing
- ADD/DROP/ALTER column parsing including nullability and defaults
- Foreign-key reference extraction and destructive-operation flags
- Synthetic risky SaaS schema, seed data, application dependency, and four migration scenarios
- Demo scenario documentation and parser tests

### Decisions

- sqlglot 30.17.0 is pinned as the PostgreSQL AST parser.
- Unsupported non-DDL statements return no changes rather than inferred facts.
- Invalid migrations raise a domain-specific error without exposing fabricated results.

### Tests

- API: `pytest` PASS (8 tests, 97.6% coverage)
- API: `ruff check .` PASS
- API: Python bytecode compilation PASS

### Git

Branch: `feature/sql-change-parser`

Commit: `f809e1e feat: implement SQL migration parser`

## 2026-09-03 — Phase 3 GitHub PR intake

### Added

- GitHub repository reference normalization and validation
- Timeout-bounded GitHub REST client for repository, PR, changed-file, and revision content retrieval
- Typed GitHub metadata, classified-file, warning, SQL analysis, and pipeline-step contracts
- Deterministic changed-file classification with explanations
- Full head-revision migration analysis through the existing Phase 2 SQL parser
- Base-revision handling for removed migrations and per-file partial failure isolation
- Secret-bearing patch and SQL redaction, protected-file policies, binary exclusions, and 1 MiB SQL limit
- Typed `POST /api/v1/analyses/github-pr` endpoint and safe HTTP error mapping
- Existing frontend form integration with loading, error, summary, and SQL change results
- Mocked GitHub client, classifier, security, API, and end-to-end PR pipeline tests

### Decisions

- GitHub REST with injected `httpx.AsyncClient` is used instead of a full SDK or GraphQL.
- Phase 3 is stacked on unmerged `feature/sql-change-parser`; no automatic merge was performed.
- SQL analysis uses full content at the PR head SHA, never the changed-files patch.
- Removed migrations are identified from base SHA but not analyzed as executable changes.
- Network tests use `httpx.MockTransport`; no real token or network dependency is present.

### Tests

- API: `pytest` PASS (64 tests, 96.53% coverage)
- API: `ruff check .` PASS
- API: Python bytecode compilation PASS
- Web: clean `npm ci`, ESLint, TypeScript, Vitest (2 tests), and production build PASS
- Web: npm audit PASS (0 vulnerabilities)
- Browser: live web/API error and success flows PASS with no console errors
- GitHub live smoke: public PR metadata and three changed files fetched/classified successfully
- Docker: NOT AVAILABLE on this host

### Known Limitations

- FastAPI/Starlette TestClient emits two upstream deprecation warnings involving `httpx`; production GitHub REST usage still requires `httpx`, so dependency churn was deferred.
- Docker is not installed on this host; sandbox execution is outside Phase 3 and was not run.
- GitHub changed-files pagination is capped at 3,000 files, matching GitHub's endpoint limit.

### Git

Branch: `feature/github-pr-intake` (stacked on `feature/sql-change-parser`)

Commits:

- `c9adba5 feat: add GitHub pull request intake pipeline`
- `0224e9d feat: connect dashboard to PR analysis`
