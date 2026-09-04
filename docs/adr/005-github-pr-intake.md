# Decision

Use GitHub REST through a small injected httpx client for pull request intake.

## Context

Phase 3 must collect verifiable PR metadata, changed files, patches, and full migration content while remaining mockable, timeout-bounded, and safe for optional token authentication.

## Options

- PyGithub SDK
- GitHub REST through httpx
- GitHub GraphQL API

## Decision

Use an explicit asynchronous REST client built on httpx. Inject the client into the pull request service and mock HTTP with `httpx.MockTransport` in tests.

## Reason

The required GitHub endpoints are few and stable. A narrow client avoids SDK weight, makes request and error behavior visible, supports optional unauthenticated access, and allows deterministic tests without network calls.

## Consequences

ChangeProof owns response mapping, pagination, timeout, and rate-limit handling. Private repositories require a locally supplied read-only token. The MVP does not implement OAuth, GitHub App installation, webhooks, or automatic retry.
