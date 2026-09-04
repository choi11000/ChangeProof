"use client";

import React, { createContext, useContext, useState } from "react";

export type Language = "ko" | "en";

export interface Translations {
  // Nav
  brand: string;
  langKo: string;
  langEn: string;

  // Hero
  heroEyebrow: string;
  heroTitle1: string;
  heroTitle2: string;
  heroLede: string;
  heroSublede: string;
  flowStep1: string;
  flowStep2: string;
  flowStep3: string;
  flowStep4: string;
  flowAriaLabel: string;
  pipelineAriaLabel: string;
  stages: string[];
  runPerfDemoBtn: string;
  howItWorksBtn: string;

  // Tabs
  tabPeakLoadTitle: string;
  tabCompatibilityTitle: string;
  tabLocalRunnerTitle: string;

  // Performance Demo
  perfDemoTitle: string;
  perfDemoSubtitle: string;
  runPeakLoadBtn: string;
  runningPeakLoadBtn: string;
  applyFixBtn: string;
  applyingFixBtn: string;
  runSameLoadBtn: string;
  baselineCardTitle: string;
  candidateCardTitle: string;
  remediatedCardTitle: string;
  metricConcurrency: string;
  metricRequests: string;
  metricP50: string;
  metricP95: string;
  metricP99: string;
  metricThroughput: string;
  metricTimeouts: string;
  metricDownstreamWait: string;
  badgeSameLoad: string;
  badgeSameConditions: string;
  badgeChangedSubject: string;
  verdictBottleneck: string;
  verdictRecovered: string;
  verdictHealthy: string;

  // Principles
  principleEyebrow: string;
  principleTitle1: string;
  principleTitle2: string;
  capabilityLabel: string;
  capabilityTitle: string;
  capabilityDesc: string;

  // Analysis Form
  repoLabel: string;
  repoPlaceholder: string;
  prLabel: string;
  prPlaceholder: string;
  analyzeBtn: string;
  analyzingBtn: string;
  loadDemoBtn: string;
  demoHint: string;
  demoScenario: string;
  databaseDemoTabTitle: string;
  databaseDemoTabDesc: string;
  apiDemoTabTitle: string;
  apiDemoTabDesc: string;
  apiDemoHint: string;
  apiDemoScenario: string;
  perfDemoHint: string;
  perfDemoScenario: string;
  domainDatabase: string;
  domainApi: string;
  domainPerformance: string;
  orDivider: string;
  manualAnalysisLabel: string;

  // Proof Summary
  proofSummaryEyebrow: string;
  proofSummaryHeading: string;
  summaryChangeLabel: string;
  summaryChangePending: string;
  summaryDependencyLabel: string;
  summaryDependencyFound: string;
  summaryDependencyPending: string;
  summaryObservationLabel: string;
  summaryObservationApiLabel: string;
  summaryObservationPending: string;
  summaryVerdictLabel: string;
  summaryVerdictPending: string;
  scopeInvariant: string;
  deterministicDetails: string;
  hypothesisDetails: string;
  experimentDetails: string;

  // Change Facts
  changeFactsEyebrow: string;
  changedFiles: string;
  sqlMigrations: string;
  appFiles: string;
  dbChanges: string;

  // Impact Surface
  impactEyebrow: string;
  impactHeading: string;
  impactIncomplete: string;
  targetEntities: string;
  appFilesAffected: string;
  directReferences: string;
  potentialReferences: string;

  // Dependency Evidence
  evidenceEyebrow: string;
  evidenceHeading: string;
  badgeChangedInPr: string;
  badgeNotChangedInPr: string;
  matchDirect: string;
  matchContext: string;
  matchColId: string;
  matchTableId: string;
  noEvidenceComplete: string;
  noEvidenceIncomplete: string;

  // Failure Hypotheses & Plans
  hypothesesEyebrow: string;
  hypothesesHeading: string;
  unverifiedProposal: string;
  hypothesisBadge: string;
  rationaleLabel: string;
  expectedFailureLabel: string;
  proposedExperimentBadge: string;
  templateLabel: string;
  executedInSandbox: string;
  notExecutedYet: string;
  expectedObservationLabel: string;
  runExperimentBtn: string;
  runningExperimentBtn: string;
  sandboxNoticeDefault: string;
  noHypothesisGenerated: string;

  // Observed Result
  reproducedFailBadge: string;
  notReproducedPassBadge: string;
  reproducedFailHeadline: string;
  notReproducedPassHeadline: string;
  inconclusiveHeadline: string;
  passSubnote: string;
  stepLabel: string;
  experimentContractLabel: string;
  subjectLabel: string;
  cleanupLabel: string;
  cleanupSucceeded: string;
  cleanupFailed: string;
  cleanupUnknown: string;

  // Remediation
  remediationEyebrow: string;
  noRemediationNeeded: string;
  remediationHeading: string;
  remediationDesc: string;
  verifyRemediationBtn: string;
  verifyingRemediationBtn: string;
  remediationRequiresFailure: string;
  beforeLabel: string;
  sameExperimentLabel: string;
  contractLabel: string;
  afterLabel: string;
  invariantSameExp: string;
  invariantSubjectChanged: string;
  yes: string;
  no: string;
}

