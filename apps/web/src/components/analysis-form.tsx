"use client";

import { FormEvent, useMemo, useState } from "react";

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
  status: "UNVERIFIED" | "PROPOSED";
};

type ExperimentStep = {
  order: number;
  type: string;
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
  status: "NOT_EXECUTED" | "PLANNED";
  plan_digest?: string | null;
};

type ExperimentVerdict =
  | "PROVEN_FAIL"
  | "PROVEN_PASS"
  | "INCONCLUSIVE"
  | "EXECUTION_ERROR";

type ExperimentStepStatus =
  | "PENDING"
  | "RUNNING"
  | "PASSED"
  | "FAILED"
  | "SKIPPED";

type ExperimentStepResult = {
  order: number;
  type: string;
  status: ExperimentStepStatus;
  duration_ms: number;
  sql_state?: string | null;
  error_type?: string | null;
  message?: string | null;
  scalar_value?: string | number | boolean | null;
  row_count?: number | null;
};

type ExperimentRun = {
  id: string;
  experiment_plan_id: string;
  experiment_contract_digest: string;
  subject_digest: string;
  template: ExperimentTemplate;
  verdict: ExperimentVerdict;
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

function matchKindLabel(kind: DependencyMatchKind): { label: string; className: string } {
  switch (kind) {
    case "QUALIFIED_REFERENCE":
      return { label: "Direct Reference", className: "badge badge-direct" };
    case "TABLE_AND_COLUMN_CONTEXT":
      return { label: "Table Context", className: "badge badge-context" };
    case "COLUMN_IDENTIFIER":
      return { label: "Potential Identifier", className: "badge badge-potential" };
    case "TABLE_IDENTIFIER":
      return { label: "Table Identifier", className: "badge badge-direct" };
    default:
      return { label: kind, className: "badge" };
  }
}

export function AnalysisForm() {
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
      changes:
        result?.sql_files.reduce(
          (total, item) => total + (item.analysis?.changes.length ?? 0),
          0,
        ) ?? 0,
    };
  }, [result]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
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
          repository,
          pull_request: Number(pullRequest),
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
        throw new Error(body.detail ?? "Experiment sandbox execution failed");
      }
      setExperimentRuns((prev) => ({ ...prev, [planId]: body.run }));
    } catch (err) {
      setExecutionError(err instanceof Error ? err.message : "Experiment execution failed");
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
        body: JSON.stringify({ fixture_id: fixtureId }),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.detail ?? "Remediation proof failed");
      }
      setRemediationProofs((previous) => ({ ...previous, [planId]: body.proof }));
    } catch (requestError) {
      setExecutionError(
        requestError instanceof Error ? requestError.message : "Remediation proof failed",
      );
    } finally {
      setProvingPlanId(null);
    }
  }

  return (
    <>
      <form className="analysis-card" onSubmit={submit}>
        <div className="field wide">
          <label htmlFor="repository">GitHub repository</label>
          <input
            id="repository"
            onChange={(event) => setRepository(event.target.value)}
            placeholder="https://github.com/acme/risky-saas"
            required
            type="text"
            value={repository}
          />
        </div>
        <div className="field">
          <label htmlFor="pr">Pull request</label>
          <input
            id="pr"
            min="1"
            onChange={(event) => setPullRequest(event.target.value)}
            placeholder="42"
            required
            type="number"
            value={pullRequest}
          />
        </div>
        <button disabled={loading} type="submit">
          {loading ? "Analyzing…" : "Analyze change"} <span>→</span>
        </button>
        {demoConfigured && (
          <div className="demo-load-group">
            <button
              className="btn-load-demo"
              disabled={loading}
              onClick={() => {
                setRepository(demoRepository);
                setPullRequest(demoPullRequest);
              }}
              type="button"
            >
              Load demo PR
            </button>
            <span className="demo-hint">Try prepared risky SaaS migration</span>
          </div>
        )}
      </form>

      {error && <p className="analysis-error" role="alert">{error}</p>}
      {executionError && <p className="analysis-error" role="alert">{executionError}</p>}

      {result && (
        <section className="analysis-result" aria-label="Pull request analysis">
          <div className="result-heading">
            <p className="eyebrow">STRUCTURED CHANGE FACTS</p>
            <h2>PR #{result.pull_request.number} — {result.pull_request.title}</h2>
          </div>
          <dl className="result-counts">
            <div><dt>Changed files</dt><dd>{result.pull_request.changed_files}</dd></div>
            <div><dt>SQL migrations</dt><dd>{counts.sql}</dd></div>
            <div><dt>Application files</dt><dd>{counts.application}</dd></div>
            <div><dt>DB changes</dt><dd>{counts.changes}</dd></div>
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
                <p className="eyebrow">IMPACT SURFACE</p>
                <h3>Cross-Layer Application References</h3>
              </div>
              {result.impact_summary && !result.impact_summary.scan_complete && (
                <span className="badge badge-warning">
                  Limited Scan (Incomplete)
                </span>
              )}
            </div>

            {result.impact_summary && (
              <dl className="result-counts">
                <div>
                  <dt>Target entities</dt>
                  <dd>{result.impact_summary.targets}</dd>
                </div>
                <div>
                  <dt>App files affected</dt>
                  <dd>{result.impact_summary.application_files_with_references}</dd>
                </div>
                <div>
                  <dt>Direct references</dt>
                  <dd>{result.impact_summary.qualified_references}</dd>
                </div>
                <div>
                  <dt>Potential references</dt>
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
                <p className="eyebrow">DEPENDENCY EVIDENCE</p>
                <h3>Deterministic Source Code Matches</h3>
              </div>
            </div>

            {result.dependency_evidence && result.dependency_evidence.length > 0 ? (
              <div className="evidence-list">
                {result.dependency_evidence.map((evidence) => {
                  const matchMeta = matchKindLabel(evidence.match_kind);
                  const targetLabel = [
                    evidence.target.table,
                    evidence.target.column,
                  ]
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
                            <span className="badge badge-changed">Changed in this PR</span>
                          ) : (
                            <span className="badge badge-unchanged">Not changed in this PR</span>
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
                  ? "No source references found in scanned application files."
                  : "No references found in scanned subset. Source analysis was limited."}
              </div>
            )}
          </div>

          <hr className="section-divider" />

          {/* Failure Hypotheses & Executable Experiment Planning */}
          <div className="evidence-section" aria-label="Failure Hypotheses">
            <div className="evidence-heading">
              <div>
                <p className="eyebrow">FAILURE HYPOTHESES &amp; EXPERIMENT PLANNING</p>
                <h3>Evidence-Grounded AI Reasoning</h3>
              </div>
              <span className="badge badge-unverified">UNVERIFIED PROPOSAL</span>
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

                  return (
                    <article key={hypothesis.id} className="hypothesis-card">
                      <div className="hypothesis-header">
                        <span className="badge badge-hypothesis">HYPOTHESIS • {hypothesis.status}</span>
                        <span className="hypothesis-category">{hypothesis.category}</span>
                      </div>
                      <h4>{hypothesis.title}</h4>
                      <p className="hypothesis-statement">{hypothesis.statement}</p>
                      <div className="hypothesis-meta">
                        <div>
                          <strong>Rationale:</strong> {hypothesis.rationale}
                        </div>
                        <div>
                          <strong>Expected Failure:</strong> <code>{hypothesis.expected_failure_mode}</code>
                        </div>
                      </div>

                      {matchingPlan && (
                        <div className="plan-card">
                          <div className="plan-header">
                            <div>
                              <span className="badge badge-plan">
                                PROPOSED EXPERIMENT • {matchingPlan.status}
                              </span>
                              <h5>Template: {matchingPlan.template}</h5>
                            </div>
                            <span className="plan-status-notice">
                              {executionRun ? "Executed in sandbox" : "Not executed yet"}
                            </span>
                          </div>
                          <p className="plan-observation">
                            <strong>Expected observation:</strong> {matchingPlan.expected_observation}
                          </p>
                          <ol className="plan-steps">
                            {matchingPlan.steps.map((step) => (
                              <li key={step.order}>
                                <span className="step-desc">{step.description}</span>
                                {step.sql && <code className="step-sql">{step.sql}</code>}
                              </li>
                            ))}
                          </ol>

                          {/* Phase 6: Run experiment action or generic limit notice */}
                          {!executionRun && (
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
                                    ? "Reproducing failure in PostgreSQL..."
                                    : "Run experiment in isolated PostgreSQL →"}
                                </button>
                              ) : (
                                <p className="sandbox-limited-notice">
                                  {result.execution_notice ||
                                    "Sandbox execution is limited to controlled demo fixtures in this MVP."}
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
                                      ? "REPRODUCED • PROVEN FAIL"
                                      : executionRun.verdict === "PROVEN_PASS"
                                        ? "NOT REPRODUCED • PROVEN PASS"
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
                                  ? "Failure reproduced in isolated PostgreSQL."
                                  : executionRun.verdict === "PROVEN_PASS"
                                    ? "This experiment completed without the expected failure."
                                    : "Experiment executed with non-conclusive observations."}
                              </div>

                              <p className="run-summary">
                                {executionRun.summary}
                                {executionRun.verdict === "PROVEN_PASS" && (
                                  <span className="run-subnote">
                                    This verdict applies only to this experiment, not to the entire pull request.
                                  </span>
                                )}
                              </p>

                              <ul className="step-results-list">
                                {executionRun.step_results.map((step) => (
                                  <li
                                    key={step.order}
                                    className={`step-result-item status-${step.status.toLowerCase()}`}
                                  >
                                    <div>
                                      <strong>Step {step.order}:</strong> {step.type}
                                    </div>
                                    <div>
                                      <span>{step.status}</span> ({step.duration_ms}ms)
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
                                Experiment Contract: <code>{executionRun.experiment_contract_digest}</code>
                                <br />
                                Subject: <code>{executionRun.subject_digest}</code>
                                <br />
                                Cleanup: {executionRun.cleanup_succeeded === true ? "SUCCEEDED" : executionRun.cleanup_succeeded === false ? "FAILED" : "UNKNOWN"}
                              </div>
                            </div>
                          )}

                          {executionRun && result.execution_allowed && result.controlled_fixture_id && (
                            <div className="remediation-card" aria-label="Remediation">
                              <p className="eyebrow">REMEDIATION</p>
                              {executionRun.verdict === "PROVEN_PASS" ? (
                                <p>No remediation required for this experiment.</p>
                              ) : executionRun.verdict === "PROVEN_FAIL" ? (
                                <>
                                  <h5>Deterministic compatibility remediation</h5>
                                  <p>
                                    This allowlisted remediation will be validated against the same experiment.
                                  </p>
                                  {!remediationProof && (
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
                                        ? "Running authoritative before and after experiments..."
                                        : "Verify remediation →"}
                                    </button>
                                  )}
                                </>
                              ) : (
                                <p>Remediation verification requires a conclusive reproduced failure.</p>
                              )}

                              {remediationProof && (
                                <div className="remediation-proof" aria-label="Remediation Proof">
                                  <span className={`badge ${remediationProof.verdict === "PROVEN_FIXED" ? "badge-pass" : "badge-inconclusive"}`}>
                                    {remediationProof.verdict.replace("_", " ")}
                                  </span>
                                  <h5>{remediationProof.description}</h5>
                                  <div className="proof-comparison">
                                    <div>
                                      <strong>Before</strong>
                                      <span>{remediationProof.before.verdict.replace("_", " ")}</span>
                                      <code>
                                        SQLSTATE {remediationProof.before.step_results.find((step) => step.sql_state)?.sql_state ?? "N/A"}
                                      </code>
                                    </div>
                                    <div>
                                      <strong>Same experiment</strong>
                                      <span>Contract: {remediationProof.experiment_contract_digest.slice(0, 20)}...</span>
                                    </div>
                                    <div>
                                      <strong>After</strong>
                                      <span>{remediationProof.after.verdict.replace("_", " ")}</span>
                                    </div>
                                  </div>
                                  <p className="proof-invariants">
                                    Same experiment: {remediationProof.same_experiment ? "YES" : "NO"} · Subject changed: {remediationProof.subject_changed ? "YES" : "NO"}
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
              <div className="empty-state">
                No evidence-grounded failure hypothesis generated for this change.
              </div>
            )}
          </div>
        </section>
      )}
    </>
  );
}
