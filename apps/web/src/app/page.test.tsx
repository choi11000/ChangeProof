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

  it("renders failure hypothesis and proposed experiment plan with unverified status", async () => {
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
                {
                  order: 5,
                  type: "RUN_READ_QUERY",
                  description: 'Execute query against removed column "legacy_status"',
                  sql: 'SELECT "legacy_status" FROM "orders" LIMIT 1;',
                },
              ],
              expected_observation: "Query execution is expected to fail with undefined column",
              status: "NOT_EXECUTED",
            },
          ],
          warnings: [],
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
      expect(screen.getByText("Evidence-Grounded AI Reasoning")).toBeInTheDocument(),
    );
    expect(screen.getByText("HYPOTHESIS • UNVERIFIED")).toBeInTheDocument();
    expect(screen.getByText("Dropped column remains referenced")).toBeInTheDocument();
    expect(screen.getByText("PROPOSED EXPERIMENT • NOT_EXECUTED")).toBeInTheDocument();
    expect(screen.getByText('SELECT "legacy_status" FROM "orders" LIMIT 1;')).toBeInTheDocument();
    expect(screen.getAllByText(/not executed yet/i).length).toBeGreaterThan(0);
  });
});