export const translations: Record<Language, Translations> = {
  ko: {
    // Nav
    brand: "ChangeProof",
    langKo: "한국어",
    langEn: "English",

    // Hero
    heroEyebrow: "운영 피크 장애 선제 검증 에이전트",
    heroTitle1: "사용자가 몰리기 전에,",
    heroTitle2: "병목을 먼저 재현하세요.",
    heroLede:
      "ChangeProof는 코드 변경을 분석해 운영 피크 시간에 발생할 수 있는 부하 시나리오를 AI가 만들고, 개발 환경에서 실제 부하를 실행해 장애를 배포 전에 재현합니다.",
    heroSublede: "개발계에서는 멀쩡한데 운영 피크에서만 터지는 장애를 배포 전에 선제 검증합니다.",
    flowStep1: "기능 테스트 통과 (단일 요청 정상)",
    flowStep2: "AI 위험 분석 (외부 의존성 감지)",
    flowStep3: "피크 트래픽 재현 (병목 검증)",
    flowStep4: "동일 부하 회복 검증 (수정 후 재실행)",
    flowAriaLabel: "4단계 부하 증명 흐름",
    pipelineAriaLabel: "부하 검증 파이프라인",
    stages: ["코드 변경", "위험 팩트", "AI 시나리오", "동시 부하 실행", "병목 재현", "회복 검증"],
    runPerfDemoBtn: "피크 장애 데모 실행",
    howItWorksBtn: "작동 원리",

    // Tabs
    tabPeakLoadTitle: "피크 부하 장애 검증",
    tabCompatibilityTitle: "호환성 검증 (DB / API)",
    tabLocalRunnerTitle: "로컬 러너 (Local Runner)",

    // Performance Demo
    perfDemoTitle: "ShiftSafe 피크 트래픽 병목 재현 데모",
    perfDemoSubtitle: "GET /dashboard 핫 경로에 동기 외부 API(날씨) 호출이 추가된 위험 변경 시나리오",
    runPeakLoadBtn: "피크 트래픽 재현 실행 (150 동시 요청) →",
    runningPeakLoadBtn: "동시 부하 실행 및 지연 시간 측정 중...",
    applyFixBtn: "수정 적용 및 동일 부하 재실행 →",
    applyingFixBtn: "동일 부하 조건에서 수정본 재검증 중...",
    runSameLoadBtn: "동일한 부하 다시 실행",
    baselineCardTitle: "변경 전 (Baseline)",
    candidateCardTitle: "위험 변경 (Candidate)",
    remediatedCardTitle: "수정 적용 (Remediated)",
    metricConcurrency: "동시 요청 수",
    metricRequests: "총 요청 수",
    metricP50: "p50 지연 시간",
    metricP95: "p95 지연 시간",
    metricP99: "p99 지연 시간",
    metricThroughput: "초당 처리량 (RPS)",
    metricTimeouts: "타임아웃 발생률",
    metricDownstreamWait: "외부 의존성 대기열",
    badgeSameLoad: "SAME LOAD (동일 부하)",
    badgeSameConditions: "SAME CONDITIONS (동일 조건)",
    badgeChangedSubject: "CHANGED SUBJECT (수정 적용)",
    verdictBottleneck: "병목 재현됨 (PROVEN_BOTTLENECK)",
    verdictRecovered: "복구 검증 완료 (PROVEN_RECOVERED)",
    verdictHealthy: "정상 (HEALTHY)",

    // Principles
    principleEyebrow: "신뢰 모델 (TECHNICAL TRUST MODEL)",
    principleTitle1: "추측이 아닌 실제 동시 부하로,",
    principleTitle2: "배포 전 병목을 증명합니다.",
    capabilityLabel: "핵심 차별점",
    capabilityTitle: "코드 변경 기반 타깃 부하 테스트",
    capabilityDesc:
      "일반적인 성능 모니터링이나 부하 툴과 달리, ChangeProof는 이번 변경으로 인해 발생할 수 있는 특정 병목 시나리오를 식별하고 정밀 검증합니다.",

    // Analysis Form
    repoLabel: "GitHub 저장소",
    repoPlaceholder: "https://github.com/acme/risky-saas",
    prLabel: "풀 리퀘스트 번호",
    prPlaceholder: "42",
    analyzeBtn: "변경사항 분석",
    analyzingBtn: "분석 중…",
    loadDemoBtn: "피크 부하 데모 실행하기",
    demoHint: "운영 피크 병목 재현 데모를 직접 실행해 보세요",
    demoScenario: "ShiftSafe 데모: GET /dashboard + 외부 날씨 API 대기열 증폭",
    databaseDemoTabTitle: "데이터베이스 스키마",
    databaseDemoTabDesc: "DROP COLUMN → PostgreSQL (42703)",
    apiDemoTabTitle: "API 계약 (OpenAPI)",
    apiDemoTabDesc: "REMOVE_RESPONSE_FIELD → ASGI",
    apiDemoHint: "API 계약 파괴적 변경 데모를 실행해 보세요",
    apiDemoScenario: "GET /users/{id} 응답 'email' 필드 제거 → 소비자 직접 참조 실패",
    perfDemoHint: "운영 피크 병목 재현 데모를 직접 실행해 보세요",
    perfDemoScenario: "GET /dashboard + 외부 API 추가 → 150 동시 요청 시 4.8초 지연 폭발",
    domainDatabase: "데이터베이스",
    domainApi: "API 계약",
    domainPerformance: "피크 부하 장애",
    orDivider: "또는",
    manualAnalysisLabel: "GitHub 저장소와 PR을 직접 분석",

    // Proof Summary
    proofSummaryEyebrow: "PROOF SUMMARY",
    proofSummaryHeading: "이 실험에서 확인된 결론",
    summaryChangeLabel: "PR 변경",
    summaryChangePending: "구조화된 변경 팩트",
    summaryDependencyLabel: "미변경 의존성",
    summaryDependencyFound: "숨은 애플리케이션 참조 발견",
    summaryDependencyPending: "참조 증거 없음",
    summaryObservationLabel: "PostgreSQL 관측",
    summaryObservationApiLabel: "API 런타임 관측",
    summaryObservationPending: "격리 실험 실행 대기",
    summaryVerdictLabel: "결정론적 판정",
    summaryVerdictPending: "PENDING",
    scopeInvariant:
      "이 증명은 해당 통제 실험에만 적용되며, 전체 PR이나 프로덕션 시스템의 안전성을 의미하지 않습니다.",
    deterministicDetails: "결정론적 팩트와 의존성 증거",
    hypothesisDetails: "AI 가설과 실행 계획",
    experimentDetails: "실험 단계 보기",

    // Change Facts
    changeFactsEyebrow: "구조화된 변경 팩트",
    changedFiles: "변경된 파일",
    sqlMigrations: "SQL 마이그레이션",
    appFiles: "애플리케이션 파일",
    dbChanges: "DB 변경 항목",

    // Impact Surface
    impactEyebrow: "영향 범위 (Impact Surface)",
    impactHeading: "크로스 레이어 애플리케이션 참조",
    impactIncomplete: "제한적 스캔 (불완전)",
    targetEntities: "대상 엔터티",
    appFilesAffected: "영향받는 앱 파일",
    directReferences: "직접 참조",
    potentialReferences: "잠재적 참조",

    // Dependency Evidence
    evidenceEyebrow: "의존성 증거",
    evidenceHeading: "결정론적 소스 코드 매칭",
    badgeChangedInPr: "이번 PR에서 변경됨",
    badgeNotChangedInPr: "이번 PR에서 변경되지 않음",
    matchDirect: "직접 참조",
    matchContext: "테이블 + 컬럼 컨텍스트",
    matchColId: "컬럼 식별자",
    matchTableId: "테이블 식별자",
    noEvidenceComplete: "스캔된 애플리케이션 파일에서 소스 참조를 찾지 못했습니다.",
    noEvidenceIncomplete: "스캔된 하위 집합에서 참조를 찾지 못했습니다. 소스 분석이 제한되었습니다.",

    // Failure Hypotheses & Plans
    hypothesesEyebrow: "장애 가설 및 실험 계획",
    hypothesesHeading: "증거 기반 AI 추론",
    unverifiedProposal: "미검증 제안",
    hypothesisBadge: "가설 •",
    rationaleLabel: "근거:",
    expectedFailureLabel: "예상 장애:",
    proposedExperimentBadge: "제안된 실험 •",
    templateLabel: "템플릿:",
    executedInSandbox: "샌드박스에서 실행 완료",
    notExecutedYet: "아직 실행되지 않음",
    expectedObservationLabel: "예상 관측 결과:",
    runExperimentBtn: "격리된 PostgreSQL에서 실험 실행 →",
    runningExperimentBtn: "PostgreSQL에서 장애 재현 중...",
    sandboxNoticeDefault: "샌드박스 실행은 이번 MVP에서 제어된 데모 픽스처로 제한됩니다.",
    noHypothesisGenerated: "이 변경사항에 대해 생성된 증거 기반 장애 가설이 없습니다.",

    // Observed Result
    reproducedFailBadge: "재현 완료 • PROVEN FAIL",
    notReproducedPassBadge: "미재현 • PROVEN PASS",
    reproducedFailHeadline: "격리된 PostgreSQL에서 장애가 재현되었습니다.",
    notReproducedPassHeadline: "이 실험은 예상된 장애 없이 완료되었습니다.",
    inconclusiveHeadline: "결정적이지 않은 관측 결과로 실험이 완료되었습니다.",
    passSubnote: "이 판정은 전체 풀 리퀘스트가 아닌 이 실험에만 적용됩니다.",
    stepLabel: "단계",
    experimentContractLabel: "실험 계약:",
    subjectLabel: "대상:",
    cleanupLabel: "정리 상태:",
    cleanupSucceeded: "성공",
    cleanupFailed: "실패",
    cleanupUnknown: "알 수 없음",

    // Remediation
    remediationEyebrow: "복구 (Remediation)",
    noRemediationNeeded: "이 실험에는 복구가 필요하지 않습니다.",
    remediationHeading: "결정론적 호환성 복구",
    remediationDesc: "이 검증된 복구책은 동일한 실험 계약을 통해 검증됩니다.",
    verifyRemediationBtn: "복구 검증 →",
    verifyingRemediationBtn: "신뢰할 수 있는 전후 비교 실험 실행 중...",
    remediationRequiresFailure: "복구 검증은 장애가 확실히 재현된 경우에만 가능합니다.",
    beforeLabel: "복구 전 (Before)",
    sameExperimentLabel: "동일한 실험 (Same experiment)",
    contractLabel: "계약:",
    afterLabel: "복구 후 (After)",
    invariantSameExp: "동일 실험:",
    invariantSubjectChanged: "대상 변경:",
    yes: "예",
    no: "아니오",
  },
  en: {
    // Nav
    brand: "ChangeProof",
    langKo: "한국어",
    langEn: "English",

    // Hero
    heroEyebrow: "CHANGE-AWARE LOAD FAILURE PROOF",
    heroTitle1: "Reproduce the bottleneck",
    heroTitle2: "before peak traffic does.",
    heroLede:
      "ChangeProof analyzes code changes, generates targeted peak-load experiments, and reproduces production bottlenecks in dev before deployment.",
    heroSublede: "Detect performance regressions that pass functional tests but explode under concurrent traffic.",
    flowStep1: "Functional Test PASS (Single Request OK)",
    flowStep2: "AI Risk Scenario (Hot Path Dependency)",
    flowStep3: "Reproduce Peak Load (Bottleneck Proven)",
    flowStep4: "Same-Load Recovery (Pass Verified)",
    flowAriaLabel: "Four-step load proof flow",
    pipelineAriaLabel: "Verification pipeline",
    stages: ["Code Change", "Risk Facts", "AI Scenario", "Concurrent Load", "Bottleneck Proven", "Recovery Verified"],
    runPerfDemoBtn: "Run Peak Load Demo",
    howItWorksBtn: "How It Works",

    // Tabs
    tabPeakLoadTitle: "Peak Load Proof",
    tabCompatibilityTitle: "Compatibility Proofs (DB / API)",
    tabLocalRunnerTitle: "Local Runner",

    // Performance Demo
    perfDemoTitle: "ShiftSafe Peak Traffic Bottleneck Demo",
    perfDemoSubtitle: "Risky change: Synchronous weather client call added to GET /dashboard hot request path",
    runPeakLoadBtn: "Reproduce Peak Load (150 Concurrent Users) →",
    runningPeakLoadBtn: "Generating concurrent load and tracking latency...",
    applyFixBtn: "Apply Fix & Run Same Load →",
    applyingFixBtn: "Re-verifying fix under identical load...",
    runSameLoadBtn: "Run Same Load Again",
    baselineCardTitle: "Before Change (Baseline)",
    candidateCardTitle: "Risky Change (Candidate)",
    remediatedCardTitle: "Remediated (Fixed)",
    metricConcurrency: "Concurrency",
    metricRequests: "Total Requests",
    metricP50: "p50 Latency",
    metricP95: "p95 Latency",
    metricP99: "p99 Latency",
    metricThroughput: "Throughput (RPS)",
    metricTimeouts: "Timeout Rate",
    metricDownstreamWait: "Downstream Wait",
    badgeSameLoad: "SAME LOAD",
    badgeSameConditions: "SAME CONDITIONS",
    badgeChangedSubject: "CHANGED SUBJECT",
    verdictBottleneck: "PROVEN_BOTTLENECK",
    verdictRecovered: "PROVEN_RECOVERED",
    verdictHealthy: "HEALTHY",

    // Principles
    principleEyebrow: "TECHNICAL TRUST MODEL",
    principleTitle1: "Deterministic verification under real load.",
    principleTitle2: "Evidence earns the verdict.",
    capabilityLabel: "CORE DIFFERENTIATOR",
    capabilityTitle: "Change-aware load verification agent",
    capabilityDesc:
      "Unlike generic APMs or load generators, ChangeProof detects WHAT CHANGED and compiles targeted concurrent load experiments to prove or disprove regressions.",

    // Analysis Form
    repoLabel: "GitHub repository",
    repoPlaceholder: "https://github.com/acme/risky-saas",
    prLabel: "Pull request",
    prPlaceholder: "42",
    analyzeBtn: "Analyze change",
    analyzingBtn: "Analyzing…",
    loadDemoBtn: "Run Peak Load Demo",
    demoHint: "Try the production peak bottleneck reproduction demo",
    demoScenario: "ShiftSafe demo: GET /dashboard + external weather API queue amplification",
    databaseDemoTabTitle: "Database Schema",
    databaseDemoTabDesc: "DROP COLUMN → PostgreSQL (42703)",
    apiDemoTabTitle: "API Contract (OpenAPI)",
    apiDemoTabDesc: "REMOVE_RESPONSE_FIELD → ASGI",
    apiDemoHint: "Try the API contract breaking change demo",
    apiDemoScenario: "GET /users/{id} response field 'email' removed → consumer direct reference fails",
    perfDemoHint: "Try the production peak load reproduction demo",
    perfDemoScenario: "GET /dashboard + external API → 150 concurrent users causes 4.8s p95 explosion",
    domainDatabase: "Database",
    domainApi: "API Contract",
    domainPerformance: "Peak Load Proof",
    orDivider: "or",
    manualAnalysisLabel: "Analyze a GitHub repository and pull request manually",

    // Proof Summary
    proofSummaryEyebrow: "PROOF SUMMARY",
    proofSummaryHeading: "What this controlled experiment concludes",
    summaryChangeLabel: "PR change",
    summaryChangePending: "Structured change fact",
    summaryDependencyLabel: "Unchanged dependency",
    summaryDependencyFound: "Hidden application reference found",
    summaryDependencyPending: "No reference evidence",
    summaryObservationLabel: "PostgreSQL observation",
    summaryObservationApiLabel: "API runtime observation",
    summaryObservationPending: "Isolated experiment pending",
    summaryVerdictLabel: "Deterministic verdict",
    summaryVerdictPending: "PENDING",
    scopeInvariant: "This proof applies to this controlled experiment, not to the entire pull request or production system.",
    deterministicDetails: "Deterministic facts and dependency evidence",
    hypothesisDetails: "AI hypothesis and experiment plan",
    experimentDetails: "View experiment steps",

    // Change Facts
    changeFactsEyebrow: "STRUCTURED CHANGE FACTS",
    changedFiles: "Changed files",
    sqlMigrations: "SQL migrations",
    appFiles: "Application files",
    dbChanges: "DB changes",

    // Impact Surface
    impactEyebrow: "IMPACT SURFACE",
    impactHeading: "Cross-Layer Application References",
    impactIncomplete: "Limited Scan (Incomplete)",
    targetEntities: "Target entities",
    appFilesAffected: "App files affected",
    directReferences: "Direct references",
    potentialReferences: "Potential references",

    // Dependency Evidence
    evidenceEyebrow: "DEPENDENCY EVIDENCE",
    evidenceHeading: "Deterministic Source Code Matches",
    badgeChangedInPr: "Changed in this PR",
    badgeNotChangedInPr: "Not changed in this PR",
    matchDirect: "Direct Reference",
    matchContext: "Table + Column Context",
    matchColId: "Column Identifier",
    matchTableId: "Table Identifier",
    noEvidenceComplete: "No source references found in scanned application files.",
    noEvidenceIncomplete: "No references found in scanned subset. Source analysis was limited.",

    // Failure Hypotheses & Plans
    hypothesesEyebrow: "FAILURE HYPOTHESES & EXPERIMENT PLANNING",
    hypothesesHeading: "Evidence-Grounded AI Reasoning",
    unverifiedProposal: "UNVERIFIED PROPOSAL",
    hypothesisBadge: "HYPOTHESIS •",
    rationaleLabel: "Rationale:",
    expectedFailureLabel: "Expected Failure:",
    proposedExperimentBadge: "PROPOSED EXPERIMENT •",
    templateLabel: "Template:",
    executedInSandbox: "Executed in sandbox",
    notExecutedYet: "Not executed yet",
    expectedObservationLabel: "Expected observation:",
    runExperimentBtn: "Run experiment in isolated PostgreSQL →",
    runningExperimentBtn: "Reproducing failure in PostgreSQL...",
    sandboxNoticeDefault: "Sandbox execution is limited to controlled demo fixtures in this MVP.",
    noHypothesisGenerated: "No evidence-grounded failure hypothesis generated for this change.",

    // Observed Result
    reproducedFailBadge: "REPRODUCED • PROVEN FAIL",
    notReproducedPassBadge: "NOT REPRODUCED • PROVEN PASS",
    reproducedFailHeadline: "Failure reproduced in isolated PostgreSQL.",
    notReproducedPassHeadline: "This experiment completed without the expected failure.",
    inconclusiveHeadline: "Experiment executed with non-conclusive observations.",
    passSubnote: "This verdict applies only to this experiment, not to the entire pull request.",
    stepLabel: "Step",
    experimentContractLabel: "Experiment Contract:",
    subjectLabel: "Subject:",
    cleanupLabel: "Cleanup:",
    cleanupSucceeded: "SUCCEEDED",
    cleanupFailed: "FAILED",
    cleanupUnknown: "UNKNOWN",

    // Remediation
    remediationEyebrow: "REMEDIATION",
    noRemediationNeeded: "No remediation required for this experiment.",
    remediationHeading: "Deterministic compatibility remediation",
    remediationDesc: "This allowlisted remediation will be validated against the same experiment.",
    verifyRemediationBtn: "Verify remediation →",
    verifyingRemediationBtn: "Running authoritative before and after experiments...",
    remediationRequiresFailure: "Remediation verification requires a conclusive reproduced failure.",
    beforeLabel: "Before",
    sameExperimentLabel: "Same experiment",
    contractLabel: "Contract:",
    afterLabel: "After",
    invariantSameExp: "Same experiment:",
    invariantSubjectChanged: "Subject changed:",
    yes: "YES",
    no: "NO",
  },
};

