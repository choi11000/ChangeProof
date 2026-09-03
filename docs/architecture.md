# Architecture

## Product invariant

ChangeProof never converts an LLM opinion directly into a verdict. Facts come from deterministic tools and every confirmed risk points to evidence.

```text
1. Change Intake             GitHub pull request                    COMPLETE
2. Change Understanding      File classification + SQL parsing     COMPLETE
3. Dependency Discovery      Application <-> schema                NEXT
4. Failure Hypothesis
5. Experiment Planning
6. Execution                 Ephemeral PostgreSQL
7. Evidence                  Observed results
8. Remediation
9. Re-execution              Same experiment
10. Proof
```

The product promise is not merely to predict failure. ChangeProof is designed to reproduce a concrete failure before production, remediate it, and rerun the same experiment to prove the result.

## Runtime components

- `apps/web`: Next.js App Router interface for PR input and analysis results.
- `apps/api`: FastAPI HTTP boundary and future explicit analysis state machine.
- `clients/github.py`: timeout-bounded GitHub REST access and safe upstream error mapping.
- `services/pull_request_service.py`: explicit change-intake orchestration with injected clients.
- `analyzers/file_classifier.py`: deterministic path-based classification and content policy.
- `postgres`: persistent product data such as analyses, steps, and evidence.
- `sandbox-postgres`: opt-in disposable target for migration validation.
- `samples/risky-saas`: synthetic demonstration repository with known-positive risks.

## SQL change analysis

`SqlMigrationParser` parses PostgreSQL DDL with sqlglot and converts supported statements into Pydantic contracts. Each record identifies the source statement, operation, affected table or column, type/default/nullability/reference metadata, and whether the operation is destructive. Unsupported non-DDL statements produce no fabricated changes; invalid SQL returns a domain-specific parse error.

## GitHub pull request intake

`POST /api/v1/analyses/github-pr` normalizes a GitHub repository reference, verifies the repository, fetches typed PR metadata and changed files, and classifies every path. SQL migrations are fetched as complete content from the head SHA rather than parsed from a diff. Removed migrations are fetched from the base SHA for identity but are deliberately not treated as new executable SQL. One unavailable or invalid SQL file becomes a structured warning instead of failing the entire analysis.

The intake records the completed steps `FETCH_PR_METADATA`, `FETCH_CHANGED_FILES`, `CLASSIFY_FILES`, `FETCH_SQL_CONTENT`, and `ANALYZE_SQL`. Logs contain only repository/PR identifiers and aggregate facts.

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
