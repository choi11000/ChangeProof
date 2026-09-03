# Architecture

## Product invariant

ChangeProof never converts an LLM opinion directly into a verdict. Facts come from deterministic tools and every confirmed risk points to evidence.

```text
Change -> Understand -> Dependencies -> Risk hypothesis
       -> Validation plan -> Tool execution -> Evidence
       -> Deterministic score -> Remediation -> Re-validation
```

## Runtime components

- `apps/web`: Next.js App Router interface for PR input and analysis results.
- `apps/api`: FastAPI HTTP boundary and future explicit analysis state machine.
- `postgres`: persistent product data such as analyses, steps, and evidence.
- `sandbox-postgres`: opt-in disposable target for migration validation.
- `samples/risky-saas`: synthetic demonstration repository with known-positive risks.

## SQL change analysis

`SqlMigrationParser` parses PostgreSQL DDL with sqlglot and converts supported statements into Pydantic contracts. Each record identifies the source statement, operation, affected table or column, type/default/nullability/reference metadata, and whether the operation is destructive. Unsupported non-DDL statements produce no fabricated changes; invalid SQL returns a domain-specific parse error.

## Planned analysis state

Each pipeline stage accepts and returns typed state. The state will contain repository and PR metadata, changed files, SQL changes, affected entities, dependencies, hypotheses, validation tasks, evidence, deterministic score, remediation, and verification. Step transitions will be logged and exposed to the UI.

## Trust boundaries

- Secrets and credential-like content are redacted before any AI request.
- GitHub, AI, Docker, and database errors produce explicit failed-step results.
- LLM output may propose hypotheses and explanations but cannot invent tool results, evidence, or scores.
- Sandbox validation uses disposable infrastructure separated from product data.

## Deployment shape

The bootstrap runs as three services through Docker Compose. The web UI communicates with the API; only the API accesses persistent PostgreSQL. A production deployment can map the same boundaries to managed services without changing the pipeline contract.
