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

Commit: pending
