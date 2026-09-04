"use client";

import { FormEvent, useMemo, useState } from "react";
import {
  Translations,
  translateCategory,
  translateHypothesisContent,
  translateObservation,
  translateRemediationDescription,
  translateRunSummary,
  translateStatus,
  translateStepDescription,
  translateStepStatus,
  translateStepType,
  translateTemplate,
  useI18n,
} from "@/lib/i18n";

type FileCategory =
  | "SQL_MIGRATION"
  | "DATABASE_SCHEMA"
  | "APPLICATION"
  | "CONFIG"
  | "TEST"
  | "DOCUMENTATION"
  | "OTHER";

type DependencyMatchKind =
  | "QUALIFIED_REFERENCE"
  | "TABLE_AND_COLUMN_CONTEXT"
  | "COLUMN_IDENTIFIER"
  | "TABLE_IDENTIFIER";

type DependencyTarget = {
  type: "TABLE" | "COLUMN";
  table: string;
  column?: string | null;
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
  | "OTHER";

type ExperimentTemplate =
  | "MIGRATION_APPLY"
  | "DROPPED_COLUMN_REFERENCE"
  | "DROPPED_TABLE_REFERENCE"
  | "NOT_NULL_COMPATIBILITY"
  | "ALTER_TYPE_COMPATIBILITY";

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
  | "CAPTURE_RESULT";

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

type ExperimentStepResult = {
  order: number;
  type: string;
  status: "PASSED" | "FAILED" | "SKIPPED";
  duration_ms: number;
  sql_state?: string | null;
  message?: string | null;
};

type ExperimentRun = {
  id: string;
  experiment_plan_id: string;
  experiment_contract_digest: string;
  subject_digest: string;
  template: ExperimentTemplate;
  verdict: "PROVEN_FAIL" | "PROVEN_PASS" | "INCONCLUSIVE" | "EXECUTION_ERROR";
  started_at: string;
  finished_at: string;
  step_results: ExperimentStepResult[];
  cleanup_succeeded?: boolean | null;
  summary: string;
};

type RemediationProof = {
  id: string;
  fixture_id: string;
  remediation_id: string;
  strategy: string;
  description: string;
  experiment_contract_digest: string;
  before: ExperimentRun;
  after: ExperimentRun;
  verdict: "PROVEN_FIXED" | "NOT_FIXED" | "INCONCLUSIVE" | "EXECUTION_ERROR";
  same_experiment: boolean;
  subject_changed: boolean;
  summary: string;
  scope_notice: string;
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

function matchKindLabel(
  kind: DependencyMatchKind,
  t: Translations,
): { label: string; className: string } {
  switch (kind) {
    case "QUALIFIED_REFERENCE":
      return { label: t.matchDirect, className: "badge badge-direct" };
    case "TABLE_AND_COLUMN_CONTEXT":
      return { label: t.matchContext, className: "badge badge-context" };
    case "COLUMN_IDENTIFIER":
      return { label: t.matchColId, className: "badge badge-potential" };
    case "TABLE_IDENTIFIER":
      return { label: t.matchTableId, className: "badge badge-direct" };
    default:
      return { label: kind, className: "badge" };
  }
}

export function AnalysisForm() {
  const { t, lang } = useI18n();
  const [repository, setRepository] = useState("");
  const [pullRequest, setPullRequest] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Phase 6 execution state
  const [executingPlanId, setExecutingPlanId] = useState<string | null>(null);
  const [experimentRuns, setExperimentRuns] = useState<Record<string, ExperimentRun>>({});
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [provingPlanId, setProvingPlanId] = useState<string | null>(null);
  const [remediationProofs, setRemediationProofs] = useState<Record<string, RemediationProof>>({});
  const demoRepository = process.env.NEXT_PUBLIC_DEMO_REPOSITORY?.trim() ?? "";
  const demoPullRequest = process.env.NEXT_PUBLIC_DEMO_PR?.trim() ?? "";
  const demoConfigured =
    demoRepository.length > 0 && /^\d+$/.test(demoPullRequest) && Number(demoPullRequest) > 0;

  const counts = useMemo(() => {
    const files = result?.changed_files ?? [];
    return {
      sql: files.filter((item) => item.category === "SQL_MIGRATION").length,
      application: files.filter((item) => item.category === "APPLICATION").length,
      changes: (result?.sql_files ?? []).reduce(
        (total, file) => total + (file.analysis?.changes.length ?? 0),
        0,
      ),
    };
  }, [result]);

  const primaryPlan = result?.experiment_plans?.at(0) ?? null;
  const primaryRun = primaryPlan ? experimentRuns[primaryPlan.id] : null;
  const primaryProof = primaryPlan ? remediationProofs[primaryPlan.id] : null;

  const summary = useMemo(() => {
    if (!result) return null;

    const change = result.sql_files
      .flatMap((file) => file.analysis?.changes ?? [])
      .at(0);
    const run = primaryRun;
    const proof = primaryProof;
    const failedStep = run?.step_results.find((step) => step.status === "FAILED");
    const changeTarget = change
      ? [change.table, change.column].filter(Boolean).join(".")
      : "";

    return {
      change: change
        ? `${change.operation}${changeTarget ? ` ${changeTarget}` : ""}`
        : t.summaryChangePending,
      dependency:
        result.dependency_evidence.length > 0
          ? t.summaryDependencyFound
          : t.summaryDependencyPending,
      observation: proof
        ? "FAIL → PASS"
        : run
          ? failedStep?.sql_state
            ? `SQLSTATE ${failedStep.sql_state}`
            : translateRunSummary(run.summary, lang)
          : t.summaryObservationPending,
      verdict: proof?.verdict ?? run?.verdict ?? t.summaryVerdictPending,
      verdictClass:
        proof?.verdict === "PROVEN_FIXED" || run?.verdict === "PROVEN_PASS"
          ? "is-pass"
          : run?.verdict === "PROVEN_FAIL"
          ? "is-fail"
          : "is-pending",
    };
  }, [lang, primaryProof, primaryRun, result, t]);

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

  async function runDemo() {
    setRepository(demoRepository);
    setPullRequest(demoPullRequest);
    await analyze(demoRepository, Number(demoPullRequest));
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
      {demoConfigured && (
        <section className="demo-launcher" aria-label={t.demoHint}>
          <button
            className="btn-live-demo"
            disabled={loading}
            onClick={runDemo}
            type="button"
          >
            {loading ? t.analyzingBtn : t.loadDemoBtn} <span>→</span>
          </button>
          <div>
            <strong>{t.demoHint}</strong>
            <code>{t.demoScenario}</code>
          </div>
        </section>
      )}

      {demoConfigured && <div className="or-divider"><span>{t.orDivider}</span></div>}

      <form className="analysis-card" onSubmit={submit}>
        <p className="manual-analysis-label">{t.manualAnalysisLabel}</p>
        <div className="field wide">
          <label htmlFor="repository">{t.repoLabel}</label>
          <input
            id="repository"
            onChange={(event) => setRepository(event.target.value)}
            placeholder={t.repoPlaceholder}
            required
            type="text"
            value={repository}
          />
        </div>
        <div className="field">
          <label htmlFor="pr">{t.prLabel}</label>
          <input
            id="pr"
            min="1"
            onChange={(event) => setPullRequest(event.target.value)}
            placeholder={t.prPlaceholder}
            required
            type="number"
            value={pullRequest}
          />
        </div>
        <button disabled={loading} type="submit">
          {loading ? t.analyzingBtn : t.analyzeBtn} <span>→</span>
        </button>
      </form>

      {error && (
        <p className="analysis-error" role="alert">
          {error}
        </p>
      )}
      {executionError && (
        <p className="analysis-error" role="alert">
          {executionError}
        </p>
      )}

      {result && (
        <section className="analysis-result" aria-label="Pull request analysis">
          {summary && (
            <section className="proof-summary" aria-label={t.proofSummaryEyebrow}>
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
                <li className="proof-node fact-node">
                  <small>{t.summaryDependencyLabel}</small>
                  <strong>{summary.dependency}</strong>
                </li>
                <li className="proof-arrow" aria-hidden="true">→</li>
                <li className={`proof-node observation-node ${summary.verdictClass}`}>
                  <small>{t.summaryObservationLabel}</small>
                  <strong>{summary.observation}</strong>
                </li>
                <li className="proof-arrow" aria-hidden="true">→</li>
                <li className={`proof-node verdict-node ${summary.verdictClass}`}>
                  <small>{t.summaryVerdictLabel}</small>
                  <strong>{summary.verdict}</strong>
                </li>
              </ol>
              {primaryProof && (
                <div className="proof-summary-invariants">
                  <span>CONTRACT {primaryProof.same_experiment ? "SAME" : "CHANGED"}</span>
                  <span>SUBJECT {primaryProof.subject_changed ? "CHANGED" : "SAME"}</span>
                </div>
              )}
              <p className="proof-scope">{t.scopeInvariant}</p>
              {primaryPlan && result.execution_allowed && result.controlled_fixture_id && (
                <div className="proof-summary-action">
                  {!primaryRun && (
                    <button
                      type="button"
                      className="btn-run-experiment"
                      disabled={executingPlanId === primaryPlan.id}
                      onClick={() => runExperiment(result.controlled_fixture_id!, primaryPlan.id)}
                    >
                      {executingPlanId === primaryPlan.id
                        ? t.runningExperimentBtn
                        : t.runExperimentBtn}
                    </button>
                  )}
                  {primaryRun?.verdict === "PROVEN_FAIL" && !primaryProof && (
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
            </section>
          )}

          <details className="result-details fact-details">
            <summary>{t.deterministicDetails}</summary>
          <div className="result-heading">
            <p className="eyebrow">{t.changeFactsEyebrow}</p>
            <h2>
              PR #{result.pull_request.number} — {result.pull_request.title}
            </h2>
          </div>
          <dl className="result-counts">
            <div>
              <dt>{t.changedFiles}</dt>
              <dd>{result.pull_request.changed_files}</dd>
            </div>
            <div>
              <dt>{t.sqlMigrations}</dt>
              <dd>{counts.sql}</dd>
            </div>
            <div>
              <dt>{t.appFiles}</dt>
              <dd>{counts.application}</dd>
            </div>
            <div>
              <dt>{t.dbChanges}</dt>
              <dd>{counts.changes}</dd>
            </div>
          </dl>
          <div className="change-list">
            {result.sql_files.map((file) => (
              <article key={file.path}>
                <code>{file.path}</code>
                {file.error && <p className="analysis-error">{file.error}</p>}
                {file.analysis?.changes.map((change, index) => (
                  <p key={`${change.operation}-${index}`}>
                    <strong>{change.operation}</strong>{" "}
                    {[change.table, change.column].filter(Boolean).join(".")}
                  </p>
                ))}
              </article>
            ))}
          </div>

          <hr className="section-divider" />

          {/* Impact Surface Section */}
          <div className="evidence-section" aria-label="Impact Surface">
            <div className="evidence-heading">
              <div>
                <p className="eyebrow">{t.impactEyebrow}</p>
                <h3>{t.impactHeading}</h3>
              </div>
              {result.impact_summary && !result.impact_summary.scan_complete && (
                <span className="badge badge-warning">{t.impactIncomplete}</span>
              )}
            </div>

            {result.impact_summary && (
              <dl className="result-counts">
                <div>
                  <dt>{t.targetEntities}</dt>
                  <dd>{result.impact_summary.targets}</dd>
                </div>
                <div>
                  <dt>{t.appFilesAffected}</dt>
                  <dd>{result.impact_summary.application_files_with_references}</dd>
                </div>
                <div>
                  <dt>{t.directReferences}</dt>
                  <dd>{result.impact_summary.qualified_references}</dd>
                </div>
                <div>
                  <dt>{t.potentialReferences}</dt>
                  <dd>
                    {result.impact_summary.contextual_references +
                      result.impact_summary.identifier_references}
                  </dd>
                </div>
              </dl>
            )}
          </div>

          {/* Dependency Evidence List */}
          <div className="evidence-section" aria-label="Dependency Evidence">
            <div className="evidence-heading">
              <div>
                <p className="eyebrow">{t.evidenceEyebrow}</p>
                <h3>{t.evidenceHeading}</h3>
              </div>
            </div>

            {result.dependency_evidence && result.dependency_evidence.length > 0 ? (
              <div className="evidence-list">
                {result.dependency_evidence.map((evidence) => {
                  const matchMeta = matchKindLabel(evidence.match_kind, t);
                  const targetLabel = [evidence.target.table, evidence.target.column]
                    .filter(Boolean)
                    .join(".");

                  return (
                    <article key={evidence.id} className="evidence-card">
                      <div className="evidence-meta">
                        <div className="evidence-path">
                          <strong>{evidence.path}</strong>:{evidence.line}
                        </div>
                        <div className="evidence-badges">
                          <span className="evidence-target">{targetLabel}</span>
                          <span className={matchMeta.className}>{matchMeta.label}</span>
                          {evidence.changed_in_pull_request ? (
                            <span className="badge badge-changed">{t.badgeChangedInPr}</span>
                          ) : (
                            <span className="badge badge-unchanged">{t.badgeNotChangedInPr}</span>
                          )}
                        </div>
                      </div>
                      <pre className="evidence-excerpt">
                        <code>{evidence.excerpt}</code>
                      </pre>
                    </article>
                  );
                })}
              </div>
            ) : (
              <div className="empty-state">
                {result.impact_summary?.scan_complete
                  ? t.noEvidenceComplete
                  : t.noEvidenceIncomplete}
              </div>
            )}
          </div>
          </details>

          {/* Failure Hypotheses & Executable Experiment Planning */}
          <details className="result-details hypothesis-details" open={!primaryRun}>
            <summary>{t.hypothesisDetails}</summary>
          <div className="evidence-section" aria-label="Failure Hypotheses">
            <div className="evidence-heading">
              <div>
                <p className="eyebrow">{t.hypothesesEyebrow}</p>
                <h3>{t.hypothesesHeading}</h3>
              </div>
              <span className="badge badge-unverified">{t.unverifiedProposal}</span>
            </div>

            {result.failure_hypotheses && result.failure_hypotheses.length > 0 ? (
              <div className="hypothesis-list">
                {result.failure_hypotheses.map((hypothesis) => {
                  const matchingPlan = result.experiment_plans?.find(
                    (p) => p.hypothesis_id === hypothesis.id,
                  );
                  const executionRun = matchingPlan ? experimentRuns[matchingPlan.id] : null;
                  const remediationProof = matchingPlan
                    ? remediationProofs[matchingPlan.id]
                    : null;
                  const translatedHypothesis = translateHypothesisContent(hypothesis, lang);

                  return (
                    <article key={hypothesis.id} className="hypothesis-card">
                      <div className="hypothesis-header">
                        <span className="badge badge-hypothesis">
                          {t.hypothesisBadge} {translateStatus(hypothesis.status, lang)}
                        </span>
                        <span className="hypothesis-category">
                          {translateCategory(hypothesis.category, lang)}
                        </span>
                      </div>
                      <h4>{translatedHypothesis.title}</h4>
                      <p className="hypothesis-statement">{translatedHypothesis.statement}</p>
                      <div className="hypothesis-meta">
                        <div>
                          <strong>{t.rationaleLabel}</strong> {translatedHypothesis.rationale}
                        </div>
                        <div>
                          <strong>{t.expectedFailureLabel}</strong>{" "}
                          <code>{translatedHypothesis.expected_failure_mode}</code>
                        </div>
                      </div>

                      {matchingPlan && (
                        <div className="plan-card">
                          <div className="plan-header">
                            <div>
                              <span className="badge badge-plan">
                                {t.proposedExperimentBadge}{" "}
                                {translateStatus(matchingPlan.status, lang)}
                              </span>
                              <h5>
                                {t.templateLabel}{" "}
                                {translateTemplate(matchingPlan.template, lang)}
                              </h5>
                            </div>
                            <span className="plan-status-notice">
                              {executionRun ? t.executedInSandbox : t.notExecutedYet}
                            </span>
                          </div>
                          <p className="plan-observation">
                            <strong>{t.expectedObservationLabel}</strong>{" "}
                            {translateObservation(matchingPlan.expected_observation, lang)}
                          </p>
                          <details className="experiment-details">
                            <summary>{t.experimentDetails}</summary>
                          <ol className="plan-steps">
                            {matchingPlan.steps.map((step) => (
                              <li key={step.order}>
                                <span className="step-desc">
                                  {translateStepDescription(step.description, lang)}
                                </span>
                                {step.sql && <code className="step-sql">{step.sql}</code>}
                              </li>
                            ))}
                          </ol>
                          </details>

                          {/* Phase 6: Run experiment action or generic limit notice */}
                          {!executionRun && matchingPlan.id !== primaryPlan?.id && (
                            <div>
                              {result.execution_allowed && result.controlled_fixture_id ? (
                                <button
                                  type="button"
                                  className="btn-run-experiment"
                                  disabled={executingPlanId === matchingPlan.id}
                                  onClick={() =>
                                    runExperiment(
                                      result.controlled_fixture_id!,
                                      matchingPlan.id,
                                    )
                                  }
                                >
                                  {executingPlanId === matchingPlan.id
                                    ? t.runningExperimentBtn
                                    : t.runExperimentBtn}
                                </button>
                              ) : (
                                <p className="sandbox-limited-notice">
                                  {result.execution_notice || t.sandboxNoticeDefault}
                                </p>
                              )}
                            </div>
                          )}

                          {/* Phase 6: Observed PostgreSQL Result */}
                          {executionRun && (
                            <div className="execution-run-card" aria-label="Observed Result">
                              <div className="run-header">
                                <div>
                                  <span
                                    className={`badge ${
                                      executionRun.verdict === "PROVEN_FAIL"
                                        ? "badge-fail"
                                        : executionRun.verdict === "PROVEN_PASS"
                                          ? "badge-pass"
                                          : executionRun.verdict === "EXECUTION_ERROR"
                                            ? "badge-error"
                                            : "badge-inconclusive"
                                    }`}
                                  >
                                    {executionRun.verdict === "PROVEN_FAIL"
                                      ? t.reproducedFailBadge
                                      : executionRun.verdict === "PROVEN_PASS"
                                        ? t.notReproducedPassBadge
                                        : executionRun.verdict}
                                  </span>
                                </div>
                              </div>

                              <div
                                className={`run-headline ${
                                  executionRun.verdict === "PROVEN_FAIL"
                                    ? "proven-fail"
                                    : executionRun.verdict === "PROVEN_PASS"
                                      ? "proven-pass"
                                      : ""
                                }`}
                              >
                                {executionRun.verdict === "PROVEN_FAIL"
                                  ? t.reproducedFailHeadline
                                  : executionRun.verdict === "PROVEN_PASS"
                                    ? t.notReproducedPassHeadline
                                    : t.inconclusiveHeadline}
                              </div>

                              <p className="run-summary">
                                {translateRunSummary(executionRun.summary, lang)}
                                {executionRun.verdict === "PROVEN_PASS" && (
                                  <span className="run-subnote">{t.passSubnote}</span>
                                )}
                              </p>

                              <ul className="step-results-list">
                                {executionRun.step_results.map((step) => (
                                  <li
                                    key={step.order}
                                    className={`step-result-item status-${step.status.toLowerCase()}`}
                                  >
                                    <div>
                                      <strong>
                                        {t.stepLabel} {step.order}:
                                      </strong>{" "}
                                      {translateStepType(step.type, lang)}
                                    </div>
                                    <div>
                                      <span>{translateStepStatus(step.status, lang)}</span> ({step.duration_ms}ms)
                                    </div>
                                    {step.status === "FAILED" && (
                                      <div className="step-error-detail">
                                        SQLSTATE: {step.sql_state ?? "N/A"} • {step.message}
                                      </div>
                                    )}
                                  </li>
                                ))}
                              </ul>

                              <div className="plan-digest-footer">
                                {t.experimentContractLabel}{" "}
                                <code>{executionRun.experiment_contract_digest}</code>
                                <br />
                                {t.subjectLabel} <code>{executionRun.subject_digest}</code>
                                <br />
                                {t.cleanupLabel}{" "}
                                {executionRun.cleanup_succeeded === true
                                  ? t.cleanupSucceeded
                                  : executionRun.cleanup_succeeded === false
                                    ? t.cleanupFailed
                                    : t.cleanupUnknown}
                              </div>
                            </div>
                          )}

                          {executionRun &&
                            result.execution_allowed &&
                            result.controlled_fixture_id && (
                              <div className="remediation-card" aria-label="Remediation">
                                <p className="eyebrow">{t.remediationEyebrow}</p>
                                {executionRun.verdict === "PROVEN_PASS" ? (
                                  <p>{t.noRemediationNeeded}</p>
                                ) : executionRun.verdict === "PROVEN_FAIL" ? (
                                  <>
                                    <h5>{t.remediationHeading}</h5>
                                    <p>{t.remediationDesc}</p>
                                    {!remediationProof && matchingPlan.id !== primaryPlan?.id && (
                                      <button
                                        type="button"
                                        className="btn-run-experiment"
                                        disabled={provingPlanId === matchingPlan.id}
                                        onClick={() =>
                                          verifyRemediation(
                                            result.controlled_fixture_id!,
                                            matchingPlan.id,
                                          )
                                        }
                                      >
                                        {provingPlanId === matchingPlan.id
                                          ? t.verifyingRemediationBtn
                                          : t.verifyRemediationBtn}
                                      </button>
                                    )}
                                  </>
                                ) : (
                                  <p>{t.remediationRequiresFailure}</p>
                                )}

                                {remediationProof && (
                                  <div
                                    className="remediation-proof"
                                    aria-label="Remediation Proof"
                                  >
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
                                    <div className="proof-comparison">
                                      <div className="proof-before">
                                        <strong>{t.beforeLabel}</strong>
                                        <span>{remediationProof.before.verdict.replace("_", " ")}</span>
                                        <code>
                                          SQLSTATE{" "}
                                          {remediationProof.before.step_results.find(
                                            (step) => step.sql_state,
                                          )?.sql_state ?? "N/A"}
                                        </code>
                                      </div>
                                      <div className="proof-contract">
                                        <strong>{t.sameExperimentLabel}</strong>
                                        <span>
                                          CONTRACT {remediationProof.same_experiment ? "SAME" : "CHANGED"}
                                        </span>
                                        <span>
                                          SUBJECT {remediationProof.subject_changed ? "CHANGED" : "SAME"}
                                        </span>
                                        <span>
                                          {t.contractLabel}{" "}
                                          {remediationProof.experiment_contract_digest.slice(0, 20)}
                                          ...
                                        </span>
                                      </div>
                                      <div className="proof-after">
                                        <strong>{t.afterLabel}</strong>
                                        <span>{remediationProof.after.verdict.replace("_", " ")}</span>
                                      </div>
                                    </div>
                                    <p className="proof-invariants">
                                      {t.invariantSameExp}{" "}
                                      {remediationProof.same_experiment ? t.yes : t.no} ·{" "}
                                      {t.invariantSubjectChanged}{" "}
                                      {remediationProof.subject_changed ? t.yes : t.no}
                                    </p>
                                    <p className="proof-demo-message">{remediationProof.summary}</p>
                                    <p className="run-subnote">{remediationProof.scope_notice}</p>
                                  </div>
                                )}
                              </div>
                            )}
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
    </>
  );
}
