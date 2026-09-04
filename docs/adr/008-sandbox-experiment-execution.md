# Decision

Ephemeral PostgreSQL Experiment Execution with Server-Controlled Fixture Registry and Deterministic Verdict Attribution.

## Context

Phase 6 marks the critical transition of ChangeProof from hypothesis generation to physical failure reproduction:
> "Don't predict the failure. Reproduce it before production."

To prove whether a database change breaks production, the system must execute the migration and verification queries against an isolated PostgreSQL instance. However, executing database operations introduces severe security and determinism concerns:
1. Public GitHub PRs could contain malicious DDL, shell escapes, or resource exhaustion attacks.
2. Unisolated database runs could cross-contaminate schemas or leak credentials.
3. Verdicts must not be decided by AI hallucinations or probabilistic text matching.

## Options Considered

1. **Arbitrary SQL Execution from PR in Shared Sandbox**:
   Directly execute migration files and user queries from any submitted GitHub PR in the sandbox database.
   *Rejected*: Severe security hazard. Any public PR could drop tables, run infinite loops, or exploit database extensions.

2. **Docker Socket Passthrough / Child Subprocess Runner**:
   Mount `/var/run/docker.sock` into the API container and launch dynamic containers via `psql` or `docker` shell commands.
   *Rejected*: Container breakouts, arbitrary command execution risks, OS portability issues, and brittle subprocess management.

3. **Server-Controlled Synthetic Fixtures + Ephemeral Schema Isolation + Deterministic Verifier (Chosen)**:
   - **Controlled Fixture Registry**: Only server-validated, allowlisted demo fixtures (`risky-saas/*`) can be executed in this MVP. Generic public PRs are flagged `execution_allowed: false` with explicit notice.
   - **Protocol-Only Interaction**: All interactions use the native `psycopg` driver without invoking external shells or child processes.
   - **Schema-Level Isolation**: Every execution runs within a uniquely generated ephemeral schema (`cp_run_<hex12>`), with search path locked and `DROP SCHEMA CASCADE` guaranteed in a `finally` block.
   - **Deterministic Verdict Verifier**: Verdicts (`PROVEN_FAIL`, `PROVEN_PASS`, `INCONCLUSIVE`, `EXECUTION_ERROR`) are attributed exclusively by deterministic rules inspecting actual PostgreSQL status and SQLSTATE codes (e.g. `42703` for undefined column, `23502` for not null violation, `22001` for truncation). AI plays zero role in determining verdicts.
   - **Audit Trail via Plan Digest**: A deterministic digest (`plan_digest`) is recorded with each run to ensure immutable end-to-end lineage into Phase 7 remediation.

## Decision

Implement `PostgresExperimentExecutor`, `ExperimentVerifier`, and `ExperimentExecutionService`:
1. Use `psycopg` async/sync native connection to communicate with `sandbox-postgres` (mapped to `127.0.0.1:5433`).
2. Enforce strict statement (`10s`) and lock (`5s`) timeouts.
3. Automatically redact connection credentials and secrets in all step outputs.
4. Expose `POST /api/v1/experiments/execute` accepting controlled fixture IDs and plan references.
5. In the UI, visually separate `AI HYPOTHESIS (UNVERIFIED)` from `OBSERVED RESULT (PROVEN_FAIL)`.

## Consequences

- **Security**: No arbitrary code execution or uncontained DDL is possible. Host Docker socket is never exposed.
- **Accuracy**: Failures are verified by real PostgreSQL engine errors (SQLSTATE), not AI guesses.
- **Safety**: Safe control fixtures (additive changes) produce verified `PROVEN_PASS` verdicts, demonstrating false-positive avoidance.
- **Host Portability**: Environments without Docker running can run the full mock-backed test suite cleanly; live sandbox integration tests skip gracefully and report infrastructure status accurately.