interface I18nContextType {
  lang: Language;
  setLang: (lang: Language) => void;
  t: Translations;
}

const I18nContext = createContext<I18nContextType>({
  lang: "ko",
  setLang: () => {},
  t: translations.ko,
});

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Language>(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("changeproof_lang") as Language;
        if (saved === "ko" || saved === "en") {
          return saved;
        }
      } catch {
        // Ignore
      }
    }
    return "ko";
  });

  const setLang = (nextLang: Language) => {
    setLangState(nextLang);
    try {
      localStorage.setItem("changeproof_lang", nextLang);
    } catch {
      // Ignore
    }
  };

  const value = {
    lang,
    setLang,
    t: translations[lang],
  };

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextType {
  return useContext(I18nContext);
}

export function translateCategory(category: string, lang: Language): string {
  if (lang !== "ko") return category;
  switch (category) {
    case "SCHEMA_CONTRACT_BREAK":
      return "스키마 계약 위반 (SCHEMA_CONTRACT_BREAK)";
    case "MIGRATION_COMPATIBILITY":
      return "마이그레이션 호환성 위반 (MIGRATION_COMPATIBILITY)";
    case "NULLABILITY_COMPATIBILITY":
      return "NULL 제약조건 호환성 위반 (NULLABILITY_COMPATIBILITY)";
    case "TYPE_COMPATIBILITY":
      return "데이터 타입 호환성 위반 (TYPE_COMPATIBILITY)";
    case "TABLE_CONTRACT_BREAK":
      return "테이블 계약 위반 (TABLE_CONTRACT_BREAK)";
    case "API_CONTRACT_BREAK":
      return "API 계약 위반 (API_CONTRACT_BREAK)";
    case "EXTERNAL_DEPENDENCY_BOTTLENECK":
      return "외부 의존성 병목 (EXTERNAL_DEPENDENCY_BOTTLENECK)";
    default:
      return category;
  }
}

