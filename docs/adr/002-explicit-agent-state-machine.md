# Decision

Implement the analysis agent as an explicit Python state machine before considering an agent framework.

## Context

The product must distinguish AI reasoning from deterministic validation and expose every pipeline input, output, and failure.

## Options

- Framework-managed graph orchestration
- An explicit typed Python state machine
- A single unstructured LLM prompt

## Decision

Start with an explicit typed Python state machine whose transitions correspond to documented analysis steps.

## Reason

The MVP pipeline is linear enough to implement directly. Explicit transitions are easier to test, log, persist, and explain during a demonstration.

## Consequences

We own transition and retry behavior. A graph framework is introduced only if branching or resumability becomes costly to maintain directly.
