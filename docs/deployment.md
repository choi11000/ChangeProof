# Deployment

ChangeProof is provider-neutral: deploy the Next.js web image, FastAPI image, product PostgreSQL, and a separately scoped disposable sandbox PostgreSQL. Never mount a Docker socket and never allow public arbitrary SQL or repository migration execution.

## Environment matrix

| Variable | Purpose | Recommended production posture |
| --- | --- | --- |
| `APP_ENV` | Runtime mode | `production` |
| `DATABASE_URL` | Product database DSN | Platform secret |
| `SANDBOX_DATABASE_URL` | Isolated experiment database DSN | Platform secret; network-restricted to API |
| `GITHUB_TOKEN` | Optional GitHub REST credential | Public-only or minimum-scope fine-grained token |
| `GITHUB_PUBLIC_REPOSITORIES_ONLY` | Blocks private repository analysis | `true` (required in production) |
| `OPENAI_API_KEY` | Optional hypothesis generation | Platform secret; omit for deterministic-only mode |
| `OPENAI_MODEL` | Planning model | Explicit supported model |
| `OPENAI_MAX_OUTPUT_TOKENS` | Per-response output ceiling | `1200` default |
| `MAX_AI_CHANGES` / `MAX_AI_EVIDENCE` | Context item bounds | `50` / `30` defaults |
| `AI_CACHE_MAX_ENTRIES` / `AI_CACHE_TTL_SECONDS` | Process-local planning cache | `256` / `3600` defaults |
| `CORS_ALLOWED_ORIGINS` | Comma-separated web origins | Exact HTTPS origin; no wildcard |
| `API_DOCS_ENABLED` | OpenAPI/docs exposure | Disable unless demo or operations require it |
| `ANALYSIS_RATE_LIMIT` | Analysis requests/client/window | `10` default |
| `EXPERIMENT_RATE_LIMIT` | Experiment requests/client/window | `6` default |
| `PROOF_RATE_LIMIT` | Proof requests/client/window | `3` default |
| `RATE_LIMIT_WINDOW_SECONDS` | Fixed-window length | `60` default |
| `RATE_LIMIT_MAX_CLIENTS` | Bounded in-memory records | `4096` default |
| `TRUST_PROXY_HEADERS` | Trust first `X-Forwarded-For` value | `false`; enable only behind an overwriting trusted proxy |
| `MAX_CONCURRENT_SANDBOX_RUNS` | API-process sandbox slots | `2` default |
| `NEXT_PUBLIC_API_URL` | Browser-visible API origin | Public HTTPS API URL, supplied at web build time |
| `NEXT_PUBLIC_DEMO_REPOSITORY` | Optional public demo repository | Supply at web build time |
| `NEXT_PUBLIC_DEMO_PR` | Optional positive demo PR number | Supply at web build time |

The process exposes `/api/v1/health/live` without external calls and `/api/v1/health/ready` for safe configuration plus sandbox reachability. Do not use GitHub or OpenAI reachability as a restart signal.

## Secrets and spend bounds

`.env` is local only. Production secrets belong in the deployment platform's secret storage. Never commit `OPENAI_API_KEY`, `GITHUB_TOKEN`, or production database credentials, and never deploy ChangeProof with a broad personal access token that can read unrelated private repositories.

Use OpenAI project billing limits or prepaid balance. For a short-lived judging deployment, keep auto recharge disabled when a strict spend ceiling is desired. Application-level context budgets, token output limits, caching, single-flight, and endpoint rate limits add another guard; current model prices are deliberately not encoded in source or documentation.

## Single-instance limitation

The planning cache, rate limiter, and sandbox gate are bounded in-memory components. They reset on restart and do not coordinate multiple API replicas. Run one API instance for the MVP or introduce an explicitly designed shared store before horizontal scaling.
