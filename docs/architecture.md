# Architecture

## Product invariant

ChangeProof never converts an LLM opinion directly into a verdict. Facts come from deterministic tools and every confirmed risk points to evidence.

```text
1. Change Intake             GitHub pull request                    COMPLETE
2. Change Understanding      File classification + SQL parsing     COMPLETE
3. Dependency Discovery      Application <-> schema                COMPLETE
4. Failure Hypothesis        Evidence-grounded AI reasoning        COMPLETE
5. Experiment Planning       Deterministic ExperimentCompiler      COMPLETE
6. Execution                 Ephemeral PostgreSQL                  COMPLETE
7. Evidence                  Observed SQLSTATE results             COMPLETE
8. Remediation               Deterministic schema fix              NEXT
9. Re-execution              Same experiment
10. Proof
```

The product promise is not merely to predict failure:
> Don't predict the failure. Reproduce it before production.

## Runtime components

- `apps/web`: Next.js App Router interface for PR input, change facts, dependency evidence, failure hypotheses, experiment plans, and observed PostgreSQL execution results.
- `apps/api`: FastAPI HTTP boundary, PR analysis pipeline, and experiment execution router.
- `clients/github.py`: timeout-bounded GitHub REST access for PRs, files, and repository trees.
- `clients/openai_client.py`: timeout-bounded OpenAI client using Responses API with Structured Outputs.
- `services/pull_request_service.py`: change-intake, dependency discovery, and planning orchestration.
- `services/repository_source_service.py`: bounded source snapshot collection at PR head SHA.
- `services/failure_planning_service.py`: safe failure planning orchestration and domain validation.
- `services/experiment_execution_service.py`: controlled fixture validation, executor invocation, and deterministic verdict synthesis.
- `analyzers/file_classifier.py`: deterministic path-based classification and content policy.
- `analyzers/dependency.py`: deterministic target extraction, reference matching, and impact summary.
- `analyzers/experiment_compiler.py`: deterministic compiler generating executable, read-oriented experiment plans.
- `analyzers/experiment_verifier.py`: deterministic verifier attributing PostgreSQL observations to `PROVEN_FAIL` / `PROVEN_PASS` / `INCONCLUSIVE` / `EXECUTION_ERROR`.
- `executors/postgres_experiment.py`: ephemeral schema isolation (`cp_run_<hex12>`), statement/lock timeouts, and secret-redacted execution runner.
- `fixtures/experiment_registry.py`: server-controlled registry of synthetic demo fixtures.
- `postgres`: persistent product data such as analyses, steps, and evidence.
- `sandbox-postgres`: disposable target for isolated experiment execution.
- `samples/risky-saas`: synthetic demonstration repository with known-positive risks.

## SQL change analysis

`SqlMigrationParser` parses PostgreSQL DDL with sqlglot and converts supported statements into Pydantic contracts. Each record identifies the source statement, operation, affected table or column, type/default/nullability/reference metadata, and whether the operation is destructive. Unsupported non-DDL statements produce no fabricated changes; invalid SQL returns a domain-specific parse error.

## GitHub pull request intake

`POST /api/v1/analyses/github-pr` normalizes a GitHub repository reference, verifies the repository, fetches typed PR metadata and changed files, and classifies every path. SQL migrations are fetched as complete content from the head SHA rather than parsed from a diff. Removed migrations are fetched from the base SHA for identity but are deliberately not treated as new executable SQL. One unavailable or invalid SQL file becomes a structured warning instead of failing the entire analysis.

## Cross-layer dependency discovery

`DependencyAnalyzer` and `RepositorySourceService` bridge schema changes and application source code. The pipeline extracts dependency targets from destructive and schema-altering SQL changes (`DROP_COLUMN`, `ALTER_COLUMN_TYPE`, nullability/default modifications, and `DROP_TABLE`).

Instead of inspecting only PR changed files, ChangeProof fetches the complete repository tree snapshot at the PR `head_sha`. Candidate source files are filtered through strict content policies (excluding secrets, keys, lockfiles, and binaries) and bounded by configurable safety limits (300 files, 256 KiB per file, 5 MiB total content).

References are matched using deterministic identifier boundaries and categorized into `QUALIFIED_REFERENCE` (direct property, index, or dot access), `TABLE_AND_COLUMN_CONTEXT` (vicinity co-occurrence), and `COLUMN_IDENTIFIER` / `TABLE_IDENTIFIER` (bare symbol reference). Every match produces a `DependencyEvidence` record with path, line number, match kind, secret-redacted excerpt, and whether the referencing file was changed in the PR or existed previously in the repository.

This phase provides deterministic source-reference evidence, not compiler-level semantic dependency proof.

## Failure hypothesis & executable experiment planning

Phase 5 introduces AI reasoning strictly bounded by deterministic facts:
1. **AI Hypothesis Generator**: An LLM reads only minimal structured context (change facts, evidence summaries, scan completeness, and warnings). It proposes testable `FailureHypothesis` records (`status=UNVERIFIED`) and selects an allowlisted `ExperimentTemplate`. The prompt boundary enforces that repository excerpts are untrusted data; the AI cannot invent IDs or generate arbitrary commands.
2. **Domain Validation**: The service validates that referenced change IDs and evidence IDs strictly belong to the provided set, and ensures the template is allowlisted.
3. **Deterministic Experiment Compiler**: `ExperimentCompiler` generates executable `ExperimentPlan` records (`status=NOT_EXECUTED`) using allowlisted, safe, read-only SQL patterns without shell command execution.

The intake records the completed steps `FETCH_PR_METADATA`, `FETCH_CHANGED_FILES`, `CLASSIFY_FILES`, `FETCH_SQL_CONTENT`, `ANALYZE_SQL`, `BUILD_CHANGE_FACTS`, `EXTRACT_DEPENDENCY_TARGETS`, `FETCH_REPOSITORY_TREE`, `FETCH_APPLICATION_CONTENT`, `DISCOVER_DEPENDENCIES`, `SUMMARIZE_IMPACT`, `GENERATE_FAILURE_HYPOTHESES`, `VALIDATE_HYPOTHESES`, and `COMPILE_EXPERIMENT_PLANS`. Logs contain only repository/PR identifiers and aggregate facts.

## Planned analysis state

Each pipeline stage accepts and returns typed state. The state will contain repository and PR metadata, changed files, SQL changes, affected entities, dependencies, hypotheses, validation tasks, evidence, deterministic score, remediation, and verification. Step transitions will be logged and exposed to the UI.

## Trust boundaries

- Secrets and credential-like content are redacted before any AI request.
- Secret-bearing files and binary/lockfile content are excluded; credential-like patch and SQL fields are redacted before they can leave the intake boundary.
- GitHub, AI, Docker, and database errors produce explicit failed-step results.
- LLM output may propose hypotheses and explanations but cannot invent tool results, evidence, or scores.
- Sandbox validation uses disposable infrastructure separated from product data.

## Deployment shape

The bootstrap runs as three services through Docker Compose. The web UI communicates with the API; only the API accesses persistent PostgreSQL. A production deployment can map the same boundaries to managed services without changing the pipeline contract.
