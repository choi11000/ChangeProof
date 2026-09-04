# ADR 011: API Contract Proof Vertical

## Status

Accepted

## Context

ChangeProof was initially proven on a single vertical: PostgreSQL database schema migrations. A critical architectural and product question arises: Is ChangeProof merely a PostgreSQL migration checker, or is it a general-purpose, reusable Change Verification Engine?

Proving engine reusability requires implementing a second proof domain with real runtime observation rather than roadmap promises. We chose API contract breaking changes—specifically OpenAPI 3.x response field removal (`REMOVE_RESPONSE_FIELD`) consumed by unchanged client application code.

## Decision

1. **Second Proof Domain (API Contract)**:
   We extended the pipeline to ingest OpenAPI 3.x specifications (`openapi.yaml`, `openapi.yml`, `openapi.json`), compare base SHA and head SHA documents deterministically, and emit typed `REMOVE_RESPONSE_FIELD` ChangeFacts with stable semantic IDs.

2. **Deterministic Consumer Dependency Discovery**:
   We scan application source code for direct response field references (e.g. `response["email"]`, `response['email']`, `response.email`) within consumer client modules. Evidence discovery remains 100% deterministic; AI is never used to discover dependencies.

3. **No Arbitrary Repository Execution**:
   To prevent remote code execution (RCE) and supply-chain vulnerabilities, ChangeProof **never** executes untrusted repository code. It never executes `npm install`, `pip install`, arbitrary shell commands, postinstall scripts, or GitHub Actions.

4. **Server-Owned Controlled ASGI Runtime**:
   The API contract experiment executes using a server-owned in-process ASGI runtime (`starlette.testclient.TestClient`) with no external network egress. The server maintains controlled fixtures (`api-contract/remove-user-email`) with verified baseline, changed, and remediated responses. The test executes a real HTTP request (`GET /users/1`) and runs a deterministic consumer probe against the actual HTTP response payload with zero external network egress.

5. **Deterministic Observation Codes**:
   The API domain does not reuse or overload SQLSTATE. Instead, it introduces deterministic API observation codes (e.g., `API_MISSING_RESPONSE_FIELD`). Verdicts require exact observation code equality; string matching or heuristic guesswork is strictly forbidden.

6. **Unchanged Same-Experiment Proof Semantics**:
   The core proof invariant remains identical across both Database and API domains:
   - `before.contract_digest == after.contract_digest` (same experiment, same request endpoint, same consumer probe)
   - `before.subject_digest != after.subject_digest` (changed subject: missing field -> restored field)
   - `PROVEN_FAIL` + `PROVEN_PASS` = `PROVEN_FIXED`

## Consequences

- The ChangeProof engine is demonstrated to be domain-extensible across Database Schema and API Contract domains without rewriting core state machines or loosening security invariants.
- AI remains strictly an unverified hypothesis generator (`status=UNVERIFIED`). It cannot assign verdicts, generate executable code, or bypass the deterministic verifier.
- Backward compatibility is strictly preserved: existing PostgreSQL integration tests, SQLSTATE 42703 observations, and the live Database demo operate completely unchanged.