export function translateTemplate(template: string, lang: Language): string {
  if (lang !== "ko") return template;
  switch (template) {
    case "DROPPED_COLUMN_REFERENCE":
      return "삭제된 컬럼 참조 검증 (DROPPED_COLUMN_REFERENCE)";
    case "DROPPED_TABLE_REFERENCE":
      return "삭제된 테이블 참조 검증 (DROPPED_TABLE_REFERENCE)";
    case "NOT_NULL_COMPATIBILITY":
      return "NOT NULL 제약조건 호환성 검증 (NOT_NULL_COMPATIBILITY)";
    case "ALTER_TYPE_COMPATIBILITY":
      return "컬럼 타입 변경 호환성 검증 (ALTER_TYPE_COMPATIBILITY)";
    case "MIGRATION_APPLY":
      return "마이그레이션 적용 검증 (MIGRATION_APPLY)";
    case "API_RESPONSE_FIELD_COMPATIBILITY":
      return "API 응답 필드 호환성 검증 (API_RESPONSE_FIELD_COMPATIBILITY)";
    case "EXTERNAL_DEPENDENCY_LATENCY":
      return "외부 의존성 지연 증폭 검증 (EXTERNAL_DEPENDENCY_LATENCY)";
    default:
      return template;
  }
}

export function translateStatus(status: string, lang: Language): string {
  if (lang !== "ko") return status;
  switch (status) {
    case "PROPOSED":
      return "제안됨 (PROPOSED)";
    case "UNVERIFIED":
      return "미검증 (UNVERIFIED)";
    case "NOT_EXECUTED":
      return "미실행 (NOT_EXECUTED)";
    case "PLANNED":
      return "계획됨 (PLANNED)";
    case "EXECUTED":
      return "실행됨 (EXECUTED)";
    default:
      return status;
  }
}

