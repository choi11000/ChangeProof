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

## 2026-09-03 — Phase 4 Cross-Layer Dependency Discovery & Impact Evidence

### Added

- Typed dependency target, match kind, evidence, impact summary, repository tree, and source document contracts
- GitHub client repository tree retrieval at PR `head_sha` (`GET /repos/{owner}/{repo}/git/trees/{head_sha}?recursive=1`)
- Bounded repository source collection (`RepositorySourceService`) with file count (300), file size (256 KiB), and total bytes (5 MiB) limits
- Graceful degradation for truncated trees and scan limit overflows via typed analysis warnings
- Deterministic pure dependency analyzer (`DependencyAnalyzer`) supporting `QUALIFIED_REFERENCE`, `TABLE_AND_COLUMN_CONTEXT`, `COLUMN_IDENTIFIER`, and `TABLE_IDENTIFIER`
- Schema dependency target extraction from `DROP_COLUMN`, `ALTER_COLUMN_TYPE`, `SET_NOT_NULL`, `DROP_NOT_NULL`, `SET_DEFAULT`, `DROP_DEFAULT`, and `DROP_TABLE`
- Support for snake_case, camelCase, and PascalCase identifier variants without probabilistic or LLM reasoning
- Secret redaction for evidence code excerpts (`redact_lines`)
- Acceptance test verifying reference discovery in unchanged application files (`order.legacy_status` in `app/order_service.py` with `changed_in_pull_request=False`)
- Frontend Impact Surface metrics and Dependency Evidence list with "Not changed in this PR" badges and match kind indicators
- Architecture decision record `docs/adr/006-dependency-discovery.md`

### Decisions

- Repository tree snapshot is fetched at exact PR `head_sha` to examine the candidate PR state rather than changed files only.
- Deterministic reference matching is used; no LLMs, embeddings, vector databases, or fake confidence percentages.
- Exact and bounded text/context matches are used instead of aggressive fuzzy or semantic matching.
- Content policies from Phase 3 (skipping `.env`, keys, secrets, lockfiles, and binaries) are reused across all source scanning.
- Dynamic tracking of `completed_steps` records only successfully completed pipeline stages.

### Tests

- API: `pytest` PASS (85 tests, 97.16% coverage)
- API: `ruff check .` PASS
- API: Python bytecode compilation PASS
- Web: `npm ci`, ESLint, TypeScript typecheck, Vitest (3 tests), and production build PASS
- Web: `npm audit` PASS (0 vulnerabilities)
- Browser smoke: live web/API interaction and error flow PASS with no console errors
- Docker: NOT AVAILABLE on this host

### Known Limitations

- Textual and contextual matching provides reference evidence, not compiler-level semantic dependency proof.
- FastAPI/Starlette TestClient emits two upstream deprecation warnings involving `httpx`.
- Docker is not installed on this host.

### Git

Branch: `feature/dependency-discovery` (stacked on `feature/github-pr-intake`)

Commits:

- `4d9f539 feat: add repository source collection and tree acquisition`
- `0f8d091 feat: discover application references to schema changes`
- `6cfd26c test: cover cross-layer dependency discovery`
- `1461df1 docs: document dependency evidence architecture`
- `00ee4b4 fix: harden dependency evidence semantics`

## 2026-09-03 — Phase 5 Evidence-Grounded Failure Hypothesis & Executable Experiment Planning

### Added

- Typed failure hypothesis schemas (`FailureHypothesis`, `FailureCategory`, `HypothesisStatus`, `HypothesisProposalResult`)
- Typed experiment plan schemas (`ExperimentPlan`, `ExperimentTemplate`, `ExperimentStep`, `ExperimentStepType`, `ExperimentStatus`)
- OpenAI client layer (`OpenAIHypothesisClient`) with Responses API, Structured Outputs, and domain error mapping
- Prompt injection boundary declaring repository content as untrusted data
- Safe failure planning service (`FailurePlanningService`) with domain validation (ID containment, template allowlist, max 3 hypotheses)
- Deterministic experiment compiler (`ExperimentCompiler`) generating safe, read-only SQL validation queries without shell execution
- Acceptance test for Phase 5 failure hypothesis generation and experiment planning
- Prompt injection safety test with malicious code comments
- Frontend Failure Hypotheses & Proposed Experiment Plans display with `UNVERIFIED` and `NOT EXECUTED YET` badges
- Architecture decision record `docs/adr/007-failure-hypothesis-planning.md`

### Decisions

- AI reasoning is introduced strictly for hypothesis proposals; deterministic compiler produces the executable plan.
- Arbitrary commands, arbitrary SQL, shell access, and Docker commands are strictly prohibited in the LLM output.
- Hypotheses remain UNVERIFIED and plans remain NOT_EXECUTED until actual execution in Phase 6 sandbox.
- If OpenAI is not configured, rate limited, or fails, the pipeline degrades gracefully with typed warnings without failing PR analysis.
- Domain validation drops any hypothesis that hallucinates non-existent change IDs or evidence IDs.

### Tests

- API: `pytest` PASS (113 tests, 96.92% coverage)
- API: `ruff check .` PASS
- API: Python bytecode compilation PASS
- Web: `npm ci`, ESLint, TypeScript typecheck, Vitest (4 tests), and production build PASS
- Web: `npm audit` PASS (0 vulnerabilities)
- Browser smoke: live web/API interaction, form submission, and error flow PASS with no console errors
- Real OpenAI smoke: live `gpt-4o-mini` structured output test PASS
- Docker: NOT REQUIRED for Phase 5 (No sandbox execution until Phase 6)

### Known Limitations

