import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Outlet, Route, Routes } from "react-router-dom";

import { AuthContext } from "../../src/auth/AuthContextDefinition";
import { AppLayout } from "../../src/layouts/AppLayout";
import { WorkerHealthPage } from "../../src/pages/WorkerHealthPage";
import { AppRouter } from "../../src/routes/AppRouter";
import { getWorkerStatus } from "../../src/services/operationsService";
import { ThemeModeProvider } from "../../src/theme/ThemeModeProvider";
import type { AuthUser } from "../../src/types/auth";
import type { WorkerStatusResponse } from "../../src/types/operations";

vi.mock("../../src/services/operationsService", () => ({ getWorkerStatus: vi.fn() }));

const payload: WorkerStatusResponse = {
  observed_at: "2026-10-07T12:00:00Z",
  telemetry_enabled: true,
  workers: [
    {
      worker_name: "upcoming-game-worker",
      health: "healthy",
      alerts: [],
      stale_after_seconds: 7322,
      instance_history_truncated: false,
      cycle_history_truncated: true,
      latest_instance: {
        id: "00000000-0000-0000-0000-000000000001",
        state: "idle",
        started_at: "2026-10-07T11:00:00Z",
        heartbeat_at: "2026-10-07T12:00:00Z",
        progress_at: "2026-10-07T12:00:00Z",
        stopped_at: null,
        poll_seconds: 3600,
        heartbeat_seconds: 3600,
        schedule_mode: "after_completion",
        last_success_at: "2026-10-07T12:00:00Z",
        last_success_duration_ms: 2000,
        telemetry_failures: 0,
        ownership_held: true,
      },
      recent_instances: [],
      recent_cycles: [
        {
          id: "00000000-0000-0000-0000-000000000002",
          sequence: 2,
          state: "succeeded",
          started_at: "2026-10-07T11:59:58Z",
          finished_at: "2026-10-07T12:00:00Z",
          duration_ms: 2000,
          expected_sources: 1,
          completed_sources: 1,
          failed_sources: 0,
          telemetry_complete: true,
          auxiliary_errors: 0,
          error_code: null,
          sources: [
            {
              sport: "NBA",
              league: "NBA_PRESEASON",
              provider: "odds_api",
              provider_source: "basketball_nba_preseason",
              state: "succeeded",
              started_at: "2026-10-07T11:59:58Z",
              finished_at: "2026-10-07T12:00:00Z",
              duration_ms: 2000,
              error_code: null,
              counters: { fetched: 0, prediction_rows_created: null },
            },
          ],
        },
      ],
    },
  ],
};

function auth(role: AuthUser["role"] = "admin") {
  return {
    user: { id: 1, username: "test", email: "test@example.com", role, is_active: true },
    isAuthenticated: true,
    isBootstrapping: false,
    login: vi.fn(),
    logout: vi.fn(),
  };
}

function wrapper(
  children: React.ReactNode,
  role: AuthUser["role"] = "admin",
  path = "/admin/workers",
) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <ThemeModeProvider>
      <AuthContext.Provider value={auth(role)}>
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={[path]}>{children}</MemoryRouter>
        </QueryClientProvider>
      </AuthContext.Provider>
    </ThemeModeProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

