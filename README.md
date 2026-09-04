# ChangeProof

**사용자가 몰리기 전에, 병목을 먼저 재현하세요.**

ChangeProof는 코드 변경을 분석해 이번 릴리스에서 새로 검증해야 할 부하 위험을 AI가 제안하고, 개발 환경에서 실제 동시 요청을 실행해 운영 피크 시간에 나타날 수 있는 병목을 배포 전에 재현하는 AI 테스트 에이전트입니다.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Peak%20Load%20Proof-blue?style=for-the-badge&logo=railway)](https://changeproof-web-production.up.railway.app)
[![CI Status](https://img.shields.io/badge/CI-Passing-brightgreen?style=for-the-badge&logo=githubactions)](https://github.com/choi11000/ChangeProof/actions)
[![Coverage](https://img.shields.io/badge/Coverage-93.69%25-brightgreen?style=for-the-badge)](apps/api)

## 기능 테스트가 통과해도 운영에서는 실패할 수 있습니다

```text
Functional Test
PASS

↓

Peak Load
BOTTLENECK REPRODUCED

↓

Fix

↓

Same Load
RECOVERY VERIFIED
```

실제 서비스에서는 출근 시간, 이벤트 오픈, 예약 시작처럼 사용자가 한꺼번에 몰리는 순간 외부 API 응답 지연이나 제한된 connection capacity가 전체 서비스 지연으로 확대될 수 있습니다. 기존 부하 테스트 도구는 부하를 실행하지만, 이번 코드 변경 때문에 어떤 상황을 새로 검증해야 하는지는 개발자가 직접 판단해야 합니다.

ChangeProof는 그 판단부터 실제 검증까지 연결합니다.

## Live Demo

[프로덕션 데모 실행하기](https://changeproof-web-production.up.railway.app)

데모는 `GET /dashboard` 요청 경로에 새 외부 API 호출이 추가된 변경을 다룹니다.

1. 단일 기능 요청은 `HTTP 200 PASS`입니다.
2. 결정론적 분석이 `EXTERNAL_CALL_ADDED_TO_REQUEST_PATH` 변경 팩트를 추출합니다.
3. OpenAI가 `DOWNSTREAM_QUEUE_AMPLIFICATION` 가설과 시나리오 유형을 `PROPOSED / UNVERIFIED` 상태로 제안합니다.
4. 서버 소유의 통제된 fixture에서 동시 요청 150개, 총 300개 요청을 실제 실행합니다.
5. 대표 production 캡처에서는 candidate p95 `3001ms`, downstream queue wait `1401ms`가 관측되어 `PROVEN_BOTTLENECK`이 발행됐습니다.
6. 캐시와 중복 요청 병합을 적용한 subject에 같은 부하를 재실행합니다.
7. 같은 캡처에서 recovered p95 `1ms`, downstream queue wait `0ms`가 관측되어 `PROVEN_RECOVERED`가 발행됐습니다.

절대 처리량 수치는 server-owned in-process controlled runtime의 측정값이며 실제 production capacity를 뜻하지 않습니다. 제품의 주된 판단 근거는 p95 latency, downstream queue wait, 기능 테스트와 피크 부하의 대비, 동일 부하에서의 회복입니다.

> 이 결과는 해당 통제 부하 실험에서 확인된 병목과 복구에 적용되며, 실제 운영 환경 전체의 성능을 보장하지 않습니다.

## AI가 하는 일과 하지 않는 일

AI는 코드 변경에서 검증해야 할 병목 가설과 시나리오 유형을 제안합니다. 실제 부하 크기는 안전 경계가 적용된 deterministic compiler가 결정하고, 최종 판정은 실제 측정값을 기준으로 deterministic verifier가 수행합니다.

```text
DETERMINISTIC CHANGE ANALYSIS = FACT
OPENAI = HYPOTHESIS
CONTROLLED LOAD RUNNER = OBSERVATION
DETERMINISTIC VERIFIER = VERDICT

SAME LOAD
- SAME CONDITIONS
- CHANGED SUBJECT
- BOTTLENECK → RECOVERED
= PROOF
```

AI 출력은 항상 `PROPOSED / UNVERIFIED`로 시작합니다. AI는 verdict를 내리지 않으며 임의의 부하 스크립트, 셸 명령 또는 public target을 실행 경로에 넣을 수 없습니다.

## k6, JMeter와 무엇이 다른가요?

k6, JMeter, Gatling, Locust는 부하를 실행하는 훌륭한 도구입니다. ChangeProof가 해결하려는 질문은 한 단계 앞에 있습니다.

> 이번 코드 변경 때문에 어떤 부하 테스트를 새로 해야 하는가?

ChangeProof는 변경된 코드에서 새로운 runtime dependency를 찾고, AI가 검증할 성능 위험을 제안한 뒤, 그 위험에 맞는 bounded load experiment를 생성하고 실제로 실행합니다.

## ChatGPT에 코드를 보여주는 것과 무엇이 다른가요?

일반 AI는 병목 가능성을 설명할 수 있지만 그 답은 제안입니다. ChangeProof는 AI 가설을 실제 동시 요청 실험으로 연결하고, 실측 latency와 queue wait을 관측한 뒤, 수정 후 같은 조건을 다시 실행해 회복까지 확인합니다.

> The value is not the AI answer. The value is closing the loop from reasoning to execution.

## Local Runner

비공개 저장소와 내부 개발 환경을 사용하는 조직을 위해 `apps/runner`가 있습니다. 실사용 구조는 Web SaaS가 private source를 직접 실행하는 방식이 아니라, 기업 개발망 안의 Local Runner가 local Git diff를 분석하고 dev/test target에 bounded load를 실행하도록 설계됐습니다.

```bash
pip install -e apps/runner
changeproof inspect --repo . --base HEAD~1
changeproof verify --base HEAD~1 --target http://localhost:8001
changeproof verify --base HEAD~1 --target http://192.168.1.50:8001 --json
```

기본 target 정책은 `localhost`와 RFC1918 사설망 개발 환경만 허용합니다. 임의 public hostname과 public IP는 거부하며, 공개 데모는 server-owned controlled fixture만 사용합니다.

## 현재 범위

현재 MVP의 primary proof는 FastAPI 요청 경로에 새로 추가된 외부 HTTP dependency의 latency amplification을 end-to-end로 검증합니다. 모든 성능 장애를 탐지한다고 주장하지 않습니다.

Database schema와 API response contract 검증은 secondary compatibility capability로 유지됩니다. DB lock contention과 connection-pool pressure는 향후 확장 후보이며 현재 구현 범위가 아닙니다.

## 검증 상태

- Backend unit: 216 passed, 11 sandbox tests deselected, 93.69% coverage
- PostgreSQL integration: 11 passed
- Performance integration: 19 passed
- Local Runner: 8 passed
- Frontend: 5 passed
- GitHub Actions: 6 jobs green on production application RC `7807251bf46bd4b309871ac7c9993c2a6155dd10`

## Release identity

- Production application RC: `7807251bf46bd4b309871ac7c9993c2a6155dd10`
- Rollback RC: `a8fda49e880df1ec71fc0ba1d3fc1c8bcc2667ae`
- Release freeze: `ACTIVE`

This result applies to the bottleneck and recovery observed in this controlled load experiment and does not guarantee the performance of the entire production system.