export function translateStepType(stepType: string, lang: Language): string {
  if (lang !== "ko") return stepType;
  switch (stepType) {
    case "PREPARE_DATABASE":
      return "데이터베이스 준비 (PREPARE_DATABASE)";
    case "LOAD_BASELINE_SCHEMA":
      return "기준 스키마 로드 (LOAD_BASELINE_SCHEMA)";
    case "LOAD_SEED_DATA":
      return "시드 데이터 적재 (LOAD_SEED_DATA)";
    case "APPLY_MIGRATION":
      return "마이그레이션 적용 (APPLY_MIGRATION)";
    case "RUN_READ_QUERY":
      return "조회 쿼리 실행 (RUN_READ_QUERY)";
    case "RUN_WRITE_MUTATION":
      return "변경 쿼리 실행 (RUN_WRITE_MUTATION)";
    case "RUN_CONCURRENT_TRANSACTION":
      return "동시 트랜잭션 실행 (RUN_CONCURRENT_TRANSACTION)";
    case "CAPTURE_RESULT":
      return "결과 관측 (CAPTURE_RESULT)";
    case "PREPARE_API_ENVIRONMENT":
      return "인프로세스 ASGI API 환경 준비 (PREPARE_API_ENVIRONMENT)";
    case "SEND_HTTP_REQUEST":
      return "HTTP 요청 전송 (SEND_HTTP_REQUEST)";
    case "PROBE_RESPONSE_FIELD":
      return "소비자 필드 프로브 실행 (PROBE_RESPONSE_FIELD)";
    case "CAPTURE_API_RESULT":
      return "API 결과 관측 (CAPTURE_API_RESULT)";
    case "INITIALIZE_LOAD_ENVIRONMENT":
      return "부하 테스트 환경 준비 (INITIALIZE_LOAD_ENVIRONMENT)";
    case "RUN_BASELINE_LOAD":
      return "기준 부하 실행 (RUN_BASELINE_LOAD)";
    case "RUN_CONCURRENT_LOAD":
      return "동시 피크 부하 실행 (RUN_CONCURRENT_LOAD)";
    case "CAPTURE_PERFORMANCE_METRICS":
      return "성능 지표 및 지연 관측 (CAPTURE_PERFORMANCE_METRICS)";
    default:
      return stepType;
  }
}

