# ChangeProof — 기술 신뢰성 입증 시트 (Technical Proof Sheet)

ChangeProof는 단순한 아이디어나 목업이 아닌, **실제 CI 및 공개 배포 환경에서 측정되고 검증된 객관적 기술 지표**를 보유하고 있습니다. 본 문서는 시스템의 기술적 신뢰성을 증명하는 수치 및 보안 검증 데이터를 정리합니다.

---

## 1. 정량적 테스트 및 코드 품질 지표 (Automated Quality Metrics)

| 구분 (Category) | 측정 지표 (Metric) | 결과 및 달성치 (Result) | 비고 (Remarks) |
| :--- | :--- | :--- | :--- |
| **백엔드 단위 테스트** | pytest 단위 테스트 | **176개 테스트 전체 통과 (PASS)** | `apps/api/tests/` |
| **백엔드 코드 커버리지** | pytest-cov | **94.92% (요구치 90% 초과 달성)** | 1,811 라인 중 1,719 라인 커버 |
| **실제 PostgreSQL CI 통합 테스트** | PostgreSQL 17.6 컨테이너 통합 검증 | **11개 샌드박스 통합 테스트 통과** | 마이그레이션 실행, 오류 코드 포착, 복구 증명 |
| **정적 분석 및 린트** | Ruff linter | **0 경고, 0 오류 (Clean)** | PEP 8 및 최신 Python 3.12 컨벤션 준수 |
| **프론트엔드 단위 테스트** | Vitest (Testing Library) | **6개 컴포넌트 테스트 전체 통과 (PASS)** | 한국어 기본값, 언어 토글, E2E 폼 검증 |
| **프론트엔드 타입 안정성** | TypeScript (`tsc --noEmit`) | **0 오류 (Type-check Clean)** | 엄격 모드 (`strict: true`) |
| **프론트엔드 린트** | ESLint (`--max-warnings=0`) | **0 경고, 0 오류 (Clean)** | Next.js 16 및 React 19 규칙 준수 |
| **프로덕션 빌드** | Next.js 16 (Turbopack) | **최적화 정적 빌드 성공** | Route `/` 및 `/_not-found` 정상 최적화 |
| **GitHub Actions CI 파이프라인** | 4개 병렬 워크플로 잡 | **모든 Job 통과 (100% Green)** | `backend-unit`, `backend-postgres-integration`, `container-build`, `frontend` |

---

## 2. 라이브 배포 및 실환경 동작 증빙 (Live Production Acceptance)

* **배포 환경**: Railway Platform (PaaS)
* **웹 프론트엔드**: [https://changeproof-web-production.up.railway.app](https://changeproof-web-production.up.railway.app) (Next.js 16, Node.js 24)
* **API 백엔드**: [https://changeproof-api-production.up.railway.app](https://changeproof-api-production.up.railway.app) (FastAPI, Python 3.12)
* **데이터베이스 샌드박스**: PostgreSQL 17.6 (Railway Private Mesh 내부망, 외부 노출 포트 없음)

### 실환경 재현 파이프라인 검증 결과 (Live Verified Flow)
1. **GitHub PR Ingestion**: 공식 데모 PR ([choi11000/changeproof-demo#1](https://github.com/choi11000/changeproof-demo/pull/1)) 커밋 `head_sha`에서 `ALTER TABLE orders DROP COLUMN legacy_status;` 정확히 감지.
2. **Deterministic Dependency Matching**: `app/order_service.py` 11번 라인의 `order.legacy_status` 직접 참조 포착.
3. **Live OpenAI Structured Outputs**: `gpt-4o-mini`를 통해 유효한 `FailureHypothesis` (상태: `UNVERIFIED`) 및 6단계 `ExperimentPlan` 수립.
4. **Isolated PostgreSQL Execution**: 임시 네임스페이스 `cp_run_<hex12>`에서 마이그레이션 실행 후 참조 쿼리 실행 시 실제 PostgreSQL 표준 오류 코드 **`SQLSTATE 42703 (undefined_column)`** 포착 $\rightarrow$ **`PROVEN_FAIL`** 발급.
5. **Deterministic Remediation**: 동일 실험 계약(`contract_...`) 하에서 복구 마이그레이션 적용 후 **`PROVEN_PASS`** 획득 $\rightarrow$ 최종 **`PROVEN_FIXED`** 증명 완결.
6. **시크릿 모드 무인증 테스트**: 브라우저 서브에이전트를 통해 개발자 세션/쿠키/로그인 없이 비로그인 상태에서 전체 플로우 100% 정상 수행 확인.

---

## 3. 보안 및 리소스 가드레일 (Security & Resource Boundaries)

* **원격 임의 코드 실행 차단**: 사용자가 제출한 SQL이나 AI가 생성한 임의 쿼리를 샌드박스에서 직접 실행하지 않으며, 사전에 엄격히 화이트리스트된 결정론적 템플릿만을 컴파일하여 실행합니다.
* **민감 정보 격리 및 비노출**: `OPENAI_API_KEY`, 데이터베이스 접속 패스워드 등 모든 자격증명은 Railway 환경 변수로만 주입되며, 프론트엔드 전달이나 로그 출력에서 원천 마스킹됩니다.
* **프라이빗 데이터베이스 메쉬**: PostgreSQL 인스턴스는 공인 IP를 갖지 않으며, 오직 `changeproof-api` 서비스만이 Railway 내부 전용 가상 사설망(`postgres.railway.internal:5432`)을 통해 접근합니다.
* **엄격한 리소스 제한**: 샌드박스 동시 실행 수 제한(최대 2개), 문장별 타임아웃(5초), 락 타임아웃(2초), 실행 후 `finally` 블록의 100% 강제 스키마 삭제(`DROP SCHEMA ... CASCADE`)를 보장합니다.
