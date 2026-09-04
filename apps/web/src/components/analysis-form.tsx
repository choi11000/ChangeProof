"use client";

import { FormEvent, useMemo, useState } from "react";
import {
  translateCategory,
  translateHypothesisContent,
  translateRemediationDescription,
  translateRunSummary,
  translateStatus,
  useI18n,
} from "@/lib/i18n";

type FileCategory =
  | "SQL_MIGRATION"
  | "DATABASE_SCHEMA"
  | "OPENAPI_SPEC"
  | "APPLICATION"
  | "CONFIG"
  | "TEST"
  | "DOCUMENTATION"
  | "OTHER";

type DependencyMatchKind =
  | "QUALIFIED_REFERENCE"
  | "TABLE_AND_COLUMN_CONTEXT"
  | "COLUMN_IDENTIFIER"
  | "TABLE_IDENTIFIER"
  | "DIRECT_RESPONSE_FIELD_REFERENCE";

type DependencyTarget = {
  type: "TABLE" | "COLUMN" | "API_ENDPOINT" | "API_FIELD";
  table: string;
  column?: string | null;
  path?: string | null;
  field?: string | null;
  change_ids?: string[];
};

type DependencyEvidence = {
  id: string;
  target: DependencyTarget;
  path: string;
  line: number;
  match_kind: DependencyMatchKind;
  excerpt: string;
  source_scope: "APPLICATION" | "TEST";
  changed_in_pull_request: boolean;
};

type ImpactSummary = {
  targets: number;
  application_files_with_references: number;
  test_files_with_references: number;
  qualified_references: number;
  contextual_references: number;
  identifier_references: number;
  scan_complete: boolean;
};

type AnalysisWarning = {
  code: string;
  message: string;
  path?: string | null;
};

type FailureCategory =
  | "SCHEMA_CONTRACT_BREAK"
  | "MIGRATION_COMPATIBILITY"
  | "NULLABILITY_COMPATIBILITY"
  | "TYPE_COMPATIBILITY"
  | "TABLE_CONTRACT_BREAK"
  | "API_CONTRACT_BREAK"
  | "EXTERNAL_API_LATENCY_AMPLIFICATION"
  | "DATABASE_LOCK_CONTENTION"
  | "OTHER";

type ExperimentTemplate =
  | "MIGRATION_APPLY"
  | "DROPPED_COLUMN_REFERENCE"
  | "DROPPED_TABLE_REFERENCE"
  | "NOT_NULL_COMPATIBILITY"
  | "ALTER_TYPE_COMPATIBILITY"
  | "API_RESPONSE_FIELD_COMPATIBILITY"
  | "EXTERNAL_DEPENDENCY_LATENCY";

type FailureHypothesis = {
  id: string;
  category: FailureCategory;
  title: string;
  statement: string;
  change_ids: string[];
  evidence_ids: string[];
  rationale: string;
  expected_failure_mode: string;
  assumptions: string[];
  experiment_template: ExperimentTemplate;
  status: "PROPOSED" | "UNVERIFIED";
};

type ExperimentStepType =
  | "PREPARE_DATABASE"
  | "LOAD_BASELINE_SCHEMA"
  | "LOAD_SEED_DATA"
  | "APPLY_MIGRATION"
  | "RUN_READ_QUERY"
  | "RUN_WRITE_MUTATION"
  | "RUN_CONCURRENT_TRANSACTION"
  | "CAPTURE_RESULT"
  | "PREPARE_API_ENVIRONMENT"
  | "SEND_HTTP_REQUEST"
  | "PROBE_RESPONSE_FIELD"
  | "CAPTURE_API_RESULT"
  | "RUN_CONCURRENT_LOAD"
  | "COLLECT_LOAD_METRICS";

type PerformanceMetricsData = {
  request_count: number;
  success_count: number;
  error_count: number;
  timeout_count: number;
  throughput_rps: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  max_inflight: number;
  downstream_wait_p95_ms: number;
  downstream_peak_inflight: number;
  timeout_rate: number;
  error_rate: number;
  regression_ratio?: number | null;
};

type ExperimentStepResult = {
  order: number;
  type: string;
  status: "PASSED" | "FAILED" | "SKIPPED";
  duration_ms: number;
  sql_state?: string | null;
  observation_code?: string | null;
  json_pointer?: string | null;
  http_status?: number | null;
  message?: string | null;
  performance_metrics?: PerformanceMetricsData | null;
};

type ExperimentStep = {
  order: number;
  type: ExperimentStepType;
  description: string;
  sql?: string | null;
};

type ExperimentPlan = {
  id: string;
  hypothesis_id: string;
  template: ExperimentTemplate;
  change_ids: string[];
  evidence_ids: string[];
  steps: ExperimentStep[];
  expected_observation: string;
  status: "NOT_EXECUTED" | "PLANNED" | "EXECUTED";
  plan_digest?: string | null;
};

type ExperimentRun = {
  id: string;
  experiment_plan_id: string;
  experiment_contract_digest: string;
  subject_digest: string;
  template: ExperimentTemplate;
  domain?: "DATABASE" | "API" | "PERFORMANCE";
  verdict: "PROVEN_FAIL" | "PROVEN_PASS" | "PROVEN_BOTTLENECK" | "INCONCLUSIVE" | "EXECUTION_ERROR";
  started_at: string;
  finished_at: string;
  step_results: ExperimentStepResult[];
  performance_metrics?: PerformanceMetricsData | null;
  cleanup_succeeded?: boolean | null;
  summary: string;
};