export function translateStepStatus(status: string, lang: Language): string {
  if (lang !== "ko") return status;
  switch (status) {
    case "PASSED":
      return "성공 (PASSED)";
    case "FAILED":
      return "실패 (FAILED)";
    case "SKIPPED":
      return "건너뜀 (SKIPPED)";
    default:
      return status;
  }
}

export function translateStepDescription(description: string, lang: Language): string {
  if (lang !== "ko") return description;
  if (/^Provision isolated PostgreSQL/i.test(description)) {
    return "격리된 PostgreSQL 데이터베이스 인스턴스 프로비저닝";
  }
  if (/^Apply pre-PR baseline schema/i.test(description)) {
    return "PR 이전 기준(Baseline) 스키마 마이그레이션 적용";
  }
  if (/^Populate representative seed data/i.test(description)) {
    return "대표 시드(Seed) 데이터 적재";
  }
  if (/^Apply PR migration containing column drop/i.test(description)) {
    return "컬럼 삭제가 포함된 PR 마이그레이션 적용";
  }
  if (/^Apply PR migration/i.test(description)) {
    return "PR 마이그레이션 적용";
  }
  if (/^Execute (?:reference )?query against removed column "([^"]+)"/i.test(description)) {
    const col = description.match(/"([^"]+)"/)?.[1] ?? "column";
    return `삭제된 컬럼 "${col}"에 대한 참조 쿼리 실행`;
  }
  if (/^Execute (?:reference )?query/i.test(description)) {
    return "참조 쿼리 실행";
  }
  if (/^Capture database response and observe if column reference fails/i.test(description)) {
    return "데이터베이스 응답 캡처 및 컬럼 참조 실패 관측";
  }
  if (/^Capture database response/i.test(description)) {
    return "데이터베이스 응답 캡처 및 결과 관측";
  }
  if (/^Initialize in-process ASGI provider environment/i.test(description)) {
    return "인프로세스 ASGI 프로바이더 환경 초기화";
  }
  if (/^Send (GET|POST|PUT|DELETE|PATCH) request to/i.test(description)) {
    return `${description} (ASGI Transport)`;
  }
  if (/^Run consumer probe verifying required field '([^']+)'/i.test(description)) {
    const field = description.match(/'([^']+)'/)?.[1] ?? "field";
    return `필수 응답 필드 '${field}'에 대한 소비자 프로브 실행`;
  }
  if (/^Capture API response/i.test(description)) {
    return "API 응답 상태 및 누락 필드 관측 결과 캡처";
  }
  return description;
}

