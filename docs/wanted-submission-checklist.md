# Wanted AI Championship 2026 — 제출 체크리스트 (Submission Checklist)

본 문서는 원티드 AI 챔피언십 2026 예선 접수 및 심사 대비 전 과정의 확인 상태를 관리하는 체크리스트입니다.

---

## 1. 대회 핵심 일정 (Official Schedule)

* **참가자 등록 마감**: 2026-09-18 23:59:59 KST
* **프로젝트 제출 마감**: 2026-09-20 23:59:59 KST
* **예선 심사 및 대중 투표**: 2026-09-21 ~ 2026-10-05 (내부 심사 80% + 대중 투표 20%)
* **TOP20 결과 발표**: 2026-10-07
* **본선 데모데이**: 2026-10-17

---

## 2. 제출 패키지 체크리스트

### A. 기본 정보 및 엔드포인트
- [x] 프로젝트명 확정: `ChangeProof`
- [x] 공식 슬로건 확정: *"Don't predict the failure. Reproduce it before production."*
- [x] 공개 웹 서비스 HTTPS 접속 정상: `https://changeproof-web-production.up.railway.app`
- [x] 공개 API 헬스체크 정상: `https://changeproof-api-production.up.railway.app/api/v1/health`
- [x] 공개 GitHub 메인 저장소 공개 상태: `https://github.com/choi11000/ChangeProof`
- [x] 공식 데모 저장소 및 PR OPEN 상태 유지: `https://github.com/choi11000/changeproof-demo/pull/1`

### B. 제출 양식 텍스트 준비 (`docs/wanted-submission.md`)
- [x] 한 줄 슬로건 (40자) 준비 완료
- [x] 매우 짧은 설명 (138자) 준비 완료
- [x] 짧은 설명 (352자) 준비 완료
- [x] 전체 상세 소개 (1,074자) 준비 완료
- [x] 해결하고자 하는 문제 정의 (634자) 준비 완료
- [x] AI 활용 방식 및 적절성 (678자) 준비 완료
- [x] 기술적 구현 및 실현 가능성 (712자) 준비 완료
- [x] 확장성 및 향후 계획 (548자) 준비 완료
- [x] 대중 투표용 눈높이 카피 및 설명 준비 완료

### C. 공시 및 보안 가드레일
- [x] 사용 AI 도구 공시 완료: OpenAI API (`gpt-4o-mini`, Structured Outputs), AI 코딩 도구
- [x] 인간 vs AI 책임 분계선 명시: AI는 판정하지 않고 가설만 제안, 검증은 실제 DB 엔진 담당
- [x] 직장/기업/고객사 기밀 데이터 및 실데이터 전무 확인 (100% 합성 데이터)
- [x] Git 커밋 히스토리에 OpenAI API Key 미존재 확인
- [x] Git 커밋 히스토리에 Railway 토큰/DB 비밀번호 미존재 확인
- [x] 로컬 `.env` 파일 gitignore 철저 적용 확인
- [x] 프로덕션 PostgreSQL 포트 외부 노출 없음 (Railway 내부 전용 프라이빗 메쉬망)

### D. 시연 및 평가 에셋
- [x] 90~150초 시연 영상 스크립트 작성 완료 (`docs/demo-video-script.md`)
- [x] 아키텍처 다이어그램 문서 작성 완료 (`docs/architecture-submission.md`)
- [x] 기술 신뢰성 입증 시트 작성 완료 (`docs/technical-proof.md`)
- [x] TOP20 본선 데모데이 발표 개요서 작성 완료 (`docs/demo-day-outline.md`)
- [x] 저장소 `README.md` 심사위원 맞춤형 개선 완료
- [x] 대표 시연 스크린샷 캡처 및 검증 완료 (`docs/assets/submission/`)

### E. 라이브 런타임 수용성 검증
- [x] 비로그인(시크릿 모드) 상태에서 웹 접속 100% 동작
- [x] "데모 PR 불러오기" 클릭 시 즉시 폼 자동 채움 작동
- [x] "변경사항 분석 →" 클릭 시 실시간 OpenAI 가설 및 실험 계획 렌더링
- [x] "격리된 PostgreSQL에서 실험 실행 →" 클릭 시 `SQLSTATE 42703` 및 `PROVEN_FAIL` 재현
- [x] "복구 검증 →" 클릭 시 동일 실험 계약에 대해 `PROVEN_PASS` 및 `PROVEN_FIXED` 증명
- [x] 상단 언어 전환기(`한국어` | `English`) 클릭 시 UI 및 AI 추론 내용 실시간 전환

### F. 최종 제출 상태 (Final Submission Gate)
- [x] 제출 패키지 준비 완료 (PACKAGE READY)
- [ ] 원티드 공식 접수 페이지 임시 저장 (Draft Save)
- [ ] 원티드 공식 접수 페이지 최종 제출 버튼 클릭 (FINAL SUBMITTED)

> [!WARNING]
> **임시 저장은 최종 제출이 아닙니다.** 접수 마감 시각(2026-09-20 23:59:59 KST) 이전에 참가자가 직접 원티드 제출 화면에서 최종 제출(Submit)을 완료해야 합니다.
