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
    expect(screen.getByText("orders.legacy_status")).toBeInTheDocument();
    expect(screen.getAllByText("1", { selector: "dd" })).toHaveLength(3);
  });
});
