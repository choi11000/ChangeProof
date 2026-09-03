import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import Home from "./page";

describe("Home", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders the pull request analysis form", () => {
    render(<Home />);

    expect(screen.getByRole("heading", { name: /prove a change is safe/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/github repository/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /analyze change/i })).toBeInTheDocument();
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
    render(<Home />);

    fireEvent.change(screen.getByLabelText(/github repository/i), {
      target: { value: "acme/risky-saas" },
    });
    fireEvent.change(screen.getByLabelText(/pull request/i), { target: { value: "42" } });
    fireEvent.click(screen.getByRole("button", { name: /analyze change/i }));

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
    render(<Home />);

    fireEvent.change(screen.getByLabelText(/github repository/i), {
      target: { value: "acme/risky-saas" },
    });
    fireEvent.change(screen.getByLabelText(/pull request/i), { target: { value: "42" } });
    fireEvent.click(screen.getByRole("button", { name: /analyze change/i }));

    await waitFor(() =>
      expect(screen.getByText("Cross-Layer Application References")).toBeInTheDocument(),
    );
    expect(screen.getByText("Direct Reference")).toBeInTheDocument();
    expect(screen.getByText("Not changed in this PR")).toBeInTheDocument();
    expect(screen.getByText("app/order_service.py")).toBeInTheDocument();
    expect(
      screen.getByText("return {'id': order.id, 'status': order.legacy_status}"),
    ).toBeInTheDocument();
  });

  it("renders failure hypothesis with notice when execution is limited", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          pull_request: {
            number: 42,
            title: "Drop legacy status",
            changed_files: 1,
            html_url: "https://github.com/generic/repo/pull/42",
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
              assumptions: ["orders table exists"],
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
              ],
              expected_observation: "Query execution fails",
              status: "NOT_EXECUTED",
            },
          ],
          execution_allowed: false,
          warnings: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<Home />);

    fireEvent.change(screen.getByLabelText(/github repository/i), {
      target: { value: "generic/repo" },
    });
    fireEvent.change(screen.getByLabelText(/pull request/i), { target: { value: "42" } });
    fireEvent.click(screen.getByRole("button", { name: /analyze change/i }));

    await waitFor(() =>
      expect(screen.getByText("Evidence-Grounded AI Reasoning")).toBeInTheDocument(),
    );
    expect(screen.getByText(/sandbox execution is limited/i)).toBeInTheDocument();
  });

  it("runs experiment on controlled fixture and renders PROVEN_FAIL observation", async () => {
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
            plan_digest: "a1b2c3d4e5f67890",
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

    render(<Home />);

    fireEvent.change(screen.getByLabelText(/github repository/i), {
      target: { value: "acme/risky-saas" },
    });
    fireEvent.change(screen.getByLabelText(/pull request/i), { target: { value: "42" } });
    fireEvent.click(screen.getByRole("button", { name: /analyze change/i }));

    // Run experiment button appears
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /run experiment in isolated postgresql/i }),
      ).toBeInTheDocument(),
    );

    fireEvent.click(
      screen.getByRole("button", { name: /run experiment in isolated postgresql/i }),
    );

    // Observed result rendered
    await waitFor(() =>
      expect(screen.getByText("Failure reproduced in isolated PostgreSQL.")).toBeInTheDocument(),
    );
    expect(screen.getByText("REPRODUCED • PROVEN FAIL")).toBeInTheDocument();
    expect(screen.getByText(/SQLSTATE: 42703/)).toBeInTheDocument();
    expect(screen.getByText(/a1b2c3d4e5f67890/)).toBeInTheDocument();
  });
});
