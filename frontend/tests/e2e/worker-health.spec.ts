import { expect, test } from "@playwright/test";

const id = "00000000-0000-0000-0000-000000000001";
const payload = {
  observed_at: "2026-10-07T12:00:00Z",
  telemetry_enabled: true,
  workers: ["final-score-worker", "upcoming-game-worker"].map((worker_name, index) => ({
    worker_name,
    health: "warning",
    stale_after_seconds: 7320,
    instance_history_truncated: false,
    cycle_history_truncated: false,
    alerts: [
      {
        code: "partial_cycle",
        severity: "warning",
        message: "The latest completed cycle is partial.",
      },
    ],
    latest_instance: {
      id: `${id.slice(0, -1)}${index + 3}`,
      state: "idle",
      started_at: "2026-10-07T10:00:00Z",
      heartbeat_at: "2026-10-07T12:00:00Z",
      progress_at: "2026-10-07T12:00:00Z",
      stopped_at: null,
      poll_seconds: 3600,
      heartbeat_seconds: 60,
      schedule_mode: "after_completion",
      last_success_at: "2026-10-07T11:00:00Z",
      last_success_duration_ms: 0,
      telemetry_failures: 0,
      ownership_held: true,
    },
    recent_instances: [],
    recent_cycles: [
      {
        id: `${id.slice(0, -1)}${index + 5}`,
        sequence: 2,
        state: "partial",
        started_at: "2026-10-07T11:00:00Z",
        finished_at: "2026-10-07T11:00:00Z",
        duration_ms: 0,
        expected_sources: 1,
        completed_sources: 1,
        failed_sources: 0,
        telemetry_complete: true,
        auxiliary_errors: 1,
        error_code: "publication_failed",
        sources: [
          {
            sport: "NBA",
            league: "NBA_PRESEASON",
            provider: "odds_api",
            provider_source: "basketball_nba_preseason",
            state: "partial",
            started_at: "2026-10-07T11:00:00Z",
            finished_at: "2026-10-07T11:00:00Z",
            duration_ms: 0,
            error_code: "publication_failed",
            counters: { fetched: 0, prediction_rows_created: null },
          },
        ],
      },
    ],
  })),
};

for (const width of [320, 390, 900, 1440]) {
  test(`admin evidence has no overflow and keyboard-accessible sources at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.route("**/api/v1/**", async (route) => {
      if (route.request().url().includes("/users/me")) {
        await route.fulfill({
          json: {
            id: 1,
            username: "admin",
            email: "admin@example.com",
            role: "admin",
            is_active: true,
          },
        });
      } else if (route.request().url().includes("/operations/workers")) {
        await route.fulfill({ json: payload });
      } else {
        await route.fulfill({ status: 404, json: { detail: "Unmocked local test request" } });
      }
    });
    await page.addInitScript(() =>
      localStorage.setItem("golden_key_access_token", "local-test-token"),
    );
    await page.goto("/admin/workers");
    await expect(page.getByRole("heading", { name: "Worker Health", exact: true })).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      width,
    );
    const cycle = page.getByRole("button", { name: "final-score-worker cycle 2: partial" });
    await cycle.focus();
    await expect(cycle).toBeFocused();
    await cycle.press("Enter");
    await expect(cycle).toHaveAttribute("aria-expanded", "true");
    await expect(page.getByRole("heading", { name: "NBA · NBA_PRESEASON" })).toBeVisible();
    const panel = page.getByRole("region", { name: "final-score-worker", exact: true });
    await expect(panel.getByText("prediction rows created", { exact: true })).toBeVisible();
    await expect(panel.getByText("Unknown", { exact: true })).toBeVisible();
    await expect(panel.locator(".MuiCollapse-entered")).toHaveCount(1);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      width,
    );
    expect(await page.getByRole("button").allTextContents()).not.toContain("Restart");
    if (width < 600) {
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      const footer = (await page.locator("footer").boundingBox())!;
      const nav = (await page.getByTestId("mobile-navigation-shell").boundingBox())!;
      expect(footer.y + footer.height).toBeLessThan(nav.y);
      await page.getByRole("button", { name: "Open navigation" }).click();
      await expect(page.getByRole("link", { name: "Worker Health" })).toBeVisible();
    } else {
      await expect(page.getByRole("link", { name: "Worker Health" })).toBeVisible();
    }
  });
}

for (const role of ["user", "viewer", "analyst"]) {
  test(`${role} cannot fetch admin telemetry from direct navigation`, async ({ page }) => {
    let statusRequests = 0;
    await page.route("**/api/v1/**", async (route) => {
      if (route.request().url().includes("/operations/workers")) statusRequests += 1;
      await route.fulfill({
        json: { id: 1, username: role, email: "test@example.com", role, is_active: true },
      });
    });
    await page.addInitScript(() =>
      localStorage.setItem("golden_key_access_token", "local-test-token"),
    );
    await page.goto("/admin/workers");
    await expect(page.getByRole("alert")).toHaveText("Administrator access required.");
    expect(statusRequests).toBe(0);
    await expect(page.getByRole("link", { name: "Worker Health" })).toHaveCount(0);
  });
}