describe("admin worker health", () => {
  it("renders evidence, ownership, cadence and accessible source details without treating null as zero", async () => {
    vi.mocked(getWorkerStatus).mockResolvedValue(payload);
    wrapper(<WorkerHealthPage />);
    expect(await screen.findByRole("heading", { name: "Worker Health", level: 1 })).toBeTruthy();
    expect(await screen.findByText("Held")).toBeTruthy();
    expect(screen.getByText("3600 seconds")).toBeTruthy();
    const cycle = screen.getByRole("button", { name: /upcoming-game-worker cycle 2: succeeded/ });
    expect(cycle.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(cycle);
    expect(cycle.getAttribute("aria-expanded")).toBe("true");
    expect(cycle.getAttribute("aria-controls")).toBe(
      `${payload.workers[0].recent_cycles[0].id}-sources`,
    );
    expect(await screen.findByRole("heading", { name: "NBA · NBA_PRESEASON" })).toBeTruthy();
    expect(screen.getByText("prediction rows created")).toBeTruthy();
    expect(screen.getByText("Unknown")).toBeTruthy();
    expect(screen.getAllByText("0").length).toBeGreaterThan(0);
    expect(screen.getByText(/Showing the latest 10 cycles/)).toBeTruthy();
  });

  it.each([390, 1280])("preserves essential evidence at width %s", async (width) => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: width });
    vi.mocked(getWorkerStatus).mockResolvedValue(payload);
    wrapper(<WorkerHealthPage />);
    expect(await screen.findByText(payload.workers[0].latest_instance!.id)).toBeTruthy();
    expect(screen.getByText("Main-loop progress")).toBeTruthy();
    expect(screen.getByText("Last success")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Refresh worker status" })).toBeTruthy();
  });

  it("does not claim healthy evidence when disabled", async () => {
    vi.mocked(getWorkerStatus).mockResolvedValue({
      ...payload,
      telemetry_enabled: false,
      workers: [
        { ...payload.workers[0], health: "disabled", latest_instance: null, recent_cycles: [] },
      ],
    });
    wrapper(<WorkerHealthPage />);
    expect(await screen.findByText(/Telemetry is disabled/)).toBeTruthy();
    expect(screen.getByText("No instance evidence available.")).toBeTruthy();
    expect(screen.queryByText("healthy")).toBeNull();
  });

  it("announces unavailable storage explicitly and permits retry", async () => {
    vi.mocked(getWorkerStatus).mockRejectedValue(
      new Error("Worker telemetry storage is unavailable"),
    );
    wrapper(<WorkerHealthPage />);
    expect(await screen.findByRole("alert")).toHaveProperty(
      "textContent",
      expect.stringContaining("Worker status unavailable"),
    );
    vi.mocked(getWorkerStatus).mockResolvedValue(payload);
    fireEvent.click(screen.getByRole("button", { name: "Refresh worker status" }));
    expect(await screen.findByText("healthy")).toBeTruthy();
  });

  it("shows classified alerts as text, not just color", async () => {
    vi.mocked(getWorkerStatus).mockResolvedValue({
      ...payload,
      workers: [
        {
          ...payload.workers[0],
          health: "critical",
          alerts: [
            { code: "stale_heartbeat", severity: "critical", message: "Heartbeat is stale." },
          ],
        },
      ],
    });

    wrapper(<WorkerHealthPage />);
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", "Heartbeat is stale.");
    expect(screen.getByText("critical")).toBeTruthy();
  });

  it("labels cached evidence as stale after a failed refresh rather than hiding the failure", async () => {
    vi.mocked(getWorkerStatus).mockResolvedValueOnce(payload).mockRejectedValue({
      status: 503,
      message: "Worker telemetry storage is unavailable",
    });
    wrapper(<WorkerHealthPage />);
    expect(await screen.findByText("healthy")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Refresh worker status" }));
    await waitFor(() =>
      expect(screen.getByRole("alert").textContent).toContain(
        "Previously loaded evidence, if shown, is stale",
      ),
    );
    expect(screen.getByText("healthy")).toBeTruthy();
  });

  it.each(["user", "viewer", "analyst"] as const)(
    "blocks %s direct navigation without fetching evidence",
    async (role) => {
      wrapper(<AppRouter />, role);
      expect(await screen.findByRole("alert")).toHaveProperty(
        "textContent",
        "Administrator access required.",
      );
      expect(getWorkerStatus).not.toHaveBeenCalled();
      expect(screen.queryByRole("heading", { name: "Worker Health" })).toBeNull();
    },
  );

  it("exposes the admin route and navigation only to administrators", async () => {
    vi.mocked(getWorkerStatus).mockResolvedValue(payload);
    wrapper(<AppRouter />);
    expect(await screen.findByRole("heading", { name: "Worker Health", level: 1 })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Worker Health" }).getAttribute("href")).toBe(
      "/admin/workers",
    );
  });

  it("leaves customer navigation destinations intact and hides operations", () => {
    wrapper(
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/admin/workers" element={<Outlet />} />
        </Route>
      </Routes>,
      "user",
    );
    expect(screen.queryByRole("link", { name: "Worker Health" })).toBeNull();
    for (const destination of [
      "/dashboard",
      "/games",
      "/saved-picks",
      "/parlays",
      "/performance",
      "/profile",
      "/how-it-works",
    ]) {
      expect(document.querySelector(`a[href="${destination}"]`)).toBeTruthy();
    }
  });
});
