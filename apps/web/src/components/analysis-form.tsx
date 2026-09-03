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
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
        </section>
      )}
    </>
  );
}
