# Railway Deployment Guide

This document details the production deployment topology and configuration for hosting ChangeProof on [Railway](https://railway.app).

---

## 1. Service Architecture (3-Service Configuration)

ChangeProof is deployed as a 3-service topology:

```text
┌─────────────────────────────────────────────────────────────┐
│                       Railway Project                       │
│                                                             │
│   ┌──────────────────┐               ┌──────────────────┐   │
│   │   Web Service    │  HTTPS CORS   │   API Service    │   │
│   │  (Next.js 16)    │ ────────────> │  (FastAPI/Py3.13)│   │
│   └──────────────────┘               └─────────┬────────┘   │
│                                                │            │
│                                                │ Private    │
│                                                │ Network    │
│                                                ▼            │
│                                      ┌──────────────────┐   │
│                                      │ Sandbox Postgres │   │
│                                      │ (Disposable DB)  │   │
│                                      └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Why 3 Services Instead of 4?

The ChangeProof architecture documents describe a future persistent `DATABASE_URL` for historical analysis archiving. In the current production-tested MVP, all pull request intake, SQL AST analysis, cross-layer dependency discovery, AI hypothesis planning, and ephemeral experiment execution operate statelessly, with isolated tests running in ephemeral schemas inside `SANDBOX_DATABASE_URL`.

To prevent unnecessary hosting costs and unused idle resources, **no product PostgreSQL database is provisioned**. Only the active **Disposable Sandbox PostgreSQL** is deployed alongside the Web and API services.

---

## 2. Environment Configuration Matrix

### API Service (`apps/api`)

| Variable | Recommended Production Value | Notes |
| :--- | :--- | :--- |
| `APP_ENV` | `production` | Enables production validation in Settings |
| `PORT` | `8000` | Process port binding |
| `CORS_ALLOWED_ORIGINS` | `https://changeproof-web.up.railway.app` | Exact HTTPS origin of Web service; no wildcards |
| `API_DOCS_ENABLED` | `false` | Disables OpenAPI docs in production |
| `GITHUB_PUBLIC_REPOSITORIES_ONLY` | `true` | Enforces public-repo-only access |
| `GITHUB_TOKEN` | *(Platform Secret)* | Optional token for higher GitHub rate limits |
| `OPENAI_API_KEY` | *(Platform Secret)* | Key for failure hypothesis reasoning |
| `OPENAI_MODEL` | `gpt-4o-mini` | Cost-effective, structured-outputs model |
| `OPENAI_MAX_OUTPUT_TOKENS` | `1200` | Strict output ceiling |
| `MAX_AI_CHANGES` | `50` | Bound input change facts |
| `MAX_AI_EVIDENCE` | `30` | Bound input dependency evidence |
| `AI_CACHE_MAX_ENTRIES` | `256` | In-memory cache entries |
| `AI_CACHE_TTL_SECONDS` | `3600` | Cache TTL (1 hour) |
| `ANALYSIS_RATE_LIMIT` | `10` | Max PR analyses per IP per window |
| `EXPERIMENT_RATE_LIMIT`| `6` | Max experiment runs per IP per window |
| `PROOF_RATE_LIMIT` | `3` | Max remediation proofs per IP per window |
| `RATE_LIMIT_WINDOW_SECONDS`| `60` | Fixed window duration (seconds) |
| `MAX_CONCURRENT_SANDBOX_RUNS`| `2` | Max concurrent database sandbox slots |
| `SANDBOX_DATABASE_URL`| `postgresql+psycopg://${PGUSER}:${PGPASSWORD}@${RAILWAY_PRIVATE_DOMAIN}:5432/${PGDATABASE}` | Internal private connection string to Sandbox PostgreSQL |
| `CONTROLLED_DEMO_REPOSITORY` | `choi11000/changeproof-demo` | Exact audited demo repository |
| `CONTROLLED_DEMO_PR` | `1` | Exact audited demo PR number |
| `CONTROLLED_DEMO_HEAD_SHA` | `08302ccf5e67d12eee0d6470ac1136f4f644cba5` | Exact audited demo PR head commit SHA |

### Web Service (`apps/web`)

| Variable | Build / Runtime | Value |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | Build-time ARG & Runtime | `https://changeproof-api.up.railway.app` |
| `NEXT_PUBLIC_DEMO_REPOSITORY` | Build-time ARG | `choi11000/changeproof-demo` |
| `NEXT_PUBLIC_DEMO_PR` | Build-time ARG | `1` |
| `PORT` | Runtime | `3000` |

### Sandbox PostgreSQL Service

- Image: `postgres:17.6-alpine`
- Private networking enabled (only accessible by the API service within the private mesh).
- Not publicly exposed to the internet.

---

## 3. Health Checks & Restart Signals

- **Live Check**: `GET /api/v1/health/live` (responds `200 OK` without hitting external services).
- **Ready Check**: `GET /api/v1/health/ready` (validates runtime configuration and tests sandbox PostgreSQL reachability via `SELECT 1`).
- *Note*: External third-party services (GitHub REST API, OpenAI API) are explicitly NOT part of the readiness check to avoid cascading restart loops during transient external upstream hiccups.

---

## 4. Current Deployment Status

```text
STATUS: DEPLOYED & OPERATIONAL
PROJECT: ChangeProof (f8da94c5-6d5a-4f04-a52a-7f3e442cf0d7)
PUBLIC WEB: https://changeproof-web-production.up.railway.app
PUBLIC API: https://changeproof-api-production.up.railway.app
SANDBOX POSTGRESQL: postgres.railway.internal:5432 (Private mesh only; zero public TCP exposure)
LIVE OPENAI: Connected (gpt-4o-mini, Structured Outputs)
```

The 3-service deployment topology is live and verified:
- **API Liveness & Readiness**: `200 OK` (`/api/v1/health/live` & `/api/v1/health/ready` reporting `sandbox: ready`).
- **Full Judge E2E Flow**: Verified in automated browser testing from "Load demo PR" to `PROVEN_FAIL` (SQLSTATE `42703`) and `PROVEN_FIXED`.