- Hypotheses are evidence-grounded proposals and remain unverified until executed in Phase 6 ephemeral environments.
- FastAPI/Starlette TestClient emits two upstream deprecation warnings involving `httpx`.
- Docker is not installed on this host.

### Git

Branch: `feature/failure-experiment-planning` (stacked on `feature/dependency-discovery`)
Commit: `455d315 feat: implement failure hypothesis and experiment planning`
PR: #2 (GitHub stacked PR `feature/failure-experiment-planning` -> `feature/dependency-discovery`)

## 2026-09-03 — Phase 5.1 API Alignment & Phase 6 Ephemeral PostgreSQL Experiment Execution

### Added

- `OpenAIHypothesisClient` aligned with official OpenAI Responses API (`client.responses.parse`) using `instructions` and `output_parsed`
- Forwarding of `OPENAI_API_KEY`, `OPENAI_MODEL`, and `GITHUB_TOKEN` into API container in `compose.yaml`
- Safe additive migration fixture `samples/risky-saas/migrations/005_safe_add_external_reference.sql`
- Port mapping `127.0.0.1:5433:5432` for `sandbox-postgres` service in `compose.yaml`
- Phase 6 Execution schemas (`ExperimentVerdict`, `ExperimentStepStatus`, `ExperimentStepResult`, `ExperimentRun`, `ExecuteExperimentRequest`, `ExecuteExperimentResponse`) in `app/schemas/execution.py`
- Server-controlled fixture registry (`app/fixtures/experiment_registry.py`) with strict demo allowlist (`risky-saas/drop-legacy-status`, `risky-saas/drop-payments`, `risky-saas/set-not-null`, `risky-saas/shrink-email`, `risky-saas/safe-additive`)
- Ephemeral PostgreSQL executor (`PostgresExperimentExecutor`) using `psycopg` protocol with unique isolated schema per run (`cp_run_<hex12>`), statement (`10s`) and lock (`5s`) timeouts, and guaranteed `DROP SCHEMA CASCADE` in `finally`
- Deterministic verifier (`ExperimentVerifier`) mapping PostgreSQL execution results and SQLSTATE codes (`42703`, `23502`, `22001`, `42P01`) to `PROVEN_FAIL`, and safe clean migrations to `PROVEN_PASS`
- Plan digest computation (`compute_plan_digest`) for tamper-evident audit lineage
- Credential and secret redaction (`redact_secrets`) preventing leak of database passwords or connection URLs in step messages
- Execution service (`ExperimentExecutionService`) and endpoint `POST /api/v1/experiments/execute`
- Frontend "Run experiment in isolated PostgreSQL →" button for controlled fixtures
- Safe boundary notice: "Sandbox execution is limited to controlled demo fixtures in this MVP" for generic PRs
- Frontend `OBSERVED RESULT` card displaying `PROVEN_FAIL` / `PROVEN_PASS` badges, SQLSTATE codes, step results checklist, execution durations, and plan digest
- Unit and integration tests for executor, verifier, registry, service, and web UI

### Decisions

- AI is completely excluded from determining experiment verdicts or SQLSTATE errors. Proof is strictly derived from PostgreSQL engine responses.
- Docker socket is never mounted into containers; no child processes or shell commands (`docker`, `psql`, `bash`) are executed.
- Generic PRs are restricted from arbitrary sandbox execution (`execution_allowed: false`) to eliminate arbitrary SQL injection risk.
- Ephemeral per-run schemas (`cp_run_<hex12>`) provide isolation within the sandbox database without requiring per-run container spin-up latency.
- Real sandbox integration tests use `@pytest.mark.sandbox` and skip cleanly when sandbox PostgreSQL is not reachable on `localhost:5433`.

### Tests

- API: `pytest` PASS (130 passed, 5 skipped for sandbox, 94.16% coverage > 90% required)
- API: `ruff check .` PASS
- API: Python bytecode compilation PASS
- Web: ESLint PASS (0 warnings)
- Web: TypeScript typecheck PASS
- Web: Vitest PASS (5 tests passed)
- Web: Next.js production build PASS
- Web: npm audit PASS (0 vulnerabilities)

### Acceptance & Docker Status

- **Host Docker Status**: Docker is NOT installed or running on this Windows host machine (`CommandNotFoundException`).
- **Phase 6 Verification Status**:
  - Implementation: **COMPLETE**
  - Unit, mock-executor, and web component tests: **100% PASS**
  - Live Docker sandbox runtime execution on this host: **BLOCKED** due to Docker unavailable on host (per Rule 59).

### Git

Branch: `feature/postgres-experiment-execution` (stacked on `feature/failure-experiment-planning`)
Commits:
- `c8cf57d fix: forward AI credentials into API container`
- `7c7623a refactor: align OpenAI hypothesis client with Responses API`

## 2026-09-03 — Phase 6.1 Runtime Proof & Integrity Hardening

### Added

- Server-owned canonical `experiment_contract_digest` and `subject_digest` identities
- Strict request validation rejecting client-supplied digest fields
- Exact SQLSTATE-only failure attribution and incomplete-step safeguards
- Cleanup observability independent of the PostgreSQL hypothesis verdict

### Tests

- API: `pytest` PASS (139 passed, 5 sandbox tests skipped, 95.25% coverage)
- API: Ruff and Python bytecode compilation PASS
- Web: ESLint, TypeScript, Vitest, production build, and npm audit PASS
- Real PostgreSQL acceptance: BLOCKED because Docker is unavailable on this host

### Status

- Execution implementation: **COMPLETE**
- Runtime PostgreSQL acceptance: **BLOCKED**
- Evidence implementation: **COMPLETE**
- Runtime evidence proof: **NOT VERIFIED**




