"use client";

import React, { createContext, useContext, useState } from "react";

export type Language = "ko" | "en";

export interface Translations {
  // Nav
  brand: string;
  systemsReady: string;
  langKo: string;
  langEn: string;

  // Hero
  heroEyebrow: string;
  heroTitle1: string;
  heroTitle2: string;
  heroLede: string;
  flowStep1: string;
  flowStep2: string;
  flowStep3: string;
  flowAriaLabel: string;
  pipelineAriaLabel: string;
  stages: string[];

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
    systemsReady: "시스템 정상 작동 중",
    langKo: "한국어",
    langEn: "English",

    // Hero
    heroEyebrow: "데이터베이스 변경 리스크 검증 에이전트",
    heroTitle1: "배포 전에 변경의 안전성을",
    heroTitle2: "직접 증명하세요.",
    heroLede:
      "ChangeProof는 PR 변경사항을 검증된 증거, 결정론적 리스크, 그리고 직접 검증 가능한 복구책으로 전환합니다.",
    flowStep1: "변경사항 분석",
    flowStep2: "장애 재현 (샌드박스)",
    flowStep3: "수정 검증 (동일 실험)",
    flowAriaLabel: "3단계 증명 흐름",
    pipelineAriaLabel: "분석 파이프라인",
    stages: ["이해", "의존성", "검증", "증거", "복구"],

    // Principles
    principleEyebrow: "설계 기반 결정론",
    principleTitle1: "추론은 가설을 만들고,",
    principleTitle2: "증거가 판정을 내립니다.",
    capabilityLabel: "현재 지원 기능",
    capabilityTitle: "PR → 구조화된 변경 팩트",
    capabilityDesc:
      "임의로 조작된 리스크 점수는 없습니다. 모든 팩트는 직접 검사 가능한 실제 소스 코드에서 시작합니다.",

    // Analysis Form
    repoLabel: "GitHub 저장소",
    repoPlaceholder: "https://github.com/acme/risky-saas",
    prLabel: "풀 리퀘스트 번호",
    prPlaceholder: "42",
    analyzeBtn: "변경사항 분석",
    analyzingBtn: "분석 중…",
    loadDemoBtn: "데모 PR 불러오기",
    demoHint: "준비된 SaaS 마이그레이션 데모 실행",

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
    systemsReady: "Systems ready",
    langKo: "한국어",
    langEn: "English",

    // Hero
    heroEyebrow: "DATABASE CHANGE RISK AGENT",
    heroTitle1: "Prove a change is safe",
    heroTitle2: "before it ships.",
    heroLede:
      "ChangeProof turns pull-request changes into validated evidence, deterministic risk, and a remediation you can verify.",
    flowStep1: "Analyze the change",
    flowStep2: "Reproduce the failure",
    flowStep3: "Verify the fix",
    flowAriaLabel: "Three-step proof flow",
    pipelineAriaLabel: "Analysis pipeline",
    stages: ["Understand", "Dependencies", "Validate", "Evidence", "Remediate"],

    // Principles
    principleEyebrow: "DETERMINISTIC BY DESIGN",
    principleTitle1: "Reasoning makes a hypothesis.",
    principleTitle2: "Evidence earns the verdict.",
    capabilityLabel: "CURRENT CAPABILITY",
    capabilityTitle: "PR → structured change facts",
    capabilityDesc:
      "No invented risk score. Every fact starts with source we can inspect.",

    // Analysis Form
    repoLabel: "GitHub repository",
    repoPlaceholder: "https://github.com/acme/risky-saas",
    prLabel: "Pull request",
    prPlaceholder: "42",
    analyzeBtn: "Analyze change",
    analyzingBtn: "Analyzing…",
    loadDemoBtn: "Load demo PR",
    demoHint: "Try prepared risky SaaS migration",

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
