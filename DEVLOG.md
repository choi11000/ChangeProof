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

## 2026-09-03 — Phase 7 Deterministic Remediation & Same-Experiment Proof

### Added

- Four allowlisted remediation subjects for the controlled risky SaaS fixtures
- Deterministic remediation strategies and registry; no arbitrary or AI-generated execution
- Server-authoritative `POST /api/v1/proofs/remediation` before/after rerun workflow
- `PROVEN_FIXED`, `NOT_FIXED`, `INCONCLUSIVE`, and `EXECUTION_ERROR` aggregate verdicts
- UI remediation action and before/same-contract/after proof presentation
- ADR 009 documenting proof identity, trust boundaries, and experiment-scoped claims

### Tests

- API: `pytest` PASS (150 passed, 11 sandbox tests skipped, 95.13% coverage)
- API: Ruff and Python bytecode compilation PASS
- Web: ESLint, TypeScript, Vitest (5 tests), production build, and npm audit PASS
- Browser smoke: local UI controls and heading visible, no console errors; proof interaction blocked by unavailable sandbox
- Actual PostgreSQL original/remediated acceptance: BLOCKED because Docker is unavailable

### Status

- Remediation implementation: **COMPLETE**
- Same-experiment re-execution implementation: **COMPLETE**
- End-to-end PostgreSQL proof: **NOT VERIFIED**

## 2026-09-03 — Phase 8 CI Runtime Proof, Public Service Hardening & AI Cost Guard

### Added

- Four-job GitHub Actions workflow for backend unit/coverage, PostgreSQL 17.6 integration, frontend quality/build/audit, and API/web container plus Compose validation
- CI-only required-sandbox gate preventing an unavailable database from becoming a green skipped suite
- Deterministic AI context budgets, target-aware evidence selection, transparent truncation statistics, output-token ceiling, usage metadata, versioned fingerprints, bounded TTL cache, and async single-flight
- Public-repository-only GitHub metadata boundary with a non-enumerating private repository error
- Endpoint-specific bounded per-client limits and one-slot-per-proof sandbox concurrency control
- Configurable CORS/docs, production setting validation, request correlation, sanitized unexpected errors, liveness, and sandbox readiness
- Build-time demo repository/PR configuration and a non-executing **Load demo PR** action
- ADR 010 and provider-neutral deployment/secret/spend guidance

### Actual PostgreSQL runtime proof

GitHub Actions run `33747973539`, job `backend-postgres-integration`, connected through psycopg to a real `postgres:17.6-alpine` service. Result: **11 passed, 0 skipped**.

- DROP COLUMN: SQLSTATE `42703`, `PROVEN_FAIL`
- DROP TABLE: SQLSTATE `42P01`, `PROVEN_FAIL`
- SET NOT NULL: SQLSTATE `23502`, `PROVEN_FAIL`
- ALTER TYPE: SQLSTATE `22001`, `PROVEN_FAIL`
- SAFE ADDITIVE: `PROVEN_PASS`
- Four remediation pairs: before `PROVEN_FAIL`, identical contract digest, different subject digest, after `PROVEN_PASS`, aggregate `PROVEN_FIXED`
- Cleanup metadata query: zero remaining `cp_run_%` schemas
- Concurrent safe-additive runs: isolated schemas and `PROVEN_PASS`

### Verification

- CI backend unit: **168 passed**, 11 deselected, **94.91% coverage**, Ruff and compileall PASS
- CI PostgreSQL integration: **11 passed**, no sandbox skip
- CI frontend: lint, typecheck, **6 tests**, build, and audit PASS
- CI container build: API image, web image, and Compose config PASS
- Local Docker: unavailable; local sandbox tests skip by design

### Git

Branch: `feature/submission-hardening` (stacked on `feature/remediation-proof-loop`)

Pull request: #5

## 2026-09-03 — Phase 9 Public Deployment, Controlled Demo PR & Submission Readiness

### Added