export function translateObservation(observation: string, lang: Language): string {
  if (lang !== "ko") return observation;
  if (/fail with undefined column error on ([a-zA-Z0-9_.]+)/i.test(observation)) {
    const target = observation.match(/fail with undefined column error on ([a-zA-Z0-9_.]+)/i)?.[1];
    return `${target} 컬럼이 존재하지 않아 정의되지 않은 컬럼 오류(undefined_column)로 쿼리 실행 실패 예상`;
  }
  if (/fail with undefined column/i.test(observation)) {
    return "정의되지 않은 컬럼 오류(undefined_column)로 쿼리 실행 실패 예상";
  }
  if (/fail with missing response field error on '([^']+)'/i.test(observation)) {
    const field = observation.match(/'([^']+)'/)?.[1] ?? "field";
    return `응답에서 필수 필드 '${field}'가 누락되어 소비자 프로브 실행 실패 예상`;
  }
  if (/saturate downstream capacity/i.test(observation) || /queue accumulation/i.test(observation)) {
    return "피크 동시 요청 시 외부 의존성 용량 포화로 인해 대기열이 급증하고 p95 응답 지연 폭발 및 타임아웃 발생 예상";
  }
  return observation;
}

export function translateRunSummary(summary: string, lang: Language): string {
  if (lang !== "ko") return summary;
  if (/Peak bottleneck reproduced/i.test(summary) || /downstream queue amplification/i.test(summary)) {
    return "통제된 부하 테스트에서 피크 병목 재현 성공: 동시 요청 증가 시 외부 의존성 용량 포화로 대기열이 적체되고 p95 지연 시간이 폭증했습니다 (DOWNSTREAM_QUEUE_AMPLIFICATION).";
  }
  if (/Peak load experiment passed/i.test(summary) || /Healthy throughput and latency/i.test(summary)) {
    return "피크 부하 검증 통과: 동시 트래픽 상황에서도 캐시 및 단일 요청 병합으로 정상적인 처리량과 안정적 지연 시간을 유지했습니다.";
  }
  if (
    /Column is removed by migration and referenced query failed with SQLSTATE 42703/i.test(summary)
  ) {
    return "격리된 PostgreSQL에서 장애 재현 성공: 마이그레이션에 의해 컬럼이 삭제되었으며, 참조 쿼리 실행 시 SQLSTATE 42703 (undefined_column: column does not exist) 오류가 발생했습니다.";
  }
  if (/API_MISSING_RESPONSE_FIELD/i.test(summary) || /missing from response payload/i.test(summary)) {
    return "통제된 API 런타임에서 장애 재현 성공: 응답에 필수 필드가 누락되어 소비자 프로브가 실패했습니다 (API_MISSING_RESPONSE_FIELD).";
  }
  if (/Failure reproduced/i.test(summary)) {
    return "격리된 환경에서 장애가 재현되었습니다.";
  }
  if (/Consumer probe passed/i.test(summary)) {
    return "통제된 API 런타임 검증 성공: 필수 응답 필드가 존재하여 소비자 프로브가 정상 통과했습니다.";
  }
  if (/Verification passed/i.test(summary)) {
    return "복구 적용 후 검증을 통과했습니다.";
  }
  return summary;
}

