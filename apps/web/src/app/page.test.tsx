import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/lib/i18n";
import Home from "./page";

function renderHome() {
  return render(
    <I18nProvider>
      <Home />
    </I18nProvider>,
  );
}

describe("Home - Production Load Failure Proof", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    localStorage.clear();
  });

  it("renders the new hero and peak load proof in Korean by default", () => {
    renderHome();

    // Slogan and hero
    expect(screen.getByRole("heading", { name: /사용자가 몰리기 전에/i })).toBeInTheDocument();
    expect(screen.getByText(/병목을 먼저 재현하세요/i)).toBeInTheDocument();

    // 4-step flow
    expect(screen.getByRole("list", { name: /4단계 부하 증명 흐름/i })).toBeInTheDocument();
    expect(screen.getByText(/기능 테스트 통과 \(단일 요청 정상\)/i)).toBeInTheDocument();
    expect(screen.getByText(/동일 부하 회복 검증 \(수정 후 재실행\)/i)).toBeInTheDocument();

    // Tab navigation
    expect(screen.getByRole("tab", { name: /피크 부하 장애 검증/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /호환성 검증/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /로컬 러너/i })).toBeInTheDocument();

    // Primary Peak Load Demo
    expect(screen.getByText(/ShiftSafe Demo · Synthetic Subject/i)).toBeInTheDocument();
    expect(screen.getByText(/기능 테스트 통과 · PASS \(200 OK, 15ms\)/i)).toBeInTheDocument();
    expect(screen.getByText(/AI 가설: PROPOSED \/ UNVERIFIED/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /피크 트래픽 재현 실행/i }),
    ).toBeInTheDocument();
  });

  it("switches language between Korean and English when language button is clicked", () => {
    renderHome();

    // Default is Korean
    expect(screen.getByRole("heading", { name: /사용자가 몰리기 전에/i })).toBeInTheDocument();

    // Switch to English
    fireEvent.click(screen.getByRole("button", { name: "English" }));
    expect(screen.getByRole("heading", { name: /reproduce the bottleneck/i })).toBeInTheDocument();
    expect(screen.getByText(/before peak traffic does/i)).toBeInTheDocument();

    // Switch back to Korean
    fireEvent.click(screen.getByRole("button", { name: "한국어" }));
    expect(screen.getByRole("heading", { name: /사용자가 몰리기 전에/i })).toBeInTheDocument();
  });

  it("executes peak load experiment and proves bottleneck, then proves recovery under same load", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    // 1. Peak load execution response (PROVEN_BOTTLENECK)
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          run: {
            id: "run_perf_01",
            experiment_plan_id: "plan-shiftsafe-peak-load",
            experiment_contract_digest: "perf_contract_1234567890",
            subject_digest: "perf_subject_candidate",
            template: "EXTERNAL_DEPENDENCY_LATENCY",
            domain: "PERFORMANCE",
            verdict: "PROVEN_BOTTLENECK",
            started_at: "2026-09-04T00:00:00Z",
            finished_at: "2026-09-04T00:00:03Z",
            step_results: [
              {
                order: 1,
                type: "RUN_CONCURRENT_LOAD",
                status: "FAILED",
                duration_ms: 3200,
                observation_code: "DOWNSTREAM_QUEUE_AMPLIFICATION",
                message: "p95 latency exploded to 4820ms due to downstream queuing",
                performance_metrics: {
                  request_count: 300,
                  success_count: 246,
                  error_count: 0,
                  timeout_count: 54,
                  throughput_rps: 31.4,
                  p50_ms: 1850,
                  p95_ms: 4820,
                  p99_ms: 5200,
                  max_inflight: 150,
                  downstream_wait_p95_ms: 3600,
                  downstream_peak_inflight: 10,
                  timeout_rate: 0.18,
                  error_rate: 0.0,
                  regression_ratio: 26.8,
                },
              },
            ],
            performance_metrics: {
              request_count: 300,
              success_count: 246,
              error_count: 0,
              timeout_count: 54,
              throughput_rps: 31.4,
              p50_ms: 1850,
              p95_ms: 4820,
              p99_ms: 5200,
              max_inflight: 150,
              downstream_wait_p95_ms: 3600,
              downstream_peak_inflight: 10,
              timeout_rate: 0.18,
              error_rate: 0.0,
              regression_ratio: 26.8,
            },
            cleanup_succeeded: true,
            summary: "Peak load failure reproduced: p95 latency 4820ms (regression 26.8x), 18% timeouts under 150 concurrent users.",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    // 2. Remediation proof response (PROVEN_RECOVERED)
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          proof: {
            id: "proof_perf_01",
            fixture_id: "shiftsafe/dashboard-weather-dependency",
            remediation_id: "remediation/shiftsafe/dashboard-weather-dependency",
            domain: "PERFORMANCE",
            strategy: "CACHE_AND_COALESCING_WITH_TIMEOUT",
            description: "Apply 10s TTL cache with single-flight request coalescing and 1.5s timeout.",
            experiment_contract_digest: "perf_contract_1234567890",
            before: {
              id: "run_perf_before",
              verdict: "PROVEN_BOTTLENECK",
              experiment_contract_digest: "perf_contract_1234567890",
              performance_metrics: {
                p95_ms: 4820,
                throughput_rps: 31.4,
                timeout_rate: 0.18,
              },
            },
            after: {
              id: "run_perf_after",
              verdict: "PROVEN_PASS",
              experiment_contract_digest: "perf_contract_1234567890",
              performance_metrics: {
                request_count: 300,
                success_count: 300,
                error_count: 0,
                timeout_count: 0,
                throughput_rps: 280.0,
                p50_ms: 45,
                p95_ms: 310,
                p99_ms: 420,
                max_inflight: 40,
                downstream_wait_p95_ms: 45,
                downstream_peak_inflight: 1,
                timeout_rate: 0.0,
                error_rate: 0.0,
              },
            },
            verdict: "PROVEN_FIXED",
            same_experiment: true,
            subject_changed: true,
            summary: "PROVEN_RECOVERED: Remediated subject successfully handled 150 concurrent users with p95 310ms and 0% timeouts.",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    renderHome();

    // Click Peak Load Demo button
    const runBtn = screen.getByRole("button", { name: /피크 트래픽 재현 실행/i });
    fireEvent.click(runBtn);

    // Verify Bottleneck Reproduction
    await waitFor(() => expect(screen.getByText("병목 재현됨 (PROVEN_BOTTLENECK)")).toBeInTheDocument());
    expect(screen.getByText(/관측: DOWNSTREAM_QUEUE_AMPLIFICATION/i)).toBeInTheDocument();
    expect(screen.getAllByText("4820 ms").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("18%")).toBeInTheDocument();
    expect(screen.getByText("3600 ms")).toBeInTheDocument();

    // Verify Remediation button is available
    const fixBtn = screen.getByRole("button", { name: /수정 적용 및 동일 부하 재실행/i });
    expect(fixBtn).toBeInTheDocument();
    fireEvent.click(fixBtn);

    // Verify Recovery Proof under same load
    await waitFor(() => expect(screen.getByText("복구 검증 완료 (PROVEN_RECOVERED)")).toBeInTheDocument());
    expect(screen.getByText(/SAME LOAD/i)).toBeInTheDocument();
    expect(screen.getByText(/SAME CONDITIONS/i)).toBeInTheDocument();
    expect(screen.getByText(/CHANGED SUBJECT/i)).toBeInTheDocument();
    expect(screen.getAllByText("310 ms").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("0%")).toBeInTheDocument();

    // Check contrast comparison
    expect(screen.getByText(/p95 응답 지연 시간 대조/i)).toBeInTheDocument();
    expect(screen.getByText("180 ms")).toBeInTheDocument();
    expect(screen.getAllByText("4820 ms").length).toBeGreaterThanOrEqual(1);
  });

  it("switches to Compatibility Proofs tab and executes Database contract demo", async () => {
    vi.stubEnv("NEXT_PUBLIC_DEMO_REPOSITORY", "choi11000/changeproof-demo");
    vi.stubEnv("NEXT_PUBLIC_DEMO_PR", "1");

    const fetchSpy = vi.spyOn(globalThis, "fetch");

    // 1. Analysis API response
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          pull_request: { number: 1, title: "Drop legacy column", changed_files: 1, html_url: "" },
          changed_files: [{ category: "SQL_MIGRATION", reason: "migration", file: { path: "migrations/001.sql" } }],
          sql_files: [{ path: "migrations/001.sql", analysis: { changes: [{ operation: "DROP_COLUMN", table: "orders", column: "legacy_status" }] }, error: null }],
          dependency_targets: [{ type: "COLUMN", table: "orders", column: "legacy_status" }],
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
          impact_summary: null,
          failure_hypotheses: [
            {
              id: "hyp_01",
              category: "SCHEMA_CONTRACT_BREAK",
              title: "Dropped column still referenced",
              statement: "Application references orders.legacy_status",
              change_ids: ["c1"],
              evidence_ids: ["ev_1"],
              rationale: "Unchanged code reads dropped column",
              expected_failure_mode: "UndefinedColumn",
              assumptions: [],
              experiment_template: "DROPPED_COLUMN_REFERENCE",
              status: "UNVERIFIED",
            },
          ],
          experiment_plans: [
            {
              id: "plan_01",
              hypothesis_id: "hyp_01",
              template: "DROPPED_COLUMN_REFERENCE",
              change_ids: ["c1"],
              evidence_ids: ["ev_1"],
              steps: [],
              expected_observation: "UndefinedColumn",
              status: "PLANNED",
            },
          ],
          execution_allowed: true,
          controlled_fixture_id: "risky-saas/drop-legacy-status",
          warnings: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    renderHome();

    // Switch to Compatibility tab
    const compatTab = screen.getByRole("tab", { name: /호환성 검증/i });
    fireEvent.click(compatTab);

    // Verify DB Demo launcher
    const dbDemoBtn = screen.getByRole("button", { name: /데모 실행/i });
    expect(dbDemoBtn).toBeInTheDocument();
    fireEvent.click(dbDemoBtn);

    await waitFor(() => expect(screen.getByText("DROP_COLUMN orders.legacy_status")).toBeInTheDocument());
  });

  it("switches to Local Runner tab and shows installation and security guide", () => {
    renderHome();

    const runnerTab = screen.getByRole("tab", { name: /로컬 러너/i });
    fireEvent.click(runnerTab);

    expect(screen.getByText(/ChangeProof Local Runner Agent/i)).toBeInTheDocument();
    expect(screen.getByText(/pip install -e apps\/runner/i)).toBeInTheDocument();
    expect(screen.getByText(/changeproof inspect --repo \. --base HEAD~1/i)).toBeInTheDocument();
    expect(screen.getByText(/changeproof verify --base HEAD~1 --target http:\/\/localhost:8001/i)).toBeInTheDocument();
    expect(screen.getByText(/보안 정책 \/ Security Boundary/i)).toBeInTheDocument();
  });
});
