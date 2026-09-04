# Decision

Evidence-grounded failure hypothesis generation using OpenAI Structured Outputs coupled with deterministic experiment compilation.

## Context

Phase 5 introduces AI reasoning to ChangeProof. Prior phases extract deterministic change facts from SQL migrations and discover concrete application source code references. However, determining which failure scenarios are worth reproducing requires contextual reasoning: understanding whether a removed column, altered type, or added constraint can break application contracts.

We must introduce AI without sacrificing the determinism, safety, or credibility of the platform.

## Options Considered

1. **End-to-End LLM Agent with Tool/Shell Execution**:
   Allow an LLM to generate arbitrary shell commands, raw SQL queries, or Docker compose invocations.
   *Rejected*: Extreme security risk (prompt injection via repository code), non-reproducible, prone to hallucination, and violates safety boundaries.

2. **Full Deterministic Rule Matrix**:
   Pre-code every combination of SQL operation and code pattern with static heuristic rules.
   *Rejected*: Lacks semantic understanding of complex multi-file application behaviors and rationale explanations.

3. **Hybrid AI Hypothesis + Deterministic Experiment Compiler (Chosen)**:
   - AI is strictly restricted to reasoning: given ChangeFacts and DependencyEvidence, propose a `FailureHypothesis` and choose an allowlisted `ExperimentTemplate`.
   - Untrusted Data Prompt Boundary: Repository content and excerpts are treated as untrusted data; instructions within code comments cannot override safety rules.
   - Deterministic `ExperimentCompiler`: Validates SQL identifiers and compiles concrete, safe, read-oriented SQL steps without shell access.
   - Unverified Semantics: Hypotheses are marked `UNVERIFIED` and experiment plans are marked `NOT_EXECUTED`. No false verdicts (`PROVEN_FAIL`, `PROVEN_PASS`, `Risk 87%`) are produced before actual execution.

## Decision

Adopt the Hybrid AI Hypothesis + Deterministic Experiment Compiler pattern:
1. Use OpenAI SDK structured parsing (`beta.chat.completions.parse`) with Pydantic schemas.
2. Supply only minimal structured context (`ChangeFactSummary`, `EvidenceSummary`) — never send full repository source or API credentials.
3. Validate all model outputs domain-wise: `change_ids` and `evidence_ids` must be subsets of provided facts; `experiment_template` must be in the template allowlist.
4. Delegate execution plan synthesis exclusively to `ExperimentCompiler`.

## Consequences

- **Safety**: Prompt injection cannot trigger arbitrary command execution or destructive SQL queries.
- **Reliability**: If OpenAI is unavailable, unconfigured, or rate-limited, the pipeline degrades gracefully with structured warnings while preserving all deterministic facts.
- **Humility**: Predictions are never presented as proven facts; verification is deferred to the Phase 6 ephemeral PostgreSQL environment.
- **Limitations**: Hypotheses may still reflect imperfect reasoning, which is why actual proof is only determined by observed sandbox results in subsequent phases.
