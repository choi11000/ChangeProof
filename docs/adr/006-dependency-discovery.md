# Decision

Bounded repository snapshot at PR head SHA with deterministic cross-layer reference analysis.

## Context

Phase 4 must bridge database schema changes and application source code by discovering concrete references to affected database entities. We must prove where an affected column or table is referenced in application source files without relying on ungrounded LLM reasoning.

## Options

1. LLM repository reasoning / RAG embeddings: High latency, hallucination risk, probabilistic scores without deterministic proof.
2. Full compiler/AST semantic analysis (Python, TypeScript, Go, Java): High complexity and language-specific tooling burden inappropriate for hackathon MVP.
3. GitHub code search API: Incomplete indexing for unmerged PR head revisions and eventual consistency lag.
4. Bounded repository snapshot at PR head SHA + deterministic identifier/qualified reference matching: Reproducible, fast, cross-language, deterministic, testable, and strictly grounded in source lines.

## Decision

Use a bounded repository tree snapshot fetched at the exact PR head SHA. Filter candidates using content policies and file classification, collect source documents within configurable limits (300 files, 256 KiB per file, 5 MiB total), and apply deterministic identifier and qualified reference matching.

## Reasons

- Reproducible: Pinning to PR head SHA guarantees identical results regardless of default branch updates.
- Grounded: Every finding points to a file, line number, excerpt, and deterministic match kind.
- Comprehensive: Searches unchanged application files in the repository snapshot, not merely files modified in the PR diff.
- Secure: Reuses existing secret redaction, credential file exclusions, and content policy boundaries.
- Failure-tolerant: Truncated trees and scan limit overflows degrade gracefully with structured warnings instead of aborting the analysis.

## Consequences

Textual and contextual matching provides reference evidence rather than compiler-level semantic dependency proof. False positives from identical identifier names are mitigated by distinguishing qualified references, table+column contexts, and potential identifier matches.
