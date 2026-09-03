# Decision

Validate database changes against a disposable PostgreSQL instance isolated from product data.

## Context

Migration execution can be destructive. Validation evidence must be real without risking the ChangeProof application database.

## Options

- Validate against the product database
- Parse SQL without executing it
- Apply migrations to a disposable PostgreSQL database

## Decision

Use an opt-in, tmpfs-backed PostgreSQL Compose service for sandbox validation in the MVP.

## Reason

It matches the supported database, provides authentic execution errors, and is reproducible without retaining validated customer data.

## Consequences

Docker availability becomes a requirement for execution validation. Later phases must add timeouts, resource limits, cleanup, and untrusted SQL controls before accepting arbitrary repositories.
