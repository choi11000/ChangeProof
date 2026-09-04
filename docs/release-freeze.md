# ChangeProof — 제출 릴리즈 동결 선언 (Release Freeze Record)

원티드 AI 챔피언십 2026 예선 심사 기간 동안 라이브 서비스의 안정성을 보장하고 예상치 못한 리그레션(Regression)을 방지하기 위해 **제출 릴리즈 동결(Submission Freeze)**을 선언합니다.

---

## 1. 동결 기준 정보 (Freeze Baseline Information)

* **동결 일자**: 2026년 9월 4일
* **기준 브랜치**: `feature/api-contract-proof` (PR #7)
* **New Wanted Release Candidate**: `e34c5335d79a8626a9fc3168bf001610456479e5`
* **Previous Safe Rollback RC**: `964d4948de48a7f49502a8a70611981b09a7f977`
* **공개 Web URL**: [https://changeproof-web-production.up.railway.app](https://changeproof-web-production.up.railway.app)
* **공개 API URL**: [https://changeproof-api-production.up.railway.app](https://changeproof-api-production.up.railway.app)
* **공식 데모 저장소 (DB)**: [https://github.com/choi11000/changeproof-demo](https://github.com/choi11000/changeproof-demo) (PR #1, Head `08302ccf5e67d12eee0d6470ac1136f4f644cba5`)
* **공식 데모 저장소 (API)**: [https://github.com/choi11000/changeproof-api-demo](https://github.com/choi11000/changeproof-api-demo) (PR #1, Head `dddd69caa31a13e0a18c097ce837d3ffd51a82e1`)
* **검증된 정상 동작 결과**:
  * **Database Schema Proof**:
    * 변경 팩트: `DROP_COLUMN orders.legacy_status`
    * 의존성 증거: `app/order_service.py:11` (직접 참조)
    * AI 가설: `legacy_status 컬럼 삭제 시 런타임 장애 발생 가능` (상태: `UNVERIFIED`)
    * PostgreSQL 샌드박스 실행: `SQLSTATE 42703 (undefined_column)` $\rightarrow$ **`PROVEN_FAIL`**
    * 호환성 복구 검증: 동일 실험 계약(`contract_...`) 일치 $\rightarrow$ **`PROVEN_FIXED`**
  * **API Contract Proof**:
    * 변경 팩트: `REMOVE_RESPONSE_FIELD GET /users/{id} (email)`
    * 의존성 증거: `client/user_client.py:8` (`response["email"]` 미변경 직접 참조)
    * AI 가설: `email 필드 제거 시 클라이언트 KeyError 발생 가능` (상태: `UNVERIFIED`)
    * 격리된 ASGI 런타임 실행: HTTP 200, `API_MISSING_RESPONSE_FIELD` (`/email`) $\rightarrow$ **`PROVEN_FAIL`**
    * 호환성 복구 검증: 동일 실험 계약(`contract_...`) 일치, 주체 변경 $\rightarrow$ **`PROVEN_FIXED`**

---

## 2. 동결 기간 중 허용 작업 (Allowed Operations)

심사 기간 중에는 심사위원의 접속 가능성을 최우선으로 보호해야 하므로, 다음과 같은 **필수 유지보수 목적의 작업만 제한적으로 허용**됩니다:
1. **서비스 장애 긴급 복구**: Railway 인프라 다운타임이나 크래시 발생 시 서비스 재기동
2. **치명적인 보안 패치**: 긴급한 API 자격증명 교체나 취약점 패치
3. **제출 텍스트 오탈자 교정**: 원티드 접수 화면의 설명 문구 단순 수정

---

## 3. 동결 기간 중 금지 작업 (Prohibited Operations)

다음과 같이 기존 시스템의 계약(Contract)이나 동작을 변경시킬 수 있는 작업은 심사가 완료될 때까지 **엄격히 금지**됩니다:
* 새로운 SQL 파서 기능이나 문법 확장
* 새로운 실험 템플릿 추가
* AI 모델 버전 변경 (현재 `gpt-4o-mini` 고정) 또는 시스템 프롬프트 변경
* 새로운 데이터베이스 엔진(MySQL 등) 추가
* UI 레이아웃의 대규모 변경이나 재설계
* 백엔드 API 엔드포인트 경로 또는 요청/응답 스키마 변경
* AWS 등 타 클라우드로의 인프라 마이그레이션 (현재 안정화된 Railway 환경 유지)
