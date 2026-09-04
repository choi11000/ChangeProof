# ADR 009: Deterministic Remediation and Same-Experiment Proof

## Status

Accepted

## Context

A before-fail/after-pass display is not sufficient proof. If a client can choose a digest, submit a cached result, or alter the verification contract between runs, it can manufacture a “same experiment” claim. Remediation also introduces an execution boundary: arbitrary model- or repository-generated SQL would exceed the controlled MVP safety model.

## Decision

All execution and proof identities are server-owned. API requests may identify an allowlisted fixture but cannot submit digests, verdicts, SQLSTATEs, or run evidence.

Experiment identity is split into:

- `experiment_contract_digest`: SHA-256 over canonical sorted, compact UTF-8 JSON containing baseline schema, seed data, template, target, verification SQL, and verifier contract version.
- `subject_digest`: SHA-256 over canonical JSON containing migration content and the original/remediated candidate variant.

The proof service reruns the original subject authoritatively instead of trusting a prior UI run. It then selects a paired `ControlledRemediation`, executes the remediated subject under the same contract, and evaluates deterministic invariants.

`PROVEN_FIXED` requires all of the following:

1. The before verdict is `PROVEN_FAIL`.
2. The after verdict is `PROVEN_PASS`.
3. Contract digests are identical.
4. Subject digests differ.
5. Neither run has an infrastructure execution error.

If the same failure remains, the result is `NOT_FIXED`. Identity mismatch, missing evidence, or cleanup hygiene failure is `INCONCLUSIVE`; infrastructure failure is `EXECUTION_ERROR`.

Executable remediation is deterministic and allowlisted. AI may propose evidence-grounded failure hypotheses but cannot produce executable SQL, shell or Docker commands, or verdicts. Generic public repository changes remain non-executable in the MVP.

## Consequences

- Client tampering, stale run IDs, and cached verdicts are outside the proof trust boundary.
- A changed migration can be distinguished from a changed experiment.
- Proof generation requires two fresh PostgreSQL executions and therefore costs more database time, but introduces no additional OpenAI calls.
- Proof is scoped to one controlled experiment and is not a safety guarantee for an entire pull request or production system.
- Real end-to-end acceptance remains blocked on hosts without Docker/PostgreSQL; passing unit tests cannot be reported as runtime proof.
