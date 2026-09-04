# ChangeProof — 본선 데모데이 발표 개요서 (Demo Day Outline)

* **대상 행사**: Wanted AI Championship 2026 본선 데모데이 (2026-10-17)
* **발표 시간**: 5분 발표 + 3분 질의응답 (총 8분 기준)
* **목표 청중**: 기술 심사위원단, 현업 엔지니어, 기술 리더

---

## 1. 발표 슬라이드 구성 및 스토리라인 (Slide Structure)

### Slide 1: 표지 및 문제 제기 (0:00 – 0:40)
* **타이틀**: ChangeProof: 배포 전에 실패를 예측하지 말고, 직접 재현하세요.
* **핵심 메시지**:
  * "가장 무서운 배포 장애는 diff에 보이지 않는 곳에서 일어납니다."
  * `ALTER TABLE orders DROP COLUMN legacy_status;`를 추가했을 때, 변경되지 않은 수십 개 파일 속의 `order.legacy_status` 참조는 diff 어디에도 없습니다.
  * 기존 해결책의 실패: 정적 분석은 오탐이 많고, 추측형 AI 리뷰어는 '위험 점수 85점' 같은 불안한 추측만 던집니다.

### Slide 2: 솔루션 — 실행형 변경 검증 에이전트 (0:40 – 1:20)
* **타이틀**: Don't Predict the Failure. Reproduce It Before Production.
* **차별점 다이어그램**:
  * 기존: PR 변경 $\rightarrow$ AI 추측 $\rightarrow$ 모호한 위험 점수 (불안감 증대)
  * ChangeProof: PR 변경 $\rightarrow$ 팩트와 증거 수집 $\rightarrow$ AI 가설 $\rightarrow$ **실제 격리된 DB 실행** $\rightarrow$ **명확한 증거(SQLSTATE 42703)** $\rightarrow$ **수정 증명(PROVEN_FIXED)**

### Slide 3: 라이브 데모 (1:20 – 2:40)
* **화면**: 실제 프로덕션 웹 화면 ([https://changeproof-web-production.up.railway.app](https://changeproof-web-production.up.railway.app))
* **3단계 시연 흐름**:
  1. **원클릭 분석**: '데모 PR 불러오기' $\rightarrow$ 마이그레이션 변경 팩트와 미변경 소스코드 의존성(`app/order_service.py:11`) 즉시 시각화.
  2. **격리된 DB 재현**: '격리된 PostgreSQL에서 실험 실행' 클릭 $\rightarrow$ 수초 내에 `SQLSTATE 42703` 발생 확인 및 `PROVEN_FAIL` 획득.
  3. **동일 실험 복구 증명**: '복구 검증' 클릭 $\rightarrow$ 동일한 실험 계약 하에서 기존 실패가 사라진 `PROVEN_PASS` 확인 및 해당 controlled experiment의 `PROVEN_FIXED` 도출.

### Slide 4: 신뢰 아키텍처 (2:40 – 3:30)
* **타이틀**: AI에게 판정을 맡기지 않는 AI 에이전트 아키텍처
* **4계층 구조 강조**:
  * `DETERMINISTIC FACT`: SQL AST 파서 & 소스코드 인덱서 (100% 결정론)
  * `AI HYPOTHESIS`: OpenAI Structured Outputs (가설 제안만, 임의 코드 실행 불가)
  * `REAL OBSERVATION`: Ephemeral PostgreSQL Sandbox (물리적 런타임 관측)
  * `DETERMINISTIC VERIFIER`: 계약 다이제스트 기반 판정 (인간이 신뢰할 수 있는 불변식)

### Slide 5: 비즈니스 임팩트 및 로드맵 (3:30 – 4:20)
* **타이틀**: 엔지니어링 신뢰성을 위한 차세대 인프라
* **MVP 검증 완료**: PostgreSQL, Python 앱, GitHub PR, 완전 배포, 백엔드 테스트 176개 및 커버리지 94.92%.
* **확장 로드맵**:
  * 1단계: MySQL, Prisma, SQLAlchemy 등 다중 DB 및 ORM 확장
  * 2단계: API 계약(OpenAPI/gRPC) 및 이벤트(Kafka/RabbitMQ) 스키마 검증 일반화
  * 3단계: GitHub App 기반 CI/CD 파이프라인 무인 자동화

### Slide 6: 결론 및 맺음말 (4:20 – 5:00)
* **요약 문장**: "추측에 의존하던 코드 리뷰를, 실험과 증거로 증명하는 시대로 전환합니다."
* **공식 웹 링크 및 QR 코드 노출**

---

## 2. 심사위원 주요 예상 질의 및 대응 (Q&A Defense)

* **Q1. 기존 정적 분석 도구나 SonarQube와 무엇이 다른가요?**
  * **A1**: 정적 분석 도구는 텍스트/AST 수준의 패턴 매칭만으로 실제 DB 엔진의 런타임 제약(마이그레이션 적용 순서, 시드 데이터 상태, 트랜잭션 락)을 모두 관찰할 수 없습니다. ChangeProof는 정적 분석으로 증거를 모은 뒤, 격리된 PostgreSQL 엔진에서 마이그레이션과 쿼리를 실행하여 특정 실험의 실제 오류(`SQLSTATE`)를 관측하고 결정론적으로 판정합니다.

* **Q2. AI(LLM)가 왜 꼭 필요한가요? 규칙 기반(Rule-based)으로도 되지 않나요?**
  * **A2**: 수많은 SQL 변경과 다양한 언어의 소스코드 간 결합을 규칙만으로 폭넓게 다루기 어렵기 때문에, LLM은 '이 변경과 증거가 결합할 때 어떤 런타임 증상이 가능한가'를 추론하고 allowlisted 실험 템플릿을 제안합니다. AI를 가설 제안자로 제한하고 사실·실행·판정을 결정론적 컴포넌트로 분리하여, 환각과 프롬프트 인젝션이 최종 verdict에 미치는 영향을 구조적으로 제한합니다.

* **Q3. 프로덕션 데이터베이스의 데이터를 그대로 복사해서 테스트하나요? 보안 문제는 없나요?**
  * **A3**: 아니오. ChangeProof는 실제 프로덕션 데이터를 복사하지 않습니다. PR 커밋의 마이그레이션과 리포지토리의 합성 시드(Seed) 데이터를 기반으로 격리된 임시 스키마(`cp_run_*`)를 즉시 생성하여 실험하고, 완료 즉시 파기합니다. 고객의 실제 고객 데이터(PII) 유출 위험이 원천적으로 없습니다.

> This proof applies to this controlled experiment, not to the entire pull request or production system.

```text
DETERMINISTIC ANALYSIS = FACT
OPENAI = HYPOTHESIS
POSTGRESQL = OBSERVATION
DETERMINISTIC VERIFIER = VERDICT

SAME EXPERIMENT
- CHANGED SUBJECT
- FAIL → PASS
= PROOF
```
