# ChangeProof — 제출 릴리즈 동결 선언 (Release Freeze Record)

원티드 AI 챔피언십 2026 예선 심사 기간 동안 검증된 릴리즈 상태를 보존하고 예상치 못한 리그레션(Regression) 가능성을 낮추기 위해 **제출 릴리즈 동결(Release Freeze: ACTIVE)**을 선언합니다.

---

## 1. 동결 기준 정보 (Freeze Baseline Information)

* **동결 일자**: 2026년 9월 4일
* **기준 브랜치**: `feature/production-load-proof` (PR #8)
* **New Wanted Performance RC**: `7807251bf46bd4b309871ac7c9993c2a6155dd10`
* **Previous Safe Rollback RC**: `a8fda49e880df1ec71fc0ba1d3fc1c8bcc2667ae`
* **공개 Web URL**: [https://changeproof-web-production.up.railway.app](https://changeproof-web-production.up.railway.app)
* **공개 API URL**: [https://changeproof-api-production.up.railway.app](https://changeproof-api-production.up.railway.app)
* **공식 데모 저장소 (DB)**: [https://github.com/choi11000/changeproof-demo](https://github.com/choi11000/changeproof-demo) (PR #1)
* **공식 데모 저장소 (API)**: [https://github.com/choi11000/changeproof-api-demo](https://github.com/choi11000/changeproof-api-demo) (PR #1)
* **검증된 정상 동작 결과**:
  * **Primary: Production Load Failure Proof ("사용자가 몰리기 전에, 병목을 먼저 재현하세요")**:
    * 기능 테스트: HTTP 200 `PASS` ("한 명이 사용하면 정상입니다.")
    * 변경 팩트: `GET /dashboard` + 새로운 외부 날씨 API 호출 (`EXTERNAL_CALL_ADDED_TO_REQUEST_PATH`)
    * AI 부하 가설: `사용자가 몰릴 경우 외부 API 응답을 기다리는 요청이 쌓일 수 있습니다.` (상태: `PROPOSED / UNVERIFIED`)
    * 피크 부하 실험 실행: 300 요청, 동시성 150 통제 부하 실행
    * 관측 및 판정: `DOWNSTREAM_QUEUE_AMPLIFICATION`, **병목 재현됨 (`PROVEN_BOTTLENECK`)**
      * 대표 production 실행의 candidate p95: 약 3,000ms
      * 다운스트림 큐 대기시간: 약 1,400ms 발생
    * 복구 검증: 동일 부하 재실행 (`SAME LOAD`, `SAME CONDITIONS`, `CHANGED SUBJECT`)
    * 최종 복구 판정: **복구 검증 완료 (`PROVEN_RECOVERED`)**
      * 복구 p95: 1ms, 다운스트림 큐 대기시간: 0ms
    * 유효 범위 고지: *"이 결과는 해당 통제 부하 실험에서 확인된 병목과 복구에 적용되며, 실제 운영 환경 전체의 성능을 보장하지 않습니다."*
  * **Secondary 호환성 기능**:
    * **Database Schema Proof**: `DROP_COLUMN orders.legacy_status` $\rightarrow$ `SQLSTATE 42703` $\rightarrow$ `PROVEN_FAIL` $\rightarrow$ `PROVEN_FIXED`
    * **API Contract Proof**: `REMOVE_RESPONSE_FIELD GET /users/{id} (email)` $\rightarrow$ `KeyError` $\rightarrow$ `PROVEN_FAIL` $\rightarrow$ `PROVEN_FIXED`

---

## 2. 동결 기간 중 허용 작업 (Allowed Operations)

심사 기간 중에는 심사위원의 접속 가능성을 최우선으로 보호해야 하므로, 다음과 같은 **필수 유지보수 목적의 작업만 제한적으로 허용**됩니다:
1. **서비스 장애 긴급 복구**: Railway 인프라 다운타임이나 크래시 발생 시 서비스 재기동
2. **치명적인 보안 패치**: 긴급한 API 자격증명 교체나 취약점 패치
3. **제출 카피 및 에셋 정비**: 원티드 접수 화면 설명 문구, 데모 영상 및 스크린샷 갱신

---

## 3. 동결 기간 중 금지 작업 (Prohibited Operations)

다음과 같이 기존 시스템의 계약(Contract)이나 런타임 동작을 변경시킬 수 있는 작업은 심사가 완료될 때까지 **엄격히 금지**됩니다:
* DB Lock 경합(P1) 또는 커넥션 풀 고갈(P2) 추가 금지
* 새로운 수직 영역(vertical)이나 플랫폼 연동 추가 금지
* AI 모델 버전 변경 또는 비결정론적 프롬프트 확장 금지
* 백엔드 API 엔드포인트 경로 또는 요청/응답 스키마 변경 금지
* Railway 인프라 구성 임의 변경 금지