export function translateRemediationDescription(desc: string, lang: Language): string {
  if (lang !== "ko") return desc;
  if (/Preserve legacy_status during the compatibility window/i.test(desc)) {
    return "새로운 status 컬럼을 도입하는 호환성 유지 기간 동안 legacy_status 컬럼을 보존하여 구버전 코드 호환성을 유지합니다.";
  }
  if (/Preserve the removed '([^']+)' response field/i.test(desc)) {
    const field = desc.match(/'([^']+)'/)?.[1] ?? "field";
    return `클라이언트 호환성 보장을 위해 제거되었던 '${field}' 응답 필드를 복구하여 하위 호환성을 유지합니다.`;
  }
  return desc;
}

export function translateHypothesisContent(
  h: {
    title: string;
    statement: string;
    rationale: string;
    expected_failure_mode: string;
    assumptions?: string[];
  },
  lang: Language,
): {
  title: string;
  statement: string;
  rationale: string;
  expected_failure_mode: string;
  assumptions: string[];
} {
  if (lang !== "ko") {
    return {
      title: h.title,
      statement: h.statement,
      rationale: h.rationale,
      expected_failure_mode: h.expected_failure_mode,
      assumptions: h.assumptions ?? [],
    };
  }

  let title = h.title;
  let statement = h.statement;
  let rationale = h.rationale;
  let expected_failure_mode = h.expected_failure_mode;
  const assumptions = (h.assumptions ?? []).map((a) => {
    if (/application is deployed without/i.test(a)) {
      return "애플리케이션이 삭제된 컬럼을 반영하지 않은 채 배포됨";
    }
    if (/references to .* are meant to be functional/i.test(a)) {
      return "애플리케이션 내의 모든 해당 컬럼 참조가 정상 동작해야 함";
    }
    if (/no alternate code paths handle/i.test(a)) {
      return "컬럼 누락 시 이를 방어하는 대체 코드 경로가 없음";
    }
    return a;
  });

  if (/dropping (?:the )?([a-zA-Z0-9_.]+) (?:column )?may break/i.test(h.title)) {
    const col =
      h.title.match(/dropping (?:the )?([a-zA-Z0-9_.]+) (?:column )?may break/i)?.[1] ??
      "해당 컬럼";
    title = `${col} 컬럼 삭제 시 애플리케이션 런타임 장애 발생 가능`;
  } else if (/dropped column remains referenced/i.test(h.title)) {
    title = "삭제된 컬럼이 애플리케이션 코드에 여전히 참조되고 있음";
  }

  if (/application references (?:the )?['"]?([a-zA-Z0-9_.]+)['"]? column/i.test(h.statement)) {
    const col =
      h.statement.match(/['"]?([a-zA-Z0-9_.]+)['"]? column/i)?.[1] ?? "컬럼";
    statement = `애플리케이션 소스 코드에서 '${col}' 컬럼을 참조하고 있어, 마이그레이션으로 컬럼이 삭제된 후 런타임 오류가 발생할 수 있습니다.`;
  } else if (/application references orders\.legacy_status after migration/i.test(h.statement)) {
    statement = "마이그레이션 후에도 애플리케이션이 orders.legacy_status를 계속 참조합니다.";
  }

  if (
    /application contains qualified references to ['"]?([a-zA-Z0-9_.]+)['"]?/i.test(
      h.rationale,
    )
  ) {
    const col =
      h.rationale.match(/qualified references to ['"]?([a-zA-Z0-9_.]+)['"]?/i)?.[1] ??
      "해당 컬럼";
    rationale = `애플리케이션에 '${col}'에 대한 직접 참조가 존재하며, 마이그레이션으로 컬럼이 삭제되면 데이터베이스에서 이를 찾을 수 없어 쿼리 실행 실패(Exception)가 발생합니다.`;
  } else if (/order_service\.py.*references dropped column/i.test(h.rationale)) {
    rationale =
      "app/order_service.py에서 삭제된 컬럼을 직접 참조하고 있어 런타임 실패가 발생합니다.";
  }

  if (
    /runtime error due to missing column reference/i.test(h.expected_failure_mode) ||
    /undefinedcolumn/i.test(h.expected_failure_mode)
  ) {
    expected_failure_mode =
      "존재하지 않는 컬럼 참조로 인한 UndefinedColumn 오류 (SQLSTATE 42703)";
  }

  return { title, statement, rationale, expected_failure_mode, assumptions };
}
