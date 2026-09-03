# ChangeProof — 100초 제품 시연 영상 스크립트 (Demo Video Script)

* **영상 목표 시간**: 약 1분 45초 (105초)
* **해상도 및 형식**: 1080p 60fps / 자막 포함
* **배경 서비스**: [https://changeproof-web-production.up.railway.app](https://changeproof-web-production.up.railway.app)
* **핵심 메시지**: *"Don't predict the failure. Reproduce it before production. Fix it, run the same experiment again, and prove the result."*

---

## 타임라인 및 화면 구성 (Timeline & Visuals)

### [00:00 – 00:15] 문제 제기: Diff 중심 코드 리뷰의 사각지대
* **화면**:
  * GitHub PR 화면 클로즈업.
  * `migrations/001_drop_legacy_status.sql` 파일에 `ALTER TABLE orders DROP COLUMN legacy_status;`만 덩그러니 있는 diff 화면.
* **내레이션 (Voiceover)**:
  > "코드 리뷰는 '무엇이 바뀌었는가'는 잘 보여주지만, '이 변경이 실제 의존 코드를 부러뜨리는가'는 증명하지 못합니다. 특히 데이터베이스 마이그레이션은 변경되지 않은 앱 코드와 결합할 때 diff에 잡히지 않는 침묵의 배포 장애를 만듭니다."

---

### [00:15 – 00:30] 해결의 시작: 원클릭 데모 PR 로드
* **화면**:
  * ChangeProof 웹 메인 화면 (`https://changeproof-web-production.up.railway.app`).
  * 상단 우측 언어 전환기(`한국어 | English`) 확인.
  * **'데모 PR 불러오기'** 버튼 클릭 $\rightarrow$ `choi11000/changeproof-demo`, PR `1` 자동 입력 $\rightarrow$ **'변경사항 분석 →'** 클릭.
* **내레이션 (Voiceover)**:
  > "ChangeProof는 추측 대신 실제 재현을 선택했습니다. 실제 GitHub PR을 입력하면, 정적 분석기가 PR의 변경사항과 저장소 전체의 소스 트리를 즉시 분석합니다."

---

### [00:30 – 00:50] 결정론적 변경 팩트 & 의존성 증거 도출
* **화면**:
  * 화면 스크롤: **'구조화된 변경 팩트'** (`DROP_COLUMN orders.legacy_status`).
  * **'영향 범위 및 의존성 증거'** 카드 클로즈업: `app/order_service.py:11`에서 `return {'id': order.id, 'status': order.legacy_status}` 코드가 하이라이트된 장면. 배지: `직접 참조`, `이번 PR에서 변경되지 않음`.
* **내레이션 (Voiceover)**:
  > "보시다시피 마이그레이션 파일에서는 컬럼을 지웠지만, 이번 PR에서 수정되지 않은 `order_service.py` 11번째 줄에는 여전히 `legacy_status`를 직접 참조하는 코드가 남아있습니다. 정규표현식이 아닌 완벽한 결정론적 증거입니다."

---

### [00:50 – 01:05] 증거 기반 AI 추론: 안전한 실험 가설 수립
* **화면**:
  * **'증거 기반 AI 추론'** 카드 포커스.
  * 배지: `가설 • 제안됨 (PROPOSED)`, `스키마 계약 위반`.
  * 가설 제목: `legacy_status 컬럼 삭제 시 애플리케이션 런타임 장애 발생 가능`.
  * 제안된 실험 계획 6단계 목록 (`격리된 PostgreSQL 프로비저닝` $\rightarrow$ `기준 스키마 적용` $\rightarrow$ `마이그레이션` $\rightarrow$ `참조 쿼리 실행`).
* **내레이션 (Voiceover)**:
  > "OpenAI는 이 증거만을 바탕으로 구체적인 장애 메커니즘을 유추하고, 안전한 6단계 실험 계획을 세웁니다. 주목할 점은 AI가 안전 여부를 판정하지 않는다는 것입니다. 상태는 철저히 `UNVERIFIED`로 격리됩니다."

---

### [01:05 – 01:25] 격리된 PostgreSQL 실험 실행: PROVEN_FAIL 재현
* **화면**:
  * **'격리된 PostgreSQL에서 실험 실행 →'** 버튼 클릭.
  * 수초 내에 결과 렌더링:
    * 붉은색 배지: `재현 완료 • PROVEN FAIL`.
    * 5단계 실패: `단계 5: 조회 쿼리 실행 - 실패 (FAILED)`.
    * 구체적 에러 포착: `SQLSTATE: 42703 • column "legacy_status" does not exist`.
* **내레이션 (Voiceover)**:
  > "이제 버튼 한 번으로, 수초 내에 프로비저닝된 격리 PostgreSQL 샌드박스에서 변경사항을 직접 실행합니다. 보시는 것처럼 실제 PostgreSQL 엔진이 `SQLSTATE 42703 (undefined_column)` 오류를 뱉어내며, 장애가 배포 전에 100% 명백하게 재현되었습니다."

---

### [01:25 – 01:45] 동일 실험 기반 복구 검증: PROVEN_FIXED 완성
* **화면**:
  * 하단 **'호환성 복구 검증'** 카드.
  * **'복구 검증 →'** 버튼 클릭.
  * 녹색 배지: `PROVEN FIXED`.
  * Before (`PROVEN FAIL`, `42703`) vs After (`PROVEN PASS`).
  * 동일 실험 계약(`contract_...`) 일치 확인.
* **내레이션 (Voiceover)**:
  > "장애를 재현했다면 고칠 수 있어야 합니다. 호환성 복구 마이그레이션을 적용한 후, 완전히 동일한 실험 계약을 다시 실행하여 마침내 `PROVEN_FIXED`로 결함이 완벽히 해결되었음을 증명합니다."

---

### [01:45 – 02:00] 신뢰 아키텍처 요약 및 엔딩
* **화면**:
  * 핵심 신뢰 아키텍처 인포그래픽:
    * `DETERMINISTIC FACT` $\rightarrow$ `AI HYPOTHESIS` $\rightarrow$ `REAL POSTGRESQL` $\rightarrow$ `PROVEN VERDICT`
  * 로고 및 공식 슬로건 화면.
* **내레이션 (Voiceover)**:
  > "팩트는 결정론으로, 가설은 AI로, 판정은 실제 데이터베이스로 내립니다. 배포 전에 실패를 예측하지 마세요. 직접 재현하고 증명하세요. ChangeProof입니다."