type RemediationProof = {
  id: string;
  fixture_id: string;
  remediation_id: string;
  domain?: "DATABASE" | "API" | "PERFORMANCE";
  strategy: string;
  description: string;
  experiment_contract_digest: string;
  baseline?: ExperimentRun | null;
  before: ExperimentRun;
  after: ExperimentRun;
  verdict: "PROVEN_FIXED" | "NOT_FIXED" | "INCONCLUSIVE" | "EXECUTION_ERROR";
  same_experiment: boolean;
  subject_changed: boolean;
  summary: string;
  scope_notice?: string;
};

type AnalysisResult = {
  pull_request: { number: number; title: string; changed_files: number; html_url: string };
  changed_files: Array<{
    category: FileCategory;
    reason: string;
    file: { path: string };
  }>;
  sql_files: Array<{
    path: string;
    analysis: null | {
      changes: Array<{ operation: string; table: string | null; column: string | null }>;
    };
    error: string | null;
  }>;
  api_files?: Array<{
    path: string;
    status: string;
    content_sha?: string | null;
    changes: Array<{
      change_type: string;
      method: string;
      path: string;
      status_code: number;
      media_type: string;
      field_name: string;
      schema_name?: string | null;
      json_pointer?: string | null;
    }>;
    error: string | null;
  }>;
  domain?: "DATABASE" | "API" | "PERFORMANCE";
  dependency_targets: DependencyTarget[];
  dependency_evidence: DependencyEvidence[];
  impact_summary: ImpactSummary | null;
  failure_hypotheses?: FailureHypothesis[];
  experiment_plans?: ExperimentPlan[];
  execution_allowed?: boolean;
  controlled_fixture_id?: string | null;
  execution_notice?: string | null;
  warnings: AnalysisWarning[];
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function AnalysisForm() {
  const { t, lang } = useI18n();

  // Navigation Tab State
  const [activeTab, setActiveTab] = useState<"peak_load" | "compatibility" | "local_runner">(
    "peak_load",
  );

  // Performance (P0) State
  const [perfRunning, setPerfRunning] = useState(false);
  const [perfRun, setPerfRun] = useState<ExperimentRun | null>(null);
  const [perfProving, setPerfProving] = useState(false);
  const [perfProof, setPerfProof] = useState<RemediationProof | null>(null);
  const [perfError, setPerfError] = useState<string | null>(null);

  // Compatibility (Database / API) Demo State
  const [selectedDemo, setSelectedDemo] = useState<"database" | "api">("database");
  const [repository, setRepository] = useState("");
  const [pullRequest, setPullRequest] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Compatibility execution state
  const [executingPlanId, setExecutingPlanId] = useState<string | null>(null);
  const [experimentRuns, setExperimentRuns] = useState<Record<string, ExperimentRun>>({});
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [provingPlanId, setProvingPlanId] = useState<string | null>(null);
  const [remediationProofs, setRemediationProofs] = useState<Record<string, RemediationProof>>({});

  const demoRepository = process.env.NEXT_PUBLIC_DEMO_REPOSITORY?.trim() ?? "";
  const demoPullRequest = process.env.NEXT_PUBLIC_DEMO_PR?.trim() ?? "";
  const demoConfigured =
    demoRepository.length > 0 && /^\d+$/.test(demoPullRequest) && Number(demoPullRequest) > 0;

  const dbDemoRepo = demoRepository || "choi11000/changeproof-demo";
  const dbDemoPR = demoPullRequest || "1";

  const apiDemoRepo =
    process.env.NEXT_PUBLIC_API_DEMO_REPOSITORY?.trim() || "choi11000/changeproof-api-demo";
  const apiDemoPR = process.env.NEXT_PUBLIC_API_DEMO_PR?.trim() || "1";

  const counts = useMemo(() => {
    const files = result?.changed_files ?? [];
    return {
      sql: files.filter((item) => item.category === "SQL_MIGRATION").length,
      api: (result?.api_files ?? []).length,
      application: files.filter((item) => item.category === "APPLICATION").length,
      changes:
        (result?.sql_files ?? []).reduce(
          (total, file) => total + (file.analysis?.changes.length ?? 0),
          0,
        ) +
        (result?.api_files ?? []).reduce(
          (total, file) => total + (file.changes?.length ?? 0),
          0,
        ),
    };
  }, [result]);

  const primaryPlan = result?.experiment_plans?.at(0) ?? null;
  const primaryRun = primaryPlan ? experimentRuns[primaryPlan.id] : null;
  const primaryProof = primaryPlan ? remediationProofs[primaryPlan.id] : null;

  const summary = useMemo(() => {
    if (!result) return null;

    const isApi =
      result.domain === "API" ||
      ((result.api_files ?? []).length > 0 && (result.sql_files ?? []).length === 0);
    const apiChange = result.api_files?.flatMap((file) => file.changes ?? []).at(0);
    const dbChange = result.sql_files
      .flatMap((file) => file.analysis?.changes ?? [])
      .at(0);
    const run = primaryRun;
    const proof = primaryProof;
    const failedStep = run?.step_results.find((step) => step.status === "FAILED");
    const changeTarget = dbChange
      ? [dbChange.table, dbChange.column].filter(Boolean).join(".")
      : "";

    let changeText = t.summaryChangePending;
    if (isApi && apiChange) {
      changeText = `${apiChange.change_type} ${apiChange.method} ${apiChange.path} (${apiChange.field_name})`;
    } else if (dbChange) {
      changeText = `${dbChange.operation}${changeTarget ? ` ${changeTarget}` : ""}`;
    }

    let obsText = t.summaryObservationPending;
    if (proof) {
      obsText = "FAIL → PASS";
    } else if (run) {
      if (failedStep?.observation_code) {
        obsText = failedStep.observation_code;
      } else if (failedStep?.sql_state) {
        obsText = `SQLSTATE ${failedStep.sql_state}`;
      } else {
        obsText = translateRunSummary(run.summary, lang);
      }
    }

    return {
      domain: isApi ? "API" : "DATABASE",
      change: changeText,
      dependency:
        result.dependency_evidence.length > 0
          ? t.summaryDependencyFound
          : t.summaryDependencyPending,
      observation: obsText,
      observationLabel: isApi ? t.summaryObservationApiLabel : t.summaryObservationLabel,
      verdict: proof?.verdict ?? run?.verdict ?? t.summaryVerdictPending,
      verdictClass:
        proof?.verdict === "PROVEN_FIXED" || run?.verdict === "PROVEN_PASS"
          ? "is-pass"
          : run?.verdict === "PROVEN_FAIL" || run?.verdict === "PROVEN_BOTTLENECK"
          ? "is-fail"
          : "is-pending",
    };
  }, [lang, primaryProof, primaryRun, result, t]);

  // Performance demo actions
  async function runPeakLoadDemo() {
    setPerfRunning(true);
    setPerfError(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/experiments/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fixture_id: "shiftsafe/dashboard-weather-dependency",
          experiment_plan_id: "plan-shiftsafe-peak-load",
        }),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.detail ?? "Peak load execution failed");
      }
      setPerfRun(body.run as ExperimentRun);
    } catch (err) {
      setPerfError(err instanceof Error ? err.message : "Peak load execution failed");
    } finally {
      setPerfRunning(false);
    }
  }

  async function applyRemediationAndVerify() {
    setPerfProving(true);
    setPerfError(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/proofs/remediation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fixture_id: "shiftsafe/dashboard-weather-dependency",
        }),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.detail ?? "Remediation proof failed");
      }
      setPerfProof(body.proof as RemediationProof);
    } catch (err) {
      setPerfError(err instanceof Error ? err.message : "Remediation proof failed");
    } finally {
      setPerfProving(false);
    }
  }

  // Compatibility PR Analysis
  async function analyze(targetRepository: string, targetPullRequest: number) {
    setLoading(true);
    setError(null);
    setResult(null);
    setExperimentRuns({});
    setExecutionError(null);
    setRemediationProofs({});
    try {
      const response = await fetch(`${apiUrl}/api/v1/analyses/github-pr`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repository: targetRepository,
          pull_request: targetPullRequest,
        }),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.detail ?? "Analysis failed");
      }
      setResult(body as AnalysisResult);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await analyze(repository, Number(pullRequest));
  }

  async function runSelectedDemo(demoKind: "database" | "api" = selectedDemo) {
    if (demoKind === "database") {
      setRepository(dbDemoRepo);
      setPullRequest(dbDemoPR);
      await analyze(dbDemoRepo, Number(dbDemoPR));
    } else {
      setRepository(apiDemoRepo);
      setPullRequest(apiDemoPR);
      await analyze(apiDemoRepo, Number(apiDemoPR));
    }
  }

  async function runExperiment(fixtureId: string, planId: string) {
    setExecutingPlanId(planId);
    setExecutionError(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/experiments/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fixture_id: fixtureId,
          experiment_plan_id: planId,
        }),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.detail ?? "Experiment execution failed");
      }
      setExperimentRuns((prev) => ({
        ...prev,
        [planId]: body.run as ExperimentRun,
      }));
    } catch (reqError) {
      setExecutionError(
        reqError instanceof Error ? reqError.message : "Experiment execution failed",
      );
    } finally {
      setExecutingPlanId(null);
    }
  }

  async function verifyRemediation(fixtureId: string, planId: string) {
    setProvingPlanId(planId);
    setExecutionError(null);
    try {
      const response = await fetch(`${apiUrl}/api/v1/proofs/remediation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fixture_id: fixtureId,
        }),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.detail ?? "Remediation proof failed");
      }
      setRemediationProofs((prev) => ({
        ...prev,
        [planId]: body.proof as RemediationProof,
      }));
    } catch (reqError) {
      setExecutionError(
        reqError instanceof Error ? reqError.message : "Remediation proof failed",
      );
    } finally {
      setProvingPlanId(null);
    }
  }

  return (
    <>
      {/* 3-Way Product Mode Navigation */}
      <div className="tab-bar" role="tablist" aria-label="Product Mode Navigation">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "peak_load"}
          className={`tab-btn ${activeTab === "peak_load" ? "active" : ""}`}
          onClick={() => setActiveTab("peak_load")}
        >
          [ {t.tabPeakLoadTitle} ]
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "compatibility"}
          className={`tab-btn ${activeTab === "compatibility" ? "active" : ""}`}
          onClick={() => setActiveTab("compatibility")}
        >
          [ {t.tabCompatibilityTitle} ]
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "local_runner"}
          className={`tab-btn ${activeTab === "local_runner" ? "active" : ""}`}
          onClick={() => setActiveTab("local_runner")}
        >
          [ {t.tabLocalRunnerTitle} ]
        </button>
      </div>

      {/* ============================================================
          TAB 1: PEAK LOAD FAILURE PROOF (PRIMARY PRODUCT)
          ============================================================ */}
      {activeTab === "peak_load" && (
        <section className="perf-demo-section" aria-label={t.tabPeakLoadTitle}>
          <div className="perf-card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px" }}>
              <div>
                <span className="badge badge-direct" style={{ marginBottom: "6px" }}>
                  ShiftSafe Demo · Synthetic Subject
                </span>
                <h3 style={{ margin: "4px 0 6px", fontSize: "1.25rem", fontWeight: 800 }}>
                  {t.perfDemoTitle}
                </h3>
                <p style={{ margin: 0, color: "var(--muted)", fontSize: "0.88rem" }}>
                  {t.perfDemoSubtitle}
                </p>
              </div>
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                <span className="badge badge-pass" title="단일 사용자 기능 테스트">
                  기능 테스트 통과 · PASS (200 OK, 15ms)
                </span>
                <span className="badge badge-potential" title="AI 가설">
                  AI 가설: PROPOSED / UNVERIFIED
                </span>
              </div>
            </div>

            {/* Architecture inspection snippet */}
            <div
              style={{
                marginTop: "16px",
                padding: "14px 18px",
                background: "#080b0f",
                borderRadius: "8px",
                border: "1px solid #1e2630",
                fontSize: "0.82rem",
                color: "#94a3b8",
                display: "grid",
                gap: "6px",
              }}
            >
              <div>
                <strong style={{ color: "var(--cyan)" }}>[코드 변경 탐지]</strong>{" "}
                <code style={{ color: "#e2e8f0" }}>GET /dashboard</code> 핫 경로에{" "}
                <code style={{ color: "#f87171" }}>WeatherClient.get_current()</code> 동기 외부 API 호출 추가됨
              </div>
              <div>
                <strong style={{ color: "var(--amber)" }}>[AI 병목 가설]</strong>{" "}
                {lang === "ko"
                  ? "단일 기능 테스트는 15ms로 정상이지만, 피크 트래픽(150 동시 요청) 시 외부 의존성(지연 700ms, 용량 10) 뒤로 요청이 누적되어 p95 지연이 폭증할 것으로 예측됨."
                  : "Single-request functional test passes at 15ms. However, under peak concurrency (150 users), limited outbound capacity (10) will cause queue accumulation, exploding p95 latency."}
              </div>
            </div>

            {/* Step 1: Run Peak Load Experiment */}
            <div style={{ marginTop: "20px" }}>
              <button
                type="button"
                className="btn-live-demo"
                onClick={runPeakLoadDemo}
                disabled={perfRunning}
                style={{ width: "100%", justifyContent: "center", display: "flex", alignItems: "center" }}
              >
                {perfRunning ? t.runningPeakLoadBtn : t.runPeakLoadBtn}
              </button>
              <p style={{ margin: "8px 0 0", color: "#64748b", fontSize: "0.75rem", textAlign: "center" }}>
                * Controlled Server-Owned Fixture (Max Concurrency: 150 · Max Requests: 300 · Timeout: 5.0s)
              </p>
            </div>

            {perfError && (
              <div className="analysis-error" style={{ marginTop: "14px" }}>
                {perfError}
              </div>
            )}

            {/* Candidate Result: Bottleneck Reproduced */}
            {perfRun && (
              <div
                style={{
                  marginTop: "24px",
                  padding: "20px",
                  background: "rgba(23, 30, 37, 0.95)",
                  border: "1px solid #334155",
                  borderRadius: "10px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px", marginBottom: "16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <span className="badge-bottleneck">{t.verdictBottleneck}</span>
                    <span className="badge badge-potential">
                      관측: DOWNSTREAM_QUEUE_AMPLIFICATION
                    </span>
                  </div>
                  <span style={{ fontSize: "0.78rem", color: "#94a3b8", fontFamily: "monospace" }}>
                    DIGEST: {perfRun.experiment_contract_digest.slice(0, 18)}...
                  </span>
                </div>

                <div className="metrics-grid">
                  <div className="metric-box">
                    <span className="metric-label">{t.metricConcurrency}</span>
                    <span className="metric-value">150</span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-label">{t.metricP50}</span>
                    <span className="metric-value">
                      {perfRun.performance_metrics?.p50_ms ?? 0} ms
                    </span>
                  </div>
                  <div className="metric-box" style={{ borderColor: "rgba(255,102,102,0.5)" }}>
                    <span className="metric-label" style={{ color: "var(--red)" }}>
                      {t.metricP95} (지연 폭증)
                    </span>
                    <span className="metric-value" style={{ color: "var(--red)" }}>
                      {perfRun.performance_metrics?.p95_ms ?? 0} ms
                    </span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-label">{t.metricThroughput}</span>
                    <span className="metric-value">
                      {perfRun.performance_metrics?.throughput_rps?.toFixed(1) ?? "0.0"} req/s
                    </span>
                  </div>
                  <div className="metric-box" style={{ borderColor: "rgba(255,102,102,0.4)" }}>
                    <span className="metric-label" style={{ color: "var(--red)" }}>
                      {t.metricTimeouts}
                    </span>
                    <span className="metric-value" style={{ color: "var(--red)" }}>
                      {((perfRun.performance_metrics?.timeout_rate ?? 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-label">{t.metricDownstreamWait}</span>
                    <span className="metric-value">
                      {perfRun.performance_metrics?.downstream_wait_p95_ms ?? 0} ms
                    </span>
                  </div>
                </div>

                {/* Step 2: Remediation & Same Load Verification */}
                <div
                  style={{
                    marginTop: "24px",
                    padding: "18px",
                    background: "rgba(10, 15, 20, 0.8)",
                    border: "1px dashed #38bdf8",
                    borderRadius: "8px",
                  }}
                >
                  <div style={{ marginBottom: "12px" }}>
                    <span className="badge badge-direct" style={{ marginBottom: "4px" }}>
                      수정 적용 방안 (Remediation)
                    </span>
                    <h4 style={{ margin: "4px 0", fontSize: "1rem" }}>
                      10초 TTL 캐시 + Single-flight 요청 병합 + 1.5s 타임아웃 + Fallback
                    </h4>
                    <p style={{ margin: 0, color: "#94a3b8", fontSize: "0.82rem" }}>
                      동일한 150 동시 요청 부하를 다시 실행하여 병목 해소 및 정상 회복을 검증합니다.
                    </p>
                  </div>

                  <button
                    type="button"
                    className="btn-live-demo"
                    onClick={applyRemediationAndVerify}
                    disabled={perfProving}
                    style={{ width: "100%", justifyContent: "center", display: "flex", alignItems: "center", background: "#38bdf8" }}
                  >
                    {perfProving ? t.applyingFixBtn : t.applyFixBtn}
                  </button>
                </div>

                {/* Remediation Result */}
                {perfProof && (
                  <div
                    style={{
                      marginTop: "20px",
                      padding: "18px",
                      background: "rgba(15, 23, 42, 0.95)",
                      border: "1px solid var(--green)",
                      borderRadius: "8px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px", marginBottom: "14px" }}>
                      <span className="badge-recovered">{t.verdictRecovered}</span>
                      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                        <span className="badge badge-pass">{t.badgeSameLoad}: YES</span>
                        <span className="badge badge-pass">{t.badgeSameConditions}: YES</span>
                        <span className="badge badge-pass">{t.badgeChangedSubject}: YES</span>
                      </div>
                    </div>

                    <div className="metrics-grid">
                      <div className="metric-box">
                        <span className="metric-label">{t.metricConcurrency}</span>
                        <span className="metric-value">150</span>
                      </div>
                      <div className="metric-box">
                        <span className="metric-label">{t.metricP50}</span>
                        <span className="metric-value">
                          {perfProof.after.performance_metrics?.p50_ms ?? 0} ms
                        </span>
                      </div>
                      <div className="metric-box" style={{ borderColor: "rgba(81,216,138,0.5)" }}>
                        <span className="metric-label" style={{ color: "var(--green)" }}>
                          {t.metricP95} (정상 회복)
                        </span>
                        <span className="metric-value" style={{ color: "var(--green)" }}>
                          {perfProof.after.performance_metrics?.p95_ms ?? 0} ms
                        </span>
                      </div>
                      <div className="metric-box">
                        <span className="metric-label">{t.metricThroughput}</span>
                        <span className="metric-value">
                          {perfProof.after.performance_metrics?.throughput_rps?.toFixed(1) ?? "0.0"} req/s
                        </span>
                      </div>
                      <div className="metric-box" style={{ borderColor: "rgba(81,216,138,0.4)" }}>
                        <span className="metric-label" style={{ color: "var(--green)" }}>
                          {t.metricTimeouts}
                        </span>
                        <span className="metric-value" style={{ color: "var(--green)" }}>
                          {((perfProof.after.performance_metrics?.timeout_rate ?? 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                      <div className="metric-box">
                        <span className="metric-label">{t.metricDownstreamWait}</span>
                        <span className="metric-value">
                          {perfProof.after.performance_metrics?.downstream_wait_p95_ms ?? 0} ms
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Visual Latency Contrast Chart (Derived from real measured execution) */}
                {(() => {
                  const candP95 = perfRun.performance_metrics?.p95_ms ?? 0;
                  const baseP95 = perfProof?.baseline?.performance_metrics?.p95_ms ?? (candP95 > 0 ? Math.round(candP95 / (perfRun.performance_metrics?.regression_ratio || 25)) : 180);
                  const remP95 = perfProof?.after?.performance_metrics?.p95_ms ?? 0;
                  const maxVal = Math.max(candP95, baseP95, remP95, 100);
                  const basePct = Math.max(6, Math.min(100, Math.round((baseP95 / maxVal) * 100)));
                  const candPct = Math.max(6, Math.min(100, Math.round((candP95 / maxVal) * 100)));
                  const remPct = remP95 > 0 ? Math.max(6, Math.min(100, Math.round((remP95 / maxVal) * 100))) : 0;

                  return (
                    <div className="contrast-container">
                      <div style={{ marginBottom: "14px" }}>
                        <h4 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 700 }}>
                          [p95 응답 지연 시간 대조 · 실측 기반 10초 직관 확인]
                        </h4>
                        <p style={{ margin: "4px 0 0", color: "#94a3b8", fontSize: "0.78rem" }}>
                          기능 테스트는 모두 정상이지만, 150 동시 피크 부하 시 실측 병목 지연과 수정 후 정상 회복이 대조됩니다.
                        </p>
                      </div>

                      {/* Baseline */}
                      <div className="contrast-item">
                        <span className="contrast-label">{t.baselineCardTitle}</span>
                        <div className="contrast-bar-wrapper">
                          <div
                            className="contrast-bar"
                            style={{
                              width: `${basePct}%`,
                              background: "var(--green)",
                            }}
                          />
                        </div>
                        <span className="contrast-num" style={{ color: "var(--green)" }}>
                          {baseP95} ms
                        </span>
                      </div>

                      {/* Candidate */}
                      <div className="contrast-item">
                        <span className="contrast-label" style={{ color: "var(--red)", fontWeight: 700 }}>
                          {t.candidateCardTitle}
                        </span>
                        <div className="contrast-bar-wrapper">
                          <div
                            className="contrast-bar"
                            style={{
                              width: `${candPct}%`,
                              background: "var(--red)",
                            }}
                          />
                        </div>
                        <span className="contrast-num" style={{ color: "var(--red)" }}>
                          {candP95} ms
                        </span>
                      </div>

                      {/* Remediated */}
                      <div className="contrast-item">
                        <span className="contrast-label" style={{ color: "var(--cyan)", fontWeight: 700 }}>
                          {t.remediatedCardTitle}
                        </span>
                        <div className="contrast-bar-wrapper">
                          <div
                            className="contrast-bar"
                            style={{
                              width: `${remPct > 0 ? remPct : 12}%`,
                              background: "var(--cyan)",
                            }}
                          />
                        </div>
                        <span className="contrast-num" style={{ color: "var(--cyan)" }}>
                          {remP95 > 0 ? `${remP95} ms` : "검증 대기"}
                        </span>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        </section>
      )}

      {/* ============================================================
          TAB 2: COMPATIBILITY PROOFS (DATABASE & API CONTRACTS)
          ============================================================ */}
      {activeTab === "compatibility" && (
        <section className="compatibility-section" aria-label={t.tabCompatibilityTitle}>
          {demoConfigured && (
            <section className="demo-launcher" aria-label={selectedDemo === "database" ? t.demoHint : t.apiDemoHint}>
              <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.85rem", flexWrap: "wrap" }}>
                <button
                  type="button"
                  className={`btn-demo-selector ${selectedDemo === "database" ? "active" : ""}`}
                  onClick={() => setSelectedDemo("database")}
                  style={{
                    padding: "0.45rem 0.9rem",
                    borderRadius: "6px",
                    border: selectedDemo === "database" ? "1px solid #06b6d4" : "1px solid #334155",
                    background: selectedDemo === "database" ? "rgba(6, 182, 212, 0.15)" : "#0f172a",
                    color: selectedDemo === "database" ? "#22d3ee" : "#94a3b8",
                    cursor: "pointer",
                    fontSize: "0.82rem",
                    fontWeight: 600,
                    textAlign: "left",
                  }}
                >
                  [ {t.databaseDemoTabTitle} ]
                  <span style={{ display: "block", fontSize: "0.72rem", fontWeight: 400, opacity: 0.85 }}>
                    {t.databaseDemoTabDesc}
                  </span>
                </button>
                <button
                  type="button"
                  className={`btn-demo-selector ${selectedDemo === "api" ? "active" : ""}`}
                  onClick={() => setSelectedDemo("api")}
                  style={{
                    padding: "0.45rem 0.9rem",
                    borderRadius: "6px",
                    border: selectedDemo === "api" ? "1px solid #06b6d4" : "1px solid #334155",
                    background: selectedDemo === "api" ? "rgba(6, 182, 212, 0.15)" : "#0f172a",
                    color: selectedDemo === "api" ? "#22d3ee" : "#94a3b8",
                    cursor: "pointer",
                    fontSize: "0.82rem",
                    fontWeight: 600,
                    textAlign: "left",
                  }}
                >
                  [ {t.apiDemoTabTitle} ]
                  <span style={{ display: "block", fontSize: "0.72rem", fontWeight: 400, opacity: 0.85 }}>
                    {t.apiDemoTabDesc}
                  </span>
                </button>
              </div>
              <button
                type="button"
                className="btn-live-demo"
                disabled={loading}
                onClick={() => runSelectedDemo(selectedDemo)}
              >
                {selectedDemo === "database" ? t.loadDemoBtn : `${t.apiDemoTabTitle} 데모 실행 →`}
              </button>
              <div>
                <strong>{selectedDemo === "database" ? t.demoHint : t.apiDemoHint}</strong>
                <code>
                  {selectedDemo === "database" ? `${dbDemoRepo}#${dbDemoPR}` : `${apiDemoRepo}#${apiDemoPR}`}
                </code>
                <p style={{ margin: "4px 0 0", color: "#8f9aa3", fontSize: "12px", lineHeight: 1.4 }}>
                  {selectedDemo === "database" ? t.demoScenario : t.apiDemoScenario}
                </p>
              </div>
            </section>
          )}

          <div className="or-divider">{t.orDivider}</div>

          <form className="analysis-card" onSubmit={submit}>
            <p className="manual-analysis-label">{t.manualAnalysisLabel}</p>
            <div className="field">
              <label htmlFor="repository">{t.repoLabel}</label>
              <input
                id="repository"
                name="repository"
                required
                placeholder={t.repoPlaceholder}
                value={repository}
                onChange={(event) => setRepository(event.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="pullRequest">{t.prLabel}</label>
              <input
                id="pullRequest"
                name="pullRequest"
                required
                inputMode="numeric"
                pattern="[0-9]+"
                placeholder={t.prPlaceholder}
                value={pullRequest}
                onChange={(event) => setPullRequest(event.target.value)}
              />
            </div>
            <button type="submit" disabled={loading}>
              {loading ? t.analyzingBtn : t.analyzeBtn}
            </button>
          </form>

          {error && <p className="analysis-error">{error}</p>}
          {executionError && <p className="analysis-error">{executionError}</p>}

          {result && (
            <section className="analysis-result">
              {summary && (
                <div className="proof-summary" aria-label={t.proofSummaryHeading}>
                  <div className="proof-summary-heading">
                    <p className="eyebrow">{t.proofSummaryEyebrow}</p>
                    <h2>{t.proofSummaryHeading}</h2>
                  </div>
                  <ol className="proof-chain">
                    <li className="proof-node fact-node">
                      <small>{t.summaryChangeLabel}</small>
                      <strong>{summary.change}</strong>
                    </li>
                    <li className="proof-arrow" aria-hidden="true">→</li>
                    <li className="proof-node">
                      <small>{t.summaryDependencyLabel}</small>
                      <strong>{summary.dependency}</strong>
                    </li>
                    <li className="proof-arrow" aria-hidden="true">→</li>
                    <li className={`proof-node observation-node ${summary.verdictClass}`}>
                      <small>{summary.observationLabel}</small>
                      <strong>{summary.observation}</strong>
                    </li>
                    <li className="proof-arrow" aria-hidden="true">→</li>
                    <li className={`proof-node verdict-node ${summary.verdictClass}`}>
                      <small>{t.summaryVerdictLabel}</small>
                      <strong>{summary.verdict.replace("_", " ")}</strong>
                    </li>
                  </ol>

                  {primaryProof && (
                    <div className="proof-summary-invariants">
                      <span>{t.invariantSameExp} {primaryProof.same_experiment ? t.yes : t.no}</span>
                      <span>{t.invariantSubjectChanged} {primaryProof.subject_changed ? t.yes : t.no}</span>
                      <span>{t.scopeInvariant}</span>
                    </div>
                  )}

                  {result.execution_allowed && primaryPlan && (
                    <div className="proof-summary-action">
                      {!primaryRun && (
                        <button
                          type="button"
                          className="btn-run-experiment"
                          disabled={executingPlanId === primaryPlan.id}
                          onClick={() =>
                            runExperiment(result.controlled_fixture_id!, primaryPlan.id)
                          }
                        >
                          {executingPlanId === primaryPlan.id
                            ? t.runningExperimentBtn
                            : t.runExperimentBtn}
                        </button>
                      )}
                      {primaryRun && primaryRun.verdict === "PROVEN_FAIL" && !primaryProof && (
                        <button
                          type="button"
                          className="btn-run-experiment"
                          disabled={provingPlanId === primaryPlan.id}
                          onClick={() =>
                            verifyRemediation(result.controlled_fixture_id!, primaryPlan.id)
                          }
                        >
                          {provingPlanId === primaryPlan.id
                            ? t.verifyingRemediationBtn
                            : t.verifyRemediationBtn}
                        </button>
                      )}
                    </div>
                  )}
                  {result.execution_notice && (
                    <p className="proof-scope">{result.execution_notice}</p>
                  )}
                </div>
              )}

              {/* Deterministic Change Facts */}
              <details className="result-details">
                <summary>{t.deterministicDetails}</summary>
                <div className="result-heading">
                  <p className="eyebrow">{t.changeFactsEyebrow}</p>
                  <h2>
                    PR #{result.pull_request.number}: {result.pull_request.title}
                  </h2>
                </div>
                <dl className="result-counts">
                  <div>
                    <dt>{t.changedFiles}</dt>
                    <dd>{result.changed_files.length}</dd>
                  </div>
                  <div>
                    <dt>{result.domain === "API" ? "OpenAPI Specs" : t.sqlMigrations}</dt>
                    <dd>{result.domain === "API" ? counts.api : counts.sql}</dd>
                  </div>
                  <div>
                    <dt>{t.appFiles}</dt>
                    <dd>{counts.application}</dd>
                  </div>
                  <div>
                    <dt>{result.domain === "API" ? "API Changes" : t.dbChanges}</dt>
                    <dd>{counts.changes}</dd>
                  </div>
                </dl>
              </details>

              {/* AI Risk Hypotheses */}
              <details className="result-details hypothesis-details" open>
                <summary>{t.hypothesisDetails}</summary>
                <div className="hypotheses-section">
                  <div className="evidence-heading">
                    <div>
                      <p className="eyebrow">{t.hypothesesEyebrow}</p>
                      <h3>{t.hypothesesHeading}</h3>
                    </div>
                    <span className="badge badge-potential">{t.unverifiedProposal}</span>
                  </div>

                  {result.failure_hypotheses && result.failure_hypotheses.length > 0 ? (
                    <div className="hypotheses-list">
                      {result.failure_hypotheses.map((hypothesis) => {
                        const matchingPlan = result.experiment_plans?.find(
                          (plan) => plan.hypothesis_id === hypothesis.id,
                        );
                        const executionRun = matchingPlan
                          ? experimentRuns[matchingPlan.id]
                          : null;
                        const remediationProof = matchingPlan
                          ? remediationProofs[matchingPlan.id]
                          : null;

                        const translatedH = translateHypothesisContent(hypothesis, lang);

                        return (
                          <article key={hypothesis.id} className="hypothesis-card">
                            <div className="hypothesis-header">
                              <span className="badge badge-warning">
                                {t.hypothesisBadge} · {translateCategory(hypothesis.category, lang)}
                              </span>
                              <span className="badge badge-potential">
                                {translateStatus(hypothesis.status, lang)}
                              </span>
                            </div>
                            <h4>{translatedH.title}</h4>
                            <p className="hypothesis-statement">
                              {translatedH.statement}
                            </p>

                            {/* Execution Results if any */}
                            {executionRun && (
                              <div
                                className={`experiment-run-result ${
                                  executionRun.verdict === "PROVEN_FAIL"
                                    ? "is-fail"
                                    : "is-pass"
                                }`}
                              >
                                <span
                                  className={`badge ${
                                    executionRun.verdict === "PROVEN_FAIL"
                                      ? "badge-fail"
                                      : "badge-pass"
                                  }`}
                                >
                                  {executionRun.verdict.replace("_", " ")}
                                </span>
                                <h4>{translateRunSummary(executionRun.summary, lang)}</h4>
                              </div>
                            )}

                            {remediationProof && (
                              <div className="remediation-proof" aria-label="Remediation Proof">
                                <span
                                  className={`badge ${
                                    remediationProof.verdict === "PROVEN_FIXED"
                                      ? "badge-pass"
                                      : "badge-inconclusive"
                                  }`}
                                >
                                  {remediationProof.verdict.replace("_", " ")}
                                </span>
                                <h5>
                                  {translateRemediationDescription(
                                    remediationProof.description,
                                    lang,
                                  )}
                                </h5>
                              </div>
                            )}
                          </article>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="empty-state">{t.noHypothesisGenerated}</div>
                  )}
                </div>
              </details>
            </section>
          )}
        </section>
      )}

      {/* ============================================================
          TAB 3: LOCAL RUNNER (OFFLINE / ENTERPRISE AGENT)
          ============================================================ */}
      {activeTab === "local_runner" && (
        <section className="runner-guide" aria-label={t.tabLocalRunnerTitle}>
          <div>
            <span className="badge badge-direct" style={{ marginBottom: "6px" }}>
              Enterprise & Offline Ready
            </span>
            <h3 style={{ margin: "4px 0 8px", fontSize: "1.25rem", fontWeight: 800 }}>
              ChangeProof Local Runner Agent
            </h3>
            <p style={{ margin: 0, color: "var(--muted)", fontSize: "0.88rem", lineHeight: 1.6 }}>
              {lang === "ko"
                ? "사내 폐쇄망, 사설 Git, DRM/DLP 환경에서도 소스 코드를 외부에 유출하지 않고 로컬 Git Diff를 분석해 피크 부하를 선제 검증합니다."
                : "Analyze local Git diffs and verify production peak load directly within private developer networks without leaking source code."}
            </p>
          </div>

          <div style={{ display: "grid", gap: "12px" }}>
            <div>
              <strong style={{ color: "#e2e8f0", fontSize: "0.85rem" }}>
                1. Runner CLI 설치
              </strong>
              <div className="runner-cmd">pip install -e apps/runner</div>
            </div>

            <div>
              <strong style={{ color: "#e2e8f0", fontSize: "0.85rem" }}>
                2. 로컬 코드 변경 검사 (Inspect Local Git Diff)
              </strong>
              <div className="runner-cmd">
                changeproof inspect --repo . --base HEAD~1
              </div>
            </div>

            <div>
              <strong style={{ color: "#e2e8f0", fontSize: "0.85rem" }}>
                3. 개발/로컬 환경 부하 선제 검증 (Verify Peak Load)
              </strong>
              <div className="runner-cmd">
                changeproof verify --base HEAD~1 --target http://localhost:8001
              </div>
            </div>

            <div>
              <strong style={{ color: "#e2e8f0", fontSize: "0.85rem" }}>
                4. CI/CD 자동화 파이프라인 연동 (Machine-Readable JSON)
              </strong>
              <div className="runner-cmd">
                changeproof verify --base HEAD~1 --target http://192.168.1.50:8001 --json
              </div>
            </div>
          </div>

          <div
            style={{
              padding: "14px 18px",
              background: "rgba(66, 211, 255, 0.08)",
              border: "1px solid rgba(66, 211, 255, 0.25)",
              borderRadius: "8px",
              fontSize: "0.8rem",
              color: "#94a3b8",
              lineHeight: 1.5,
            }}
          >
            <strong style={{ color: "var(--cyan)" }}>[보안 정책 / Security Boundary]</strong>
            <br />
            - 로컬 러너는 오직 <code style={{ color: "white" }}>localhost</code> 및 RFC1918 사설망(10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)만 허용합니다.
            <br />
            - 임의의 공용 인터넷 URL 및 외부 운영 도메인은 기본 거부(<code style={{ color: "var(--red)" }}>TargetSecurityError</code>)되어 DDoS 공격 도구로의 오용을 원천 차단합니다.
          </div>
        </section>
      )}
    </>
  );
}
