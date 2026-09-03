# ADR 010: Public service guardrails

## Status

Accepted

## Context

A public ChangeProof instance can consume server-side GitHub and OpenAI credentials and can start comparatively expensive PostgreSQL experiments. Without explicit boundaries it could proxy access to private repositories, repeat identical model calls, accept unbounded client traffic, exhaust sandbox connections, or expose internal failures.

## Decision

- Repository analysis is public-only by default and mandatory in production. A GitHub credential must be public-only or fine-grained with the minimum repository access; a broad personal token must not be deployed.
- AI receives a deterministic bounded context. Application and strong references rank first, unchanged PR references are favored at equal strength, and an initial per-target selection prevents one target from consuming the whole evidence budget.
- The planning key hashes the PR head SHA, bounded context, model, and prompt version. Valid structured results are held in a bounded in-memory TTL cache, while failures and domain-invalid output are not cached. Concurrent identical requests use one async single-flight task.
- Endpoint-specific fixed-window client limits and a bounded sandbox semaphore constrain public work. A remediation before/after pair owns one logical sandbox slot.
- Unknown exceptions are correlated with a server request ID, redacted in traceback logs, and sanitized at the HTTP boundary.

## Consequences

The cache and rate-limit records are intentionally process-local to avoid Redis or another platform dependency in the MVP. They provide deterministic bounds for one API instance but do not coordinate replicas and reset on restart. A horizontally scaled deployment must add a shared implementation without changing the endpoint contracts. AI remains a hypothesis generator; PostgreSQL observations and deterministic verifiers remain the only source of verdicts.
