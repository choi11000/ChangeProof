# ChangeProof — Submission & Evaluation Runbook

> **"Don't predict the failure. Reproduce it before production."**

ChangeProof bridges the critical gap between database schema migrations and application code. Rather than relying on speculative AI predictions or static regex scans, ChangeProof deterministically parses SQL migrations, extracts cross-layer application references, reasons over real failure modes, and proves them in isolated PostgreSQL sandboxes before code reaches production.

---

## 1. Quick Access & Demo Resources

| Resource | Value / Link |
| :--- | :--- |
| **Main Repository** | [https://github.com/choi11000/ChangeProof](https://github.com/choi11000/ChangeProof) |
| **Public Web App** | [https://changeproof-web-production.up.railway.app](https://changeproof-web-production.up.railway.app) |
| **Public API Origin** | [https://changeproof-api-production.up.railway.app](https://changeproof-api-production.up.railway.app) |
| **API Liveness** | [https://changeproof-api-production.up.railway.app/api/v1/health/live](https://changeproof-api-production.up.railway.app/api/v1/health/live) |
| **API Readiness** | [https://changeproof-api-production.up.railway.app/api/v1/health/ready](https://changeproof-api-production.up.railway.app/api/v1/health/ready) |
| **Public Demo PR** | [https://github.com/choi11000/changeproof-demo/pull/1](https://github.com/choi11000/changeproof-demo/pull/1) |
| **Demo Repository** | [https://github.com/choi11000/changeproof-demo](https://github.com/choi11000/changeproof-demo) |
| **Audited Demo Revision** | `08302ccf5e67d12eee0d6470ac1136f4f644cba5` |
| **Deployment Status** | `ONLINE & OPERATIONAL` (Railway public deployment with live OpenAI & Sandbox PostgreSQL) |

---

## 2. Evaluation Walkthrough (Judge Flow)

Follow these steps to evaluate the full verification and remediation loop:

```text
1. Load Demo PR
   │
2. Analyze Change
   ├── Structured Change Facts (AST Operation: DROP_COLUMN orders.legacy_status)
   ├── Cross-Layer Dependency Evidence (app/order_service.py:11 references legacy_status)
   ├── AI Failure Hypothesis (Schema mismatch will cause runtime breakage)
   └── Deterministic Experiment Plan (Template: DROPPED_COLUMN_REFERENCE)
   │
3. Run Experiment in Isolated PostgreSQL
   ├── Ephemeral Schema Provisioned (cp_run_<hex12>)
   ├── Baseline Schema + Seed Data applied
   ├── Subject Migration applied (DROP COLUMN legacy_status)
   ├── Verification Query executed (SELECT legacy_status FROM orders)
   └── VERDICT: PROVEN_FAIL (SQLSTATE 42703: undefined_column)
   │
4. Verify Remediation
   ├── Apply Non-Destructive Remediation (Preserve column / compatibility view)
   ├── Execute Same Verification Query Contract
   └── VERDICT: PROVEN_FIXED (Run is PROVEN_PASS with identical contract digest)
```

### Step-by-Step Instructions

1. **Open ChangeProof Dashboard**:
   Navigate to the web interface (e.g. `http://localhost:3000` or deployed URL).
2. **Load Demo PR**:
   Click the **"Load demo PR"** button. The input fields will populate:
   - Repository: `choi11000/changeproof-demo`
   - Pull Request: `1`
   *(Inputs are prefilled without automatically firing network calls).*
3. **Analyze Change**:
   Click **"Analyze change →"**. ChangeProof contacts GitHub, parses the SQL migration AST, gathers unchanged repository source files at the PR head commit, and presents:
   - **Structured Change Facts**: `DROP_COLUMN orders.legacy_status`
   - **Cross-Layer Evidence**: `app/order_service.py:11` qualified reference to `order.legacy_status`
   - **Evidence-Grounded AI Hypothesis**: Broken column read in `order_service.py`
   - **Deterministic Experiment Plan**: Dropped column reference experiment
4. **Reproduce Failure in Sandbox**:
   Click **"Run experiment in isolated PostgreSQL →"**.
   - An ephemeral schema `cp_run_<hex12>` is provisioned in PostgreSQL.
   - The migration is applied and the application query executed.
   - **Verdict**: `PROVEN_FAIL` with PostgreSQL SQLSTATE `42703` (`undefined_column`).
5. **Verify Remediation**:
   Click **"Verify remediation"**.
   - The same experiment verification query is executed against the non-destructive compatibility schema.
   - **Verdict**: `PROVEN_FIXED`. The exact same experiment passes (`PROVEN_PASS`), conclusively proving the fix.

---

## 3. Local Evaluation & Verification

To run ChangeProof locally with full PostgreSQL sandbox execution:

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 16+ (or Docker)

### Option A: Running with Docker Compose

```powershell
# 1. Clone repository
git clone https://github.com/choi11000/ChangeProof.git
cd ChangeProof

# 2. Configure environment
cp .env.example .env
# Edit .env to add your OPENAI_API_KEY and optional GITHUB_TOKEN

# 3. Start stack with sandbox profile
docker compose --profile sandbox up --build
```

Access the UI at `http://localhost:3000`.

### Option B: Native Host Execution

```powershell
# 1. Start Sandbox PostgreSQL (e.g. via docker or local service)
docker run -d --name cp-sandbox -p 5433:5432 -e POSTGRES_PASSWORD=changeproof -e POSTGRES_USER=changeproof -e POSTGRES_DB=changeproof_sandbox postgres:17-alpine

# 2. Run API backend
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
uvicorn app.main:app --port 8000

# 3. Run Web frontend (in a separate terminal)
cd apps/web
npm install
npm run dev
```

---

## 4. Security & Safety Architecture

1. **Exact Demo Identity Authorization (`ControlledDemoPolicy`)**:
   - Substring matching has been removed.
   - Sandbox execution is exclusively permitted when `repository.full_name`, `pull_request.number`, and `pull_request.head_sha` match the audited server-side identity (`choi11000/changeproof-demo#1` at SHA `08302ccf5e67d12eee0d6470ac1136f4f644cba5`).
   - Unaudited revisions or public repositories can be analyzed for facts and hypotheses, but sandbox execution is safely disabled:
     > *"Sandbox execution is disabled because this demo revision is not the audited revision."*
2. **Ephemeral PostgreSQL Isolation**:
   - Every experiment executes inside a randomly generated schema namespace: `cp_run_<hex12>`.
   - Schemas are forcibly dropped via `DROP SCHEMA CASCADE` in a guaranteed `finally:` block.
   - Strict `statement_timeout = '5s'` and `lock_timeout = '2s'` prevent hanging transactions.
3. **No Docker Socket Mounting**:
   - ChangeProof does not mount `/var/run/docker.sock` and does not spawn untrusted containers at runtime.
4. **Secret Redaction**:
   - All connection strings, passwords, and tokens are redacted from logs and client-facing API responses.

---

## 5. Automated Verification Results

- **Backend Test Suite**: 176 passed, 11 skipped (requiring active sandbox), **95.10% coverage** (exceeds the 90% threshold).
- **Backend Linting**: `ruff check .` clean (0 errors), `python -m compileall app` clean.
- **Frontend Test Suite**: 6/6 Vitest unit tests passed.
- **Frontend Quality**: ESLint clean (0 warnings), TypeScript `tsc --noEmit` clean, Next.js optimized production build clean.
