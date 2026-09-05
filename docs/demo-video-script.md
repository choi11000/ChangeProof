# ChangeProof — 100초 제품 시연 영상 스크립트 (Demo Video Script)

* **영상 목표 시간**: 약 1분 40초 (100초, 90~110초 범위)
* **해상도 및 형식**: 1080p 60fps / 한국어 음성 + 한국어 burn-in 자막
* **선택 자막**: 영문 SRT 별도 파일
* **배경 서비스**: [https://changeproof-web-production.up.railway.app](https://changeproof-web-production.up.railway.app)
* **핵심 슬로건**: *"트래픽이 몰리기 전에, 숨은 병목을 먼저 검증하세요."*
* **기준 RC**: `7807251bf46bd4b309871ac7c9993c2a6155dd10`

---

## 타임라인 및 화면 구성 (Timeline & Visual Storyboard)

### [00:00 – 00:08] 1. 문제 제기: 기능 테스트의 맹점
* **화면**:
  * 실제 production Hero와 `Functional PASS → Peak Load → Same Load Recovery` 흐름.
* **내레이션 (Voiceover)**:
  > "기능 테스트가 통과했다고 실제 서비스도 안전한 것은 아닙니다. 사용자가 한꺼번에 몰리는 순간, 평소 보이지 않던 병목이 나타날 수 있습니다."

---

### [00:08 – 00:20] 2. 코드 변경 팩트: 숨겨진 외부 의존성
* **화면**:
  * Git Diff 화면 포커스: `GET /dashboard` 엔드포인트에 `weather_client.get_current()` 호출이 새로 추가된 코드.
  * ChangeProof 메인 화면 진입 (`https://changeproof-web-production.up.railway.app`).
  * 변경 팩트 카드: `EXTERNAL_CALL_ADDED_TO_REQUEST_PATH`.
* **내레이션 (Voiceover)**:
  > "대시보드에 날씨 정보를 보여주기 위해 외부 API 호출을 추가했습니다. 개발 환경에서 단 한 번 호출할 때는 아무런 문제가 보이지 않습니다."

---

### [00:20 – 00:32] 3. AI 부하 가설 수립: 시나리오 제안
* **화면**:
  * '증거 기반 AI 부하 가설' 카드 포커스.
  * 상태 배지: `PROPOSED / UNVERIFIED`.
  * 가설 문구: *"사용자가 몰릴 경우 외부 API 응답을 기다리는 요청이 쌓여 대기열이 급증할 수 있습니다."*
* **내레이션 (Voiceover)**:
  > "k6나 JMeter는 부하를 실행하지만, '이번 변경 때문에 어떤 부하 테스트를 해야 하는가'는 알려주지 못합니다. ChangeProof의 AI는 코드 변경 사실을 바탕으로 병목 가설과 시나리오를 제안합니다."

---

### [00:32 – 00:55] 4. 기능 통과 & 피크 부하 실행 $\rightarrow$ 병목 재현
* **화면**:
  * **'피크 장애 데모 실행'** 원클릭.
  * STEP 1: 기능 테스트 `HTTP 200 PASS` ("한 명이 사용하면 정상입니다.")
  * STEP 4: *"피크 부하 실험 실행 중..."* 프로그레스 링.
  * STEP 5: 붉은색 결과 카드 점등: `병목 재현됨` (`PROVEN_BOTTLENECK`).
* **내레이션 (Voiceover)**:
  > "한 명이 사용할 때 기능 요청은 통과합니다. 하지만 동시 요청 150건의 피크 부하를 적용하면 숨어 있던 병목이 드러나고, 실측값을 기준으로 `PROVEN_BOTTLENECK`이 발행됩니다."

---

### [00:55 – 01:15] 5. 실측 지표 분석: 다운스트림 큐 증폭
* **화면**:
  * 실측 런타임 지표 테이블 클로즈업:
    * 대표 production 실행의 candidate p95: 약 3,000ms
    * 다운스트림 대기시간: 약 1,400ms 발생
  * 관측 코드: `DOWNSTREAM_QUEUE_AMPLIFICATION`.
* **내레이션 (Voiceover)**:
  > "추측이 아닌 실제 측정값입니다. 대표 실행에서 candidate p95 지연시간이 약 3,000ms까지 증가했고, 외부 API 응답을 기다리는 대기열이 약 1.4초 형성됐습니다."

---

### [01:15 – 01:32] 6. 호환성 복구 & 동일 부하 재실행
* **화면**:
  * 복구 전략 안내: 짧은 캐시 + 중복 호출 병합(singleflight) + 타임아웃.
  * **'동일 부하 다시 실행'** 버튼 클릭.
  * 배지 확인: `SAME LOAD`, `SAME CONDITIONS`, `CHANGED SUBJECT`.
* **내레이션 (Voiceover)**:
  > "외부 호출을 캐싱하고 중복 요청을 병합하는 복구 코드를 적용합니다. 그리고 완전히 동일한 부하 조건으로 다시 실행합니다."

---

### [01:32 – 01:45] 7. 복구 증명 완료 (PROVEN_RECOVERED) & 클로징
* **화면**:
  * 초록색 결과 카드 점등: `복구 검증 완료` (`PROVEN_RECOVERED`).
  * 복구 후 핵심 지표: p95 1ms, 큐 대기시간 0ms.
  * 하단 유효 범위 고지문 하이라이트.
  * 최종 슬로건 타이틀 카드.
* **내레이션 (Voiceover)**:
  > "동일 부하에서 p95 지연시간과 큐 대기가 회복되어 `PROVEN_RECOVERED`가 발행됐습니다. 이 결과는 해당 통제 부하 실험에만 적용됩니다. 트래픽이 몰리기 전에, 숨은 병목을 먼저 검증하세요. ChangeProof입니다."

---

## 편집 불변식

- 실제 production 화면만 사용하고 가짜 CI, 모니터링 경고 또는 실행 결과를 합성하지 않습니다.
- `PROPOSED`, `UNVERIFIED`, `PROVEN_BOTTLENECK`, `PROVEN_RECOVERED`, `DOWNSTREAM_QUEUE_AMPLIFICATION`, `p95`는 영문 기술 토큰으로 유지합니다.
- 절대 처리량을 성공 훅으로 사용하지 않습니다. 화면에 보일 경우 `Controlled runtime throughput`으로만 설명합니다.
- Korean burn-in subtitle을 기본으로 하고 English subtitle은 별도 SRT로 제공합니다.
- 마지막 화면에 다음 범위를 유지합니다: "이 결과는 해당 통제 부하 실험에서 확인된 병목과 복구에 적용되며, 실제 운영 환경 전체의 성능을 보장하지 않습니다."