- `ControlledDemoPolicy` in `apps/api/app/services/controlled_demo_policy.py`: Server-side exact demo identity authorization enforcing `repository.full_name`, `pull_request.number`, and audited `head_sha` matching.
- Elimination of insecure substring matching (`"risky-saas" in repository.full_name.lower()`) preventing attacker-controlled execution.
- Safe degraded notice when unaudited revisions are analyzed: *"Sandbox execution is disabled because this demo revision is not the audited revision."*
- Audited server configuration: `CONTROLLED_DEMO_REPOSITORY`, `CONTROLLED_DEMO_PR`, `CONTROLLED_DEMO_HEAD_SHA`, and dynamic `PORT`.
- Public synthetic demo repository: [`choi11000/changeproof-demo`](https://github.com/choi11000/changeproof-demo) with open pull request [PR #1](https://github.com/choi11000/changeproof-demo/pull/1) at audited revision `08302ccf5e67d12eee0d6470ac1136f4f644cba5`.
- Dynamic PORT support in `apps/api/Dockerfile` for Railway compatibility.
- Comprehensive Railway deployment guide (`docs/deployment-railway.md`) detailing the 3-service configuration (Web, API, Disposable Sandbox PostgreSQL; omitting unused product DB).
- Comprehensive submission runbook (`docs/submission-runbook.md`) documenting judge walkthrough, local verification options, security guarantees, and execution proofs.
- Frontend "Load demo PR" UX improvements with demo hint and server-provided execution notices.

### Verification

- Backend unit tests: **176 passed**, 11 skipped (sandbox integration requiring live db), **95.10% coverage** (exceeds 90% requirement).
- Ruff check: **All checks passed!** (0 errors).
- Python compileall: **Clean**.
- Frontend: ESLint clean, TypeScript `tsc --noEmit` clean, Vitest **6/6 passed**, Next.js Turbopack optimized production build clean.
- Railway deployment status: `DEPLOYMENT AUTH BLOCKED` recorded truthfully pending user Railway credentials.

### Git

Branch: `feature/public-deployment` (stacked on `feature/submission-hardening`)

## 2026-09-03 — Phase 9.1 Railway Deployment Unblock, Live OpenAI & Public End-to-End Acceptance

### Added & Resolved

- **Railway Project & Service Provisioning**:
  - Project: `ChangeProof` (`f8da94c5-6d5a-4f04-a52a-7f3e442cf0d7`) under account `choi120792@gmail.com`.
  - Topology: 3 services (`changeproof-web`, `changeproof-api`, `Postgres`).
  - Disposable Sandbox PostgreSQL provisioned with private-mesh networking only (`postgres.railway.internal:5432`); zero public TCP exposure.
  - Persistent product DB deliberately omitted per Phase 9 stateless MVP architecture finding.
- **Dynamic Port & Packaging Fixes**:
  - Fixed GitHub client base64 decoding to strip standard MIME line breaks before decoding (`"".join(data["content"].split())`).
  - Copied synthetic fixture samples to `apps/api/samples` and made `get_repo_root()` discover `samples/risky-saas` dynamically across parent hierarchies.
  - Added `COPY samples ./samples` to `apps/api/Dockerfile` ensuring fixture files are present in containerized environments.
- **Production Public URLs**:
  - Web: `https://changeproof-web-production.up.railway.app`
  - API: `https://changeproof-api-production.up.railway.app`
  - Liveness & Readiness: `GET /api/v1/health/live` (200 OK), `GET /api/v1/health/ready` (200 OK, `sandbox: ready`).
- **Live OpenAI Acceptance**:
  - Real `gpt-4o-mini` reasoning verified on live API.
  - Successfully produced structured `FailureHypothesis` (`id: hypothesis_001`, `category: SCHEMA_CONTRACT_BREAK`, `status: PROPOSED` / `UNVERIFIED`) and 6-step `ExperimentPlan` (`template: DROPPED_COLUMN_REFERENCE`, `status: NOT_EXECUTED`).
  - Verified in-memory planning cache hit (`cache_hit: true` on subsequent identical request) and context budgeting.
- **Live PostgreSQL Sandbox Execution**:
  - Executed in real Railway PostgreSQL disposable database.
  - Provisioned ephemeral schema `cp_run_<hex12>`, executed pre-PR baseline, seed data, PR migration, and verification query.
  - Verified `PROVEN_FAIL` with exact PostgreSQL SQLSTATE `42703` (`UndefinedColumn: column "legacy_status" does not exist`).
  - Schema dropped with `cleanup_succeeded: true`.
- **Live Remediation Proof**:
  - Reran original/remediated pair against same contract digest (`contract_b58d...`).
  - Before: `PROVEN_FAIL` (SQLSTATE `42703`), After: `PROVEN_PASS` (`legacy_status` preserved during compatibility window).
  - Subject digest changed, contract digest identical, final verdict: `PROVEN_FIXED`.
- **Public Browser E2E Acceptance**:
  - Automated browser subagent executed full 10-step judge flow on `https://changeproof-web-production.up.railway.app`.
  - Verified "Load demo PR" populated `choi11000/changeproof-demo#1`.
  - Verified Change Facts, Dependency Evidence (`app/order_service.py` marked "Not changed in this PR"), AI Hypothesis, PostgreSQL failure reproduction, and remediation proof.
  - 0 console script errors captured.
- **Secret Audit**:
  - Confirmed `.env` is git-ignored (`git check-ignore .env` PASS).
  - Zero API keys, database credentials, or tokens in git commits.

### Verification

- Backend unit tests: **176 passed**, 11 skipped (sandbox integration requiring live db), **94.92% coverage** (exceeds 90% requirement).
- Linters: Ruff clean, python compileall clean.
- Frontend: ESLint clean, TypeScript `tsc --noEmit` clean, Vitest 6/6 passed, Next.js Turbopack production build clean.
- Public deployment status: **ONLINE & OPERATIONAL** (`https://changeproof-web-production.up.railway.app`).

### Git

Branch: `feature/public-deployment` (stacked on `feature/submission-hardening`)





