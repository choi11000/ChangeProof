# Wanted AI Championship 2026 — ChangeProof 제출 문서 (Single Source of Truth)

> **핵심 제품 슬로건**:  
> *"Don't predict the failure. Reproduce it before production. Fix it, run the same experiment again, and prove the result."*  
> (배포 전에 실패를 예측하지 말고, 직접 재현하세요. 수정 후 동일한 실험을 다시 실행해 증명하세요.)

---

## 1. 프로젝트 기본 정보

* **프로젝트명**: ChangeProof (체인지프루프)
* **카테고리**: 실행형 변경 검증 에이전트 (Executable Change Verification Agent / Evidence-to-Proof CI Safety System)
* **공개 웹 서비스**: [https://changeproof-web-production.up.railway.app](https://changeproof-web-production.up.railway.app)
* **공개 API 엔드포인트**: [https://changeproof-api-production.up.railway.app](https://changeproof-api-production.up.railway.app)
* **공개 GitHub 저장소**: [https://github.com/choi11000/ChangeProof](https://github.com/choi11000/ChangeProof)
* **공식 데모 저장소 (DB)**: [https://github.com/choi11000/changeproof-demo](https://github.com/choi11000/changeproof-demo)
* **공식 데모 풀 리퀘스트 (DB)**: [https://github.com/choi11000/changeproof-demo/pull/1](https://github.com/choi11000/changeproof-demo/pull/1)
* **공식 데모 저장소 (API)**: [https://github.com/choi11000/changeproof-api-demo](https://github.com/choi11000/changeproof-api-demo)
* **공식 데모 풀 리퀘스트 (API)**: [https://github.com/choi11000/changeproof-api-demo/pull/1](https://github.com/choi11000/changeproof-api-demo/pull/1)

---

## 2. 분량별 프로젝트 소개 카피 (Submission Copy)

### A. 한 줄 슬로건 (Tagline)
* **권장 기본형 (40자)**:
  > **배포 전에 실패를 예측하지 말고, 격리된 DB에서 직접 재현하세요.**
* **대안 후보 1 (51자)**:
  > **PR의 데이터베이스 위험을 점수로 추측하지 않고 실제 PostgreSQL에서 실패로 재현합니다.**
* **대안 후보 2 (34자)**:
  > **코드 리뷰의 추측을 실제 데이터베이스 증거로 증명합니다.**

### B. 매우 짧은 설명 (100–150자)
* **글자 수**: 142자 (공백 포함)
> ChangeProof는 GitHub PR의 PostgreSQL 스키마 변경 및 OpenAPI 응답 계약 변경과 미변경 소스코드 간의 숨은 의존성을 추적하고, 특정 변경으로 발생 가능한 런타임 실패를 격리된 샌드박스에서 직접 재현하여 관찰된 증거로 결정론적 verdict를 생성하는 실행형 검증 에이전트입니다.

### C. 짧은 설명 (250–400자)
* **글자 수**: 385자 (공백 포함)
> 현대의 코드 리뷰와 AI 리뷰어는 "무엇이 바뀌었는가"와 "위험해 보이는가"는 답하지만, "이 변경이 실제 의존 코드를 부러뜨리는가"는 증명하지 못합니다. 스키마와 API 계약 변경은 diff에 없는 미변경 코드와 결합할 때 치명적인 런타임 장애를 만듭니다. ChangeProof는 PR의 SQL 마이그레이션 및 OpenAPI 스펙과 앱 소스코드를 분석해 의존성 증거를 도출하고, AI로 구체적 장애 가설을 세운 뒤, 격리된 런타임에서 특정 실패(`SQLSTATE 42703`, `API_MISSING_RESPONSE_FIELD`)를 재현해 `PROVEN_FAIL`을 생성합니다. 호환성 복구 후 동일한 실험을 다시 실행해 관찰된 실패가 사라진 경우에만 `PROVEN_PASS`와 `PROVEN_FIXED`를 제공합니다.

### D. 전체 프로젝트 상세 소개 (800–1200자)
* **글자 수**: 1,074자 (공백 포함)
> 소프트웨어 배포 사고의 상당수는 데이터베이스 마이그레이션에서 발생합니다. 기존의 정적 분석 도구나 LLM 코드 리뷰어는 PR diff만을 검토하여 "위험 점수 85점"이나 "주의 필요" 같은 모호한 예측을 출력합니다. 하지만 개발자가 실제로 필요한 것은 점수가 아니라 "어떤 쿼리가, 어떤 SQL 오류로, 왜 실패하는가"에 대한 반박 불가능한 증거입니다. 특히 테이블 컬럼 삭제(`DROP COLUMN`)와 같이 스키마는 변경되었으나 앱 코드는 수정되지 않은 크로스 레이어 변경은 diff 중심의 리뷰에서 쉽게 누락됩니다.
>
> ChangeProof는 추측(Prediction) 대신 재현(Reproduction)을 선택했습니다.
>
> 1. **결정론적 팩트 수집**: GitHub PR의 SQL 마이그레이션을 AST 수준으로 파싱하고, 전체 앱 소스코드 트리를 인덱싱하여 변경되지 않은 채 남아있는 숨은 의존성 증거(`DependencyEvidence`)를 100% 결정론적으로 추출합니다.
> 2. **증거 기반 AI 가설 수립**: OpenAI Structured Outputs를 통해 검증된 증거만을 바탕으로 구체적인 장애 메커니즘과 안전한 실험 계획(Plan)을 가설(`UNVERIFIED`)로 제안합니다. AI는 판정을 내리지 않고 검증 가능한 실험 설계만을 담당합니다.
> 3. **격리된 PostgreSQL 실험 실행**: AI가 선택한 allowlisted 템플릿으로 결정론적 컴파일러가 실험 계획을 생성한 뒤, 격리된 PostgreSQL 샌드박스에서 기준 스키마 적용, 시드 데이터 적재, PR 마이그레이션 실행, 참조 쿼리 관측을 순차 수행합니다. 실제 데이터베이스 엔진이 반환한 `SQLSTATE 42703` (undefined_column)을 포착하고 결정론적 verifier가 증거 기반 판정(`PROVEN_FAIL`)을 내립니다.
> 4. **호환성 복구 및 동일 실험 증명**: 구버전 호환성을 유지하는 복구 마이그레이션을 적용한 후, 동일한 실험 계약(Contract Digest)을 재실행합니다. 같은 실험에서 기존 실패가 더 이상 재현되지 않을 때 `PROVEN_PASS`를 확인하고, 그 before/after 실험 쌍에 한해 `PROVEN_FIXED`를 결정론적으로 판정합니다.

### E. 해결하고자 하는 문제 (500–800자)
* **글자 수**: 634자 (공백 포함)
> 데이터베이스 스키마 변경은 소프트웨어 엔지니어링에서 가장 높은 장애 리스크를 지닙니다. 오늘날의 CI 파이프라인과 코드 리뷰는 치명적인 사각지대를 지니고 있습니다.
>
> 첫째, **Diff의 한계**: PR 리뷰는 변경된 파일만을 보여줍니다. `ALTER TABLE orders DROP COLUMN legacy_status;`라는 마이그레이션이 추가되었을 때, 변경되지 않고 방치된 `app/order_service.py`의 `order.legacy_status` 참조는 diff 어디에도 나타나지 않습니다.
>
> 둘째, **추측형 AI 리뷰의 신뢰성 결여**: 최근 유행하는 AI PR 요약기나 코드 리뷰어는 그럴듯한 텍스트로 위험성을 경고하거나 주관적인 리스크 점수를 매깁니다. 하지만 환각(Hallucination) 가능성 때문에 개발팀은 AI의 점수를 믿고 배포를 중단하거나 진행할 수 없습니다.
>
> 셋째, **실제 환경 테스트의 비용과 위험**: 프로덕션 DB와 동일한 상태에서 스키마 변경을 안전하게 사전 실행해 볼 수 있는 격리된 검증 인프라가 부재하여, 결국 staging이나 production 배포 순간에야 장애가 발견됩니다.
>
> ChangeProof는 이 사각지대를 해결하기 위해 "미변경 의존성 탐색"과 "격리된 데이터베이스 샌드박스 실행"을 결합하여, 배포 전 단계에서 장애를 직접 확인 가능한 사실로 전환합니다.

### F. AI 활용 방식 및 적절성 (500–800자)
* **글자 수**: 678자 (공백 포함)
> ChangeProof의 핵심 설계 원칙은 **"AI는 가설을 만들고, 증거가 판정을 내린다"**입니다. AI에게 안전 여부 판정이나 임의 코드 실행 권한을 위임하지 않고, 오직 인간 엔지니어처럼 가설적 사고가 필요한 영역에만 한정하여 엄격하게 활용합니다.
>
> * **결정론적 영역 (No AI)**: SQL 변경 사실 파싱, 앱 소스코드 의존성 매칭, 실험 샌드박스 프로비저닝, 쿼리 실행, 오류 코드 판정, 복구 전후 계약 검증은 모두 100% 결정론적 엔진이 처리합니다.
> * **AI 영역 (OpenAI Structured Outputs)**: 확정된 변경 팩트와 의존성 증거만을 컨텍스트로 전달받아, '이 변경이 런타임에 어떤 장애 증상으로 발현될 것인가'에 대한 가설(`FailureHypothesis`)과 사전 정의된 안전한 실험 템플릿(DROPPED_COLUMN_REFERENCE 등)을 매핑하는 역할만을 수행합니다.
> * **보안 및 환각 방지**: 저장소 소스코드는 프롬프트 인젝션 위험이 있는 비신뢰 데이터로 격리됩니다. AI 출력은 엄격한 JSON 스키마로 제한되며, AI가 임의의 SQL이나 셸 명령어를 생성할 수 없습니다. AI가 제안한 상태는 항상 `UNVERIFIED`로 표기되며, 실제 PostgreSQL에서 재현되기 전까지는 절대 결론으로 채택되지 않습니다.

### G. 기술적 구현 및 실현 가능성 (500–800자)
* **글자 수**: 712자 (공백 포함)
> ChangeProof는 아이디어 단계의 프로토타입이 아닌, 실제 배포되어 동작하는 완전한 풀스택 시스템입니다.
>
> 1. **SQL AST & 의존성 분석 엔진 (Python 3.13, sqlglot)**: 정규표현식이 아닌 SQL AST 파서를 통해 테이블/컬럼 변경을 구조화하고, PR 기준 커밋(`head_sha`)의 전체 소스 트리를 탐색하여 직접 참조와 테이블 컨텍스트 매칭을 정확히 분류합니다.
> 2. **AI 구조화 추론 계층 (OpenAI gpt-4o-mini)**: 시스템 프롬프트 인젝션 차단 샌드박싱과 Pydantic 기반 Structured Outputs를 적용하여 가설을 생성합니다. 인메모리 싱글플라이트(Single-flight) 락과 캐시를 통해 중복 LLM 호출 비용과 지연 시간을 최소화했습니다.
> 3. **격리된 PostgreSQL 샌드박스 실행기 (psycopg)**: 매 실험마다 고유한 임시 네임스페이스(`cp_run_<hex12>`)를 생성하고, 문장별 타임아웃(10초) 및 락 타임아웃(5초)을 적용하여 6단계 실험을 수행합니다. 실패 시 PostgreSQL 표준 오류 코드(`SQLSTATE 42703`)를 포착하며, `finally` 블록에서 스키마 cleanup을 수행하고 결과를 기록합니다.
> 4. **공개 배포 및 자동화된 품질 검증**: Railway HTTPS 환경에 Web(Next.js 16), API(FastAPI), Sandbox Postgres를 완전히 배포 완료했습니다. 176개의 백엔드 단위 테스트(커버리지 94.92%), 실제 PostgreSQL 기반 CI 통합 테스트, 프론트엔드 Vitest 및 Turbopack 빌드 테스트가 GitHub Actions에서 100% 통과하고 있습니다.

### H. 확장성 및 향후 계획 (400–700자)
* **글자 수**: 548자 (공백 포함)
> 현재 ChangeProof는 PostgreSQL SQL 마이그레이션과 Python 애플리케이션 소스코드, GitHub PR 분석을 지원하는 MVP를 완성했습니다. 본 아키텍처는 다음 영역으로 확장 가능하도록 모듈화되어 있습니다.
>
> 1. **다양한 DB 엔진 및 ORM 계약 확장**: MySQL, MariaDB, DynamoDB 등 이기종 데이터베이스와 Prisma, SQLAlchemy, TypeORM, Django ORM 등 코드 레벨 스키마 정의 분석으로 확장합니다.
> 2. **크로스 서비스 API & 이벤트 스키마 검증**: OpenAPI/gRPC 스펙 변경 및 Kafka/RabbitMQ 이벤트 메시지 스키마 변경 시, 소비(Consumer) 서비스 코드와의 호환성을 사전 검증하는 시스템으로 일반화합니다.
> 3. **CI/CD 플랫폼 및 GitHub App 완전 통합**: 개발자가 웹에 접속하지 않아도, PR 생성 시 GitHub Actions 또는 GitHub Check Runs로 자동 실행되어 코멘트에 재현 증거와 `SQLSTATE` 로그를 남기는 파이프라인으로 확장할 계획입니다.

---

## 3. 대중 투표용 카피 (Public Voting Copy)

### A. 대중 투표용 1줄 카피 (비전문가 눈높이)
> **"DB 컬럼 하나 지웠다가 서비스 장애 난 적 있으신가요? ChangeProof가 배포 전에 가상 DB에서 직접 터뜨려보고 막아드립니다."**

### B. 대중 투표용 2–3줄 설명
> 개발자가 코드를 고칠 때 데이터베이스 컬럼 이름을 바꾸거나 삭제하면, 다른 코드에서 이를 여전히 부르고 있어 서비스가 멈추는 대형 사고가 자주 일어납니다.  
> ChangeProof는 사람이 눈으로 찾기 어려운 숨은 코드 연결 고리를 찾아내고, 격리된 데이터베이스 샌드박스에서 특정 변경으로 예상되는 실패를 직접 재현합니다. 실제 SQLSTATE 관측과 동일 실험 재실행 결과를 확인하고 배포 판단에 활용하세요!

### C. 기술 심사위원용 핵심 요약
> ChangeProof는 Diff 중심 코드 리뷰의 사각지대인 크로스 레이어 스키마 변경 리스크를 해결하는 실행형 검증 시스템입니다. PR의 SQL 마이그레이션과 미변경 소스코드 간의 의존성을 정적 분석하고, OpenAI로 실험 가설을 수립한 뒤, 격리된 PostgreSQL 샌드박스에서 실제 마이그레이션과 쿼리를 실행해 `SQLSTATE 42703`을 재현(`PROVEN_FAIL`)합니다. 이어 호환성 복구를 적용해 동일 실험 통과(`PROVEN_PASS` $\rightarrow$ `PROVEN_FIXED`)까지 완결하는 Deterministic Proof 루프를 제공합니다.

---

## 4. 공시 의무 AI 도구 및 책임 분계선 (AI Tool Disclosure)

### 공식 공시 도구 목록
1. **OpenAI API (`gpt-4o-mini`)**:
   * **활용 목적**: 증거 기반 실패 가설 수립 및 실행 가능한 실험 템플릿 매핑
   * **활용 기능**: Structured Outputs (Pydantic 스키마 강제), 엄격한 안전 경계 시스템 프롬프트
   * **호출 위치**: `apps/api/app/clients/openai_client.py`, `apps/api/app/services/failure_planning_service.py`
2. **Google Antigravity**:
   * **활용 목적**: 시스템 아키텍처 설계 보조, FastAPI/Next.js 코드 구현, 단위/통합 테스트 코드 작성, CI 파이프라인 구성 및 문서화 지원

### 인간 vs AI 책임 분계선 (Human vs AI Responsibility)
* **AI의 역할**: 복잡한 의존성 관계 속에서 발생 가능한 런타임 장애의 메커니즘을 유추하고, 검증에 필요한 실험 템플릿을 신속하게 제안하는 보조적 분석가.
* **시스템/인간의 통제**: 
  * AI는 절대 안전성 여부(Pass/Fail)나 리스크 점수를 직접 결정하지 못합니다.
  * AI가 생성한 임의의 SQL이나 셸 스크립트는 샌드박스에서 실행되지 않습니다.
  * 실패 재현은 격리 PostgreSQL의 런타임 에러(`SQLSTATE`) 관측으로 확인하고, verdict는 결정론적 verifier가 발급합니다.
  * 최종 머지 및 배포 결정은 제공된 재현 증거를 확인한 엔지니어의 몫입니다.

---

## 5. 원티드 AI 챔피언십 심사 기준 매핑 (Evaluation Criteria Mapping)

| 평가 기준 | 배점 비중 | ChangeProof 구현 및 증빙 내용 |
| :--- | :--- | :--- |
| **기획력 / 문제 정의**<br>(Planning & Problem Definition) | 예선 80% / 본선 포함 | - **명확한 현업 페인포인트**: 기존 코드 리뷰의 "Diff 중심성"으로 인해 발생하는 스키마-코드 간 침묵의 런타임 장애 타겟팅.<br>- **시장 차별화**: 흔한 "AI 코드 리뷰어"나 "점수 예측기"를 거부하고 "실행형 검증 및 증거 재현 에이전트"라는 독창적 카테고리 개척.<br>- **구체적 타겟 고객**: 백엔드 엔지니어, 플랫폼/DBA 팀, DevOps/SRE 엔지니어. |
| **실현 가능성**<br>(Feasibility) | 예선 80% / 본선 포함 | - **완전한 상용 수준 배포**: 아이디어가 아닌 실제 동작하는 공개 HTTPS 서비스 (`https://changeproof-web-production.up.railway.app`) 운영 중.<br>- **실시간 E2E 동작 검증**: 공개 GitHub PR 분석 $\rightarrow$ OpenAI 실시간 추론 $\rightarrow$ 실제 PostgreSQL 격리 샌드박스 실행 $\rightarrow$ `SQLSTATE 42703` 재현 $\rightarrow$ 복구 검증 완결.<br>- **검증된 품질**: 백엔드 176개 테스트(커버리지 94.92%), PostgreSQL CI 통합 테스트, 프론트엔드 6개 테스트 전체 통과. |
| **확장성**<br>(Scalability) | 예선 80% / 본선 포함 | - **모듈형 설계**: 파서, 의존성 엔진, AI 플래너, 샌드박스 실행기가 독립 계층으로 분리되어 있어 MySQL, Oracle, MongoDB 등 타 엔진으로 손쉽게 플러그인 확장 가능.<br>- **엔터프라이즈 통합성**: GitHub App, GitLab CI, ArgoCD 등 현대 배포 자동화 도구와 연동 가능한 API First 아키텍처.<br>- **비용 및 리소스 제어**: LLM 컨텍스트 예산화, 싱글플라이트 락, 샌드박스 동시성 제한을 갖춘 프로덕션 지향 구조. |
| **AI 활용 적절성**<br>(Appropriateness of AI Usage) | 예선 80% / 본선 포함 | - **결정론과 AI의 엄격한 분리**: 팩트 수집과 판정에는 결정론 엔진을, 다차원 관계 해석과 가설 수립에는 LLM을 배치하는 최적의 역할 분담.<br>- **AI 영향 제한**: 소스코드를 비신뢰 데이터로 취급하고 Structured Outputs를 강제하며, AI 출력은 항상 `UNVERIFIED`로 격리.<br>- **신뢰 경계**: AI를 가설 제안자로 제한하고 사실·실행·판정을 결정론적 컴포넌트로 분리하여, 환각과 프롬프트 인젝션이 최종 verdict에 미치는 영향을 구조적으로 제한. |

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
