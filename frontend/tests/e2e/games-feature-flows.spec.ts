import { expect, test, type Page } from "@playwright/test";

async function authenticateViewer(page: Page, id: number) {
  await page.addInitScript(() => {
    localStorage.setItem("golden_key_access_token", "seed-token");
  });
  await page.route("**/api/v1/users/me", (route) => route.fulfill({
    json: {
      id,
      username: "viewer",
      email: "viewer@nik.ai",
      role: "viewer",
      is_active: true,
    },
  }));
}

function prediction(overrides: Record<string, unknown> = {}) {
  return {
    prediction_id: 100,
    game_id: 200,
    sport: "NBA",
    game_date: "2099-01-01T01:00:00Z",
    home_team: "Boston Celtics",
    away_team: "Miami Heat",
    market: "spread",
    selection: "HOME",
    display_selection: "Boston Celtics -4.5",
    line_value: -4.5,
    american_odds: -110,
    confidence_score: 82.3,
    npi_score: 114.2,
    simulation_probability: 67.1,
    projected_edge: 8.2,
    risk_level: "low",
    reasoning: "Spread model.",
    model_version: "NPI-v2",
    ...overrides,
  };
}

test("games page renders today's prediction opportunities", async ({ page }) => {
  await authenticateViewer(page, 20);
  await page.route("**/api/v1/product/predictions/today**", (route) => route.fulfill({
    json: {
      sport: null,
      count: 1,
      predictions: [prediction()],
    },
  }));

  await page.goto("/games");

  await expect(page.getByRole("heading", { name: "Games", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Miami Heat @ Boston Celtics" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Boston Celtics -4.5" })).toBeVisible();
});

test("games supports the NCAAF prediction filter", async ({ page }) => {
  await authenticateViewer(page, 21);

  const requestedUrls: string[] = [];
  await page.route("**/api/v1/product/predictions/today**", (route) => {
    requestedUrls.push(route.request().url());
    return route.fulfill({
      json: { sport: "NCAAF", count: 0, predictions: [] },
    });
  });

  await page.goto("/games");
  await page.getByRole("button", { name: "NCAAF", exact: true }).click();

  await expect(page).toHaveURL(/sport=NCAAF/);
  await expect.poll(() => requestedUrls.some((url) => url.includes("sport=NCAAF"))).toBe(true);
});

test("games shows server error and recovers on retry", async ({ page }) => {
  await authenticateViewer(page, 40);

  let gameCalls = 0;
  await page.route("**/api/v1/product/predictions/today**", (route) => {
    gameCalls += 1;
    if (gameCalls <= 4) {
      return route.fulfill({
        status: 500,
        json: { detail: "upstream error" },
      });
    }

    return route.fulfill({
      json: {
        sport: null,
        count: 1,
        predictions: [prediction({
          prediction_id: 700,
          game_id: 701,
          home_team: "Lakers",
          away_team: "Warriors",
          market: "moneyline",
          display_selection: "Lakers ML",
          line_value: null,
          american_odds: -120,
          confidence_score: 75.5,
          npi_score: 109.9,
          simulation_probability: 64,
          projected_edge: 5,
          risk_level: "medium",
          reasoning: "Moneyline model.",
        })],
      },
    });
  });

  await page.goto("/games");

  await expect.poll(() => gameCalls, { timeout: 15_000 }).toBeGreaterThanOrEqual(4);
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible({ timeout: 15_000 });
  await page.getByRole("button", { name: "Retry" }).click();

  await expect(page.getByRole("heading", { name: "Games", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Warriors @ Lakers" })).toBeVisible();
});