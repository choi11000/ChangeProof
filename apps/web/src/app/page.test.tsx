import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider, translations } from "@/lib/i18n";
import Home from "./page";

function renderHome() {
  return render(
    <I18nProvider>
      <Home />
    </I18nProvider>,
  );
}

describe("Home", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    localStorage.clear();
  });

  it("renders the pull request analysis form in Korean by default", () => {
    renderHome();

    expect(screen.getByRole("heading", { name: /배포 전에 실패를 직접 재현하세요/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/github 저장소/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /변경사항 분석/i })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: /3단계 증명 흐름/i })).toHaveTextContent(
      /변경사항 분석/i,
    );
    expect(screen.queryByRole("button", { name: /live demo 실행하기/i })).not.toBeInTheDocument();
  });

  it("switches language between Korean and English when language button is clicked", () => {
    renderHome();

    // Default is Korean
    expect(screen.getByRole("heading", { name: /배포 전에 실패를 직접 재현하세요/i })).toBeInTheDocument();

    // Switch to English
    fireEvent.click(screen.getByRole("button", { name: "English" }));
    expect(screen.getByRole("heading", { name: /reproduce the failure before it ships/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /analyze change/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/github repository/i)).toBeInTheDocument();

    // Switch back to Korean
    fireEvent.click(screen.getByRole("button", { name: "한국어" }));
    expect(screen.getByRole("heading", { name: /배포 전에 실패를 직접 재현하세요/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /변경사항 분석/i })).toBeInTheDocument();
  });

  it("starts analysis immediately with configured demo values", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEMO_REPOSITORY", "demo/public-repo");
    vi.stubEnv("NEXT_PUBLIC_DEMO_PR", "17");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          pull_request: { number: 17, title: "Demo failure", changed_files: 0, html_url: "" },
          changed_files: [],
          sql_files: [],
          dependency_targets: [],
          dependency_evidence: [],
          impact_summary: null,
          warnings: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    renderHome();

    fireEvent.click(screen.getByRole("button", { name: /live demo 실행하기/i }));

    expect(screen.getByLabelText(/github 저장소/i)).toHaveValue("demo/public-repo");
    expect(screen.getByLabelText(/풀 리퀘스트/i)).toHaveValue(17);
    await waitFor(() => expect(screen.getByText(/PR #17/i)).toBeInTheDocument());
    expect(screen.getByText("이 실험에서 확인된 결론")).toBeInTheDocument();
    expect(
      screen.getByText(
        "이 증명은 해당 통제 실험에만 적용되며, 전체 PR이나 프로덕션 시스템의 안전성을 의미하지 않습니다.",
      ),
    ).toBeInTheDocument();
    expect(translations.en.scopeInvariant).toBe(
      "This proof applies to this controlled experiment, not to the entire pull request or production system.",
    );
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/analyses/github-pr"),
      expect.objectContaining({
        body: JSON.stringify({ repository: "demo/public-repo", pull_request: 17 }),
      }),
    );
  });

  it("submits a PR and renders deterministic change facts", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          pull_request: {
            number: 42,
            title: "Drop legacy status",
            changed_files: 2,
            html_url: "https://github.com/acme/risky-saas/pull/42",
          },
          changed_files: [
            { category: "SQL_MIGRATION", reason: "migration", file: { path: "migrations/001.sql" } },
            { category: "APPLICATION", reason: "source", file: { path: "app/order.py" } },
          ],
          sql_files: [
            {
              path: "migrations/001.sql",
              error: null,
              analysis: {
                changes: [{ operation: "DROP_COLUMN", table: "orders", column: "legacy_status" }],
              },
            },
          ],
          dependency_targets: [],
          dependency_evidence: [],
          impact_summary: null,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    renderHome();

    fireEvent.change(screen.getByLabelText(/github 저장소/i), {
      target: { value: "acme/risky-saas" },
    });
    fireEvent.change(screen.getByLabelText(/풀 리퀘스트/i), { target: { value: "42" } });
    fireEvent.click(screen.getByRole("button", { name: /변경사항 분석/i }));

    await waitFor(() => expect(screen.getByText("DROP_COLUMN")).toBeInTheDocument());
    expect(screen.getAllByText("orders.legacy_status").length).toBeGreaterThan(0);
  });

  it("renders impact surface and dependency evidence with unchanged PR status", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          pull_request: {
            number: 42,
            title: "Drop legacy status",
            changed_files: 1,
            html_url: "https://github.com/acme/risky-saas/pull/42",
          },
          changed_files: [
            { category: "SQL_MIGRATION", reason: "migration", file: { path: "migrations/001.sql" } },
          ],
          sql_files: [
            {
              path: "migrations/001.sql",
              error: null,
              analysis: {
                changes: [{ operation: "DROP_COLUMN", table: "orders", column: "legacy_status" }],
              },
            },
          ],
          dependency_targets: [
            { type: "COLUMN", table: "orders", column: "legacy_status" },
          ],
          dependency_evidence: [
            {
              id: "ev_1",
              target: { type: "COLUMN", table: "orders", column: "legacy_status" },
              path: "app/order_service.py",
              line: 11,
              match_kind: "QUALIFIED_REFERENCE",
              excerpt: "return {'id': order.id, 'status': order.legacy_status}",
              source_scope: "APPLICATION",
              changed_in_pull_request: false,
            },
          ],
          impact_summary: {
            targets: 1,
            application_files_with_references: 1,
            test_files_with_references: 0,
            qualified_references: 1,
            contextual_references: 0,
            identifier_references: 0,
            scan_complete: true,
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    renderHome();

    fireEvent.change(screen.getByLabelText(/github 저장소/i), {
      target: { value: "acme/risky-saas" },
    });
    fireEvent.change(screen.getByLabelText(/풀 리퀘스트/i), { target: { value: "42" } });
    fireEvent.click(screen.getByRole("button", { name: /변경사항 분석/i }));

    await waitFor(() =>
      expect(screen.getByText("크로스 레이어 애플리케이션 참조")).toBeInTheDocument(),
    );
    expect(screen.getAllByText("직접 참조").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("이번 PR에서 변경되지 않음")).toBeInTheDocument();
    expect(screen.getByText("app/order_service.py")).toBeInTheDocument();
    expect(
      screen.getByText("return {'id': order.id, 'status': order.legacy_status}"),
    ).toBeInTheDocument();
  });

  it("runs experiment on controlled fixture and renders PROVEN_FAIL observation and remediation", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    // 1. First fetch for PR analysis
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          pull_request: {
            number: 42,
            title: "Drop legacy status",
            changed_files: 1,
            html_url: "https://github.com/acme/risky-saas/pull/42",
          },
          changed_files: [],
          sql_files: [],
          dependency_targets: [],
          dependency_evidence: [],
          impact_summary: null,
          failure_hypotheses: [
            {
              id: "hyp_001",
              category: "SCHEMA_CONTRACT_BREAK",
              title: "Dropped column remains referenced",
              statement: "Application references orders.legacy_status after migration",
              change_ids: ["c1"],
              evidence_ids: ["e1"],
              rationale: "order_service.py:11 references dropped column",
              expected_failure_mode: "UndefinedColumn",
              assumptions: [],
              experiment_template: "DROPPED_COLUMN_REFERENCE",
              status: "UNVERIFIED",
            },
          ],
          experiment_plans: [
            {
              id: "plan_001",
              hypothesis_id: "hyp_001",
              template: "DROPPED_COLUMN_REFERENCE",
              change_ids: ["c1"],
              evidence_ids: ["e1"],
              steps: [
                {
                  order: 1,
                  type: "PREPARE_DATABASE",
                  description: "Provision isolated PostgreSQL database instance",
                  sql: null,
                },
                {
                  order: 5,
                  type: "RUN_READ_QUERY",
                  description: 'Execute query against removed column "legacy_status"',
                  sql: 'SELECT "legacy_status" FROM "orders" LIMIT 1;',
                },
              ],
              expected_observation: "Query execution is expected to fail with undefined column",
              status: "NOT_EXECUTED",
              plan_digest: "a1b2c3d4e5f67890",
            },
          ],
          execution_allowed: true,
          controlled_fixture_id: "risky-saas/drop-legacy-status",
          warnings: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    // 2. Second fetch for experiment execution
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          run: {
            id: "run_001",
            experiment_plan_id: "plan_001",
            experiment_contract_digest: "contract_a1b2c3d4e5f67890",
            subject_digest: "subject_a1b2c3d4e5f67890",
            cleanup_succeeded: true,
            template: "DROPPED_COLUMN_REFERENCE",
            verdict: "PROVEN_FAIL",
            started_at: "2026-09-03T00:00:00Z",
            finished_at: "2026-09-03T00:00:01Z",
            step_results: [
              {
                order: 1,
                type: "PREPARE_DATABASE",
                status: "PASSED",
                duration_ms: 5,
              },
              {
                order: 5,
                type: "RUN_READ_QUERY",
                status: "FAILED",
                duration_ms: 8,
                sql_state: "42703",
                message: 'column "legacy_status" does not exist',
              },
            ],
            summary: "Failure reproduced in isolated PostgreSQL: Column is removed by migration and referenced query failed with SQLSTATE 42703 (undefined_column).",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    // 3. Authoritative remediation proof response
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          proof: {
            id: "proof_001",
            fixture_id: "risky-saas/drop-legacy-status",
            remediation_id: "remediation/risky-saas/preserve-legacy-status",
            strategy: "PRESERVE_COLUMN_COMPATIBILITY",
            description: "Preserve legacy_status during the compatibility window while adding status.",
            experiment_contract_digest: "contract_a1b2c3d4e5f67890",
            before: {
              id: "run_before",
              experiment_plan_id: "plan_001",
              experiment_contract_digest: "contract_a1b2c3d4e5f67890",
              subject_digest: "subject_before",
              cleanup_succeeded: true,
              template: "DROPPED_COLUMN_REFERENCE",
              verdict: "PROVEN_FAIL",
              started_at: "2026-09-03T00:00:00Z",
              finished_at: "2026-09-03T00:00:01Z",
              step_results: [{ order: 5, type: "RUN_READ_QUERY", status: "FAILED", duration_ms: 1, sql_state: "42703" }],
              summary: "Failure reproduced.",
            },
            after: {
              id: "run_after",
              experiment_plan_id: "plan_001",
              experiment_contract_digest: "contract_a1b2c3d4e5f67890",
              subject_digest: "subject_after",
              cleanup_succeeded: true,
              template: "DROPPED_COLUMN_REFERENCE",
              verdict: "PROVEN_PASS",
              started_at: "2026-09-03T00:00:01Z",
              finished_at: "2026-09-03T00:00:02Z",
              step_results: [],
              summary: "Verification passed.",
            },
            verdict: "PROVEN_FIXED",
            same_experiment: true,
            subject_changed: true,
            summary: "Failure reproduced before remediation. The same experiment passed after remediation.",
            scope_notice: "This proof applies to this controlled experiment, not to the entire pull request or production system.",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    renderHome();

    fireEvent.change(screen.getByLabelText(/github 저장소/i), {
      target: { value: "acme/risky-saas" },
    });
    fireEvent.change(screen.getByLabelText(/풀 리퀘스트/i), { target: { value: "42" } });
    fireEvent.click(screen.getByRole("button", { name: /변경사항 분석/i }));

    // Verify translated hypothesis and plan in Korean
    await waitFor(() =>
      expect(
        screen.getByText(/삭제된 컬럼이 애플리케이션 코드에 여전히 참조되고 있음/i),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText(/스키마 계약 위반/i)).toBeInTheDocument();
    expect(screen.getByText(/삭제된 컬럼 참조 검증/i)).toBeInTheDocument();

    // Run experiment button appears in Korean
    expect(
      screen.getByRole("button", { name: /격리된 postgresql에서 실험 실행/i }),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: /격리된 postgresql에서 실험 실행/i }),
    );

    // Observed result rendered
    await waitFor(() =>
      expect(screen.getByText("격리된 PostgreSQL에서 장애가 재현되었습니다.")).toBeInTheDocument(),
    );
    expect(screen.getByText("재현 완료 • PROVEN FAIL")).toBeInTheDocument();
    expect(screen.getByText(/SQLSTATE: 42703/)).toBeInTheDocument();
    expect(screen.getByText("contract_a1b2c3d4e5f67890")).toBeInTheDocument();
    expect(screen.getByText("subject_a1b2c3d4e5f67890")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /복구 검증/i }));
    await waitFor(() => expect(screen.getByText("PROVEN FIXED")).toBeInTheDocument());
    expect(fetchSpy.mock.calls[2]?.[0]).toBe(
      "http://localhost:8000/api/v1/proofs/remediation",
    );
    const remediationRequest = JSON.parse(
      fetchSpy.mock.calls[2]?.[1]?.body as string,
    ) as Record<string, unknown>;
    expect(remediationRequest).toEqual({
      fixture_id: "risky-saas/drop-legacy-status",
    });
    expect(remediationRequest).not.toHaveProperty("experiment_plan_id");
    expect(screen.getByText("PROVEN_FIXED")).toBeInTheDocument();
    expect(screen.getByText("FAIL → PASS")).toBeInTheDocument();
    expect(screen.getByText(/동일 실험: 예/i)).toBeInTheDocument();
    expect(screen.getByText(/대상 변경: 예/i)).toBeInTheDocument();
  });
});
