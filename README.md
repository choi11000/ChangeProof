# ChangeProof

**사용자가 몰리기 전에, 병목을 먼저 재현하세요.**  
*(Reproduce the bottleneck before peak traffic does.)*

ChangeProof analyzes software changes, identifies new peak-load risks, generates targeted load experiments with AI, and executes them in a controlled development environment before deployment.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Peak%20Load%20Proof-blue?style=for-the-badge&logo=railway)](https://changeproof-web-production.up.railway.app)
[![CI Status](https://img.shields.io/badge/CI-Passing-brightgreen?style=for-the-badge&logo=githubactions)](https://github.com/choi11000/ChangeProof/actions)
[![Test Coverage](https://img.shields.io/badge/Coverage-93.89%25-brightgreen?style=for-the-badge)](apps/api)

---

## 🎯 The Real Problem: The Peak-Load Blindspot

```text
Code / infrastructure change
   ↓
Functional test PASS (1 user, 15ms)
   ↓
Development environment appears completely healthy
   ↓
Production peak time arrives
   ↓
150 concurrent users hit the endpoint simultaneously
   ↓
New downstream dependency or lock contention amplifies latency
   ↓
Requests accumulate behind limited connection capacity
   ↓
Service experiences severe latency explosion (p95: 4.8s) or cascading timeouts
```

### The Typical Scenario
Before change:
```text
GET /dashboard → database lookup (15ms) → response
```

After risky change:
```text
GET /dashboard → database lookup → WeatherClient.get_current() (700ms external) → response
```

* **Functional test**: **PASS** (15ms mock or single request succeeds normally).
* **At 5 concurrent users**: Everything looks fine.
* **At peak traffic (150 concurrent users)**: Outbound connection capacity (10) saturates, requests queue, p95 explodes from **180ms to 4,820ms**, and timeouts reach 18%.

---

## 💡 What ChangeProof Does: Change-Aware Load Verification

ChangeProof is an **AI Test Agent** that reads **WHAT CHANGED** and compiles **WHAT NEW LOAD EXPERIMENT** should be executed because of that specific change.

```text
Code Change
   ↓
Deterministic Risk Facts (FastAPI route + external client call added to hot path)
   ↓
AI Risk Scenario Planner (OpenAI hypothesis: PROPOSED / UNVERIFIED)
   ↓
Deterministic Load Compiler (Bounded concurrency, safety caps)
   ↓
ChangeProof Runner (Async concurrent load generator)
   ↓
Runtime Observations (DOWNSTREAM_QUEUE_AMPLIFICATION, p95 4,820ms, timeouts 18%)
   ↓
Deterministic Bottleneck Verdict (PROVEN_BOTTLENECK)
   ↓
Remediation Applied (10s TTL Cache + Request Coalescing + 1.5s Timeout)
   ↓
SAME Load Experiment Executed (Identical contract digest, 150 concurrent users)
   ↓
Deterministic Recovery Verdict (PROVEN_RECOVERED, p95 310ms, timeouts 0%)
```

---

## ⚡ Live Demo (ShiftSafe Workforce Safety Service)

Experience the 10-second instant visual contrast in the web application:

1. **Service**: Synthetic workforce safety dashboard (`GET /dashboard`).
2. **Functional Test**: `PASS (200 OK, 15ms)`.
3. **Risky Change**: Synchronous external `WeatherClient.get_current()` call added directly to the dashboard request path.
4. **Click "피크 트래픽 재현 실행"** (Run Peak Load):
   * 150 concurrent users, 300 requests, controlled 700ms downstream delay, capacity 10.
   * **Result**: p95 spikes to **4,820 ms**, 18% timeouts $\rightarrow$ **`PROVEN_BOTTLENECK`** (`DOWNSTREAM_QUEUE_AMPLIFICATION`).
5. **Click "수정 적용 및 동일 부하 재실행"** (Verify Recovery under Same Load):
   * Applies cache + coalescing + 1.5s timeout.
   * Re-executes the **exact same 150-user load scenario**.
   * **Result**: p95 drops to **310 ms**, 0% timeouts $\rightarrow$ **`PROVEN_RECOVERED`** (`CONTRACT SAME: YES`, `CHANGED SUBJECT: YES`).

---

## 🖥️ Local Runner Agent (`apps/runner`)

In enterprise environments with private repositories, DLP, DRM, or internal staging services unreachable from public SaaS, ChangeProof runs directly inside developer networks:

```bash
# 1. Install local runner
pip install -e apps/runner

# 2. Inspect local Git diff for performance risks
changeproof inspect --repo . --base HEAD~1

# 3. Verify peak load against local/dev environment
changeproof verify --base HEAD~1 --target http://localhost:8001

# 4. Output machine-readable JSON for CI/CD gates
changeproof verify --base HEAD~1 --target http://192.168.1.50:8001 --json
```

---

## ❓ Why Not Just k6, JMeter, or Gatling?

> **k6, JMeter, Gatling, and Locust are excellent load execution tools.**

ChangeProof focuses on a fundamentally different question:
* Existing tools ask: *"How many requests per second can this endpoint handle?"*
* **ChangeProof asks**: *"Given **THIS CODE CHANGE**, what **NEW** load scenario should we run?"*

Without ChangeProof, developers must manually hypothesize bottlenecks, script synthetic traffic, and maintain test scenarios for every PR. ChangeProof uses deterministic change facts and bounded AI reasoning to design the right experiment for the released diff automatically.

---

## ❓ Why Not Just ChatGPT?

A chat model can offer generic advice like *"Adding external API calls may cause latency under load."*

ChangeProof connects that reasoning to:
1. **Local code changes** in Git diffs.
2. **Controlled load scenarios** compiled deterministically.
3. **Actual concurrent execution** collecting per-request percentiles.
4. **Deterministic threshold verdicts** (`PROVEN_BOTTLENECK`).
5. **Same-experiment remediation proofs** (`PROVEN_RECOVERED`).

The value is the verified end-to-end workflow, not a chat suggestion.

---

## 🤖 The AI Role

OpenAI is strictly an **information synthesis and hypothesis authority**:
* **Generates**: Probable risk mechanisms, scenario classes, and explanations of why unit tests missed the issue.
* **Status**: Hypotheses always remain **`PROPOSED / UNVERIFIED`**.
* **AI never determines verdicts** and **never writes executable load scripts, shell commands, or arbitrary target URLs**.
* The deterministic compiler clamps all load parameters, and the deterministic verifier alone evaluates runtime metrics against invariant thresholds.

---

## 🛡️ Technical Trust Model

```text
DETERMINISTIC CHANGE ANALYSIS = FACT
OPENAI = PERFORMANCE HYPOTHESIS (PROPOSED / UNVERIFIED)
CONTROLLED LOAD RUNNER = OBSERVATION
DETERMINISTIC THRESHOLD VERIFIER = VERDICT

SAME LOAD EXPERIMENT
- CHANGED SUBJECT
- FAIL → PASS (p95: 4820ms → 310ms)
= PROOF (PROVEN_RECOVERED)
```

---

## 🔒 Security Boundaries

To prevent abuse or unintentional disruption:
* **Max Concurrency**: Clamped to 150 (demo) / 200 (runner max).
* **Max Requests**: Clamped to 300 (demo) / 1000 (runner max).
* **Target Environment Restrictions**:
  * Public web demo executes **only against server-owned controlled synthetic fixtures**.
  * Local Runner **strictly restricts execution to `localhost` and RFC1918 private subnets** (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
  * Arbitrary public domains and public IP addresses are rejected with `TargetSecurityError`.
* **Zero Code Exfiltration**: Raw repository source code remains local; only bounded change facts leave the environment.

---

## 📦 Compatibility Proofs (Secondary Vertical)

ChangeProof also preserves its deep contract verification vertical under the secondary **Compatibility Proofs** tab:
* **Database Schema Contract Proof**: Discovers unchanged application queries referencing dropped PostgreSQL columns and reproduces engine failure (`SQLSTATE 42703 • undefined_column` $\rightarrow$ `PROVEN_FAIL` $\rightarrow$ `PROVEN_FIXED`).
* **API Contract Proof**: Detects removed fields from OpenAPI specifications and proves client breakage under ASGI execution (`API_MISSING_RESPONSE_FIELD` $\rightarrow$ `PROVEN_FAIL` $\rightarrow$ `PROVEN_FIXED`).

---

## 🧪 Testing & Verification

```bash
# Backend unit & integration suite (208 tests, 93.89% coverage)
cd apps/api
pytest --cov=app --cov-report=term-missing

# Local runner agent suite (4 tests)
cd apps/runner
pytest

# Frontend vitest suite (5 tests) & Next.js production build
cd apps/web
npm test -- --run
npm run build
```
