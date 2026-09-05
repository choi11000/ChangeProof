# ChangeProof — Submission & Evaluation Runbook

> **"트래픽이 몰리기 전에, 숨은 병목을 먼저 검증하세요."**
> *(Don't predict the failure. Reproduce the bottleneck before production.)*

ChangeProof는 기능 테스트(단일 요청)로는 정상 동작하지만, 실제 사용자가 몰렸을 때 외부 API 대기열이나 리소스 병목으로 인해 멈춰버리는 **프로덕션 부하 장애(Production Load Failure)**를 코드 변경 사실과 AI 가설을 바탕으로 배포 전에 재현하고 검증하는 **AI 테스트 에이전트**입니다.

---

## 1. Quick Access & Production Resources

| Resource | Value / Link |
| :--- | :--- |
| **Main Repository** | [https://github.com/choi11000/ChangeProof](https://github.com/choi11000/ChangeProof) |
| **Current Pivot PR** | [https://github.com/choi11000/ChangeProof/pull/8](https://github.com/choi11000/ChangeProof/pull/8) |
| **Production Web App** | [https://changeproof-web-production.up.railway.app](https://changeproof-web-production.up.railway.app) |
| **Production API Origin** | [https://changeproof-api-production.up.railway.app](https://changeproof-api-production.up.railway.app) |
| **API Liveness** | [https://changeproof-api-production.up.railway.app/api/v1/health/live](https://changeproof-api-production.up.railway.app/api/v1/health/live) |
| **API Readiness** | [https://changeproof-api-production.up.railway.app/api/v1/health/ready](https://changeproof-api-production.up.railway.app/api/v1/health/ready) |
| **Preview Web App** | [https://changeproof-web-preview.up.railway.app](https://changeproof-web-preview.up.railway.app) |
| **Preview API Origin** | [https://changeproof-api-preview.up.railway.app](https://changeproof-api-preview.up.railway.app) |
| **New Wanted Performance RC** | `7807251bf46bd4b309871ac7c9993c2a6155dd10` |
| **Previous Stable Multi-Domain RC** | `a8fda49e880df1ec71fc0ba1d3fc1c8bcc2667ae` |
| **Deployment Status** | `ONLINE & PRODUCTION VERIFIED` (Railway production + preview) |

---

## 2. Evaluation Walkthrough (Judge Flow)

### 0단계: 진입 및 첫인상 (10초 이해도)
메인 화면 진입 시 헤드라인을 통해 제품의 본질을 즉시 파악할 수 있습니다:
> *"트래픽이 몰리기 전에, 숨은 병목을 먼저 검증하세요."*
> (기능 테스트에서는 정상인데, 트래픽이 몰렸을 때 터지는 병목을 배포 전에 선제 검증하는 서비스)

### 1단계: 기능 테스트 통과 (Single Request Functional Pass)
- 메인 화면의 **'피크 장애 데모 실행'** 버튼을 클릭합니다.
- **결과**: `HTTP 200 PASS`
- **UI 메시지**: *"한 명이 사용하면 정상입니다."*

### 2단계: 코드 변경 팩트 확인 (Change Fact)
- **변경 사항**: `GET /dashboard` 엔드포인트에 `weather_client.get_current()` 외부 날씨 API 직접 호출 추가 (`EXTERNAL_CALL_ADDED_TO_REQUEST_PATH`)

### 3단계: AI 부하 가설 수립 (AI Risk Hypothesis)
- **AI 제안**: *"사용자가 몰릴 경우 외부 API 응답을 기다리는 요청이 쌓일 수 있습니다."*
- **상태 격리**: `PROPOSED / UNVERIFIED` (AI는 가설만 제안하며, 장애 증명은 deterministic verifier가 담당)

### 4단계: 피크 부하 실험 실행 (Real Controlled Peak Load)
- 서버 소유의 통제된 샌드박스 피크 부하(동시성 150, 총 300건 요청)를 실제 실행합니다.
- 화면에 *"피크 부하 실험 실행 중..."* 표시 후 실측 런타임 수치가 렌더링됩니다.

### 5단계: 병목 재현 판정 (PROVEN_BOTTLENECK)
- **한국어 주 라벨**: `병목 재현됨`
- **기술 배지**: `PROVEN_BOTTLENECK`
- **핵심 관측**: `DOWNSTREAM_QUEUE_AMPLIFICATION`
- **실측 지표**:
  * 대표 production 실행의 candidate p95: ~3,000ms (임계치 500ms 초과)
  * 다운스트림 큐 대기시간: ~1,400ms 발생

### 6단계: 호환성 복구 조치 안내 (Remediation)
- **Before**: 모든 요청이 외부 날씨 API를 동기식으로 직접 호출
- **After**: 짧은 캐시(short cache) + 중복 호출 병합(singleflight coalesce) + 타임아웃/fallback

### 7단계: 동일 부하 재실행 (Same Load Rerun)
- **'동일 부하 다시 실행'** 버튼을 클릭합니다.
- 동일한 부하 계약(`SAME LOAD`, `SAME CONDITIONS`, `CHANGED SUBJECT`)으로 재실행됩니다.

### 8단계: 복구 증명 완료 (PROVEN_RECOVERED)
- **한국어 주 라벨**: `복구 검증 완료`
- **기술 배지**: `PROVEN_RECOVERED`
- **핵심 실측 지표**: 복구 후 p95: ~1ms, 큐 대기시간: 0ms
- **기술 상세**: 화면의 처리량은 server-owned in-process controlled runtime throughput이며 실제 production capacity를 의미하지 않습니다.
- **유효 범위 고지 (Disclaimer)**:
  > *"이 결과는 해당 통제 부하 실험에서 확인된 병목과 복구에 적용되며, 실제 운영 환경 전체의 성능을 보장하지 않습니다."*

---

## 3. Secondary Compatibility Capabilities

기존에 검증된 2가지 compatibility vertical도 우측 상단 링크를 통해 접근할 수 있습니다:
1. **Database Schema Contract Proof**: `DROP_COLUMN orders.legacy_status` $\rightarrow$ `SQLSTATE 42703` $\rightarrow$ `PROVEN_FAIL` $\rightarrow$ `PROVEN_FIXED`
2. **API Contract Proof**: `REMOVE_RESPONSE_FIELD GET /users/{id} (email)` $\rightarrow$ `KeyError` $\rightarrow$ `PROVEN_FAIL` $\rightarrow$ `PROVEN_FIXED`

---

## 4. Local Runner Architecture (Enterprise Safe)

기업의 비공개 소스코드 보안을 위해 ChangeProof Runner는 개발/테스트 내부망 안에서 직접 동작할 수 있습니다:
```text
Developer
    ↓
Local Git / Private Repo
    ↓
ChangeProof Runner (CLI)
    ↓
Dev/Test Environment
    ↓
Measured Result (Deterministic Proof)
```
- 공개 데모: 서버 소유 격리 픽스처(server-owned fixture)로 안전하게 실행
- 엔터프라이즈 환경: 로컬 러너가 사내망 내부에서 부하를 실행하므로 GitHub 공개나 외부 코드 유출 불필요

---

## 5. Automated Verification Results

- **Backend Test Suite**: 216 passed, 0 failed, **93.72% coverage**
- **Performance Integration**: 통제 부하 모의 실행 및 회귀 민감도 100% 통과
- **Runner Suite**: 8/8 tests passed
- **Frontend Quality**: Vitest passed, ESLint 0 warnings, TypeScript 0 errors, Next.js optimized production build clean
- **GitHub Actions CI (Run 33878985875)**: 6/6 green
