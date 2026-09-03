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
      </form>

      {error && <p className="analysis-error" role="alert">{error}</p>}

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
              <span className="badge badge-unverified">NOT EXECUTED YET</span>
            </div>

            {result.failure_hypotheses && result.failure_hypotheses.length > 0 ? (
              <div className="hypothesis-list">
                {result.failure_hypotheses.map((hypothesis) => {
                  const matchingPlan = result.experiment_plans?.find(
                    (p) => p.hypothesis_id === hypothesis.id,
                  );

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
                            <span className="plan-status-notice">Not executed yet</span>
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
