import { expect, test, type Page } from "@playwright/test";
import { join } from "node:path";

function previewPath(filename: string): string {
  return process.env.DESIGN_PREVIEW_DIR
    ? join(process.env.DESIGN_PREVIEW_DIR, filename)
    : test.info().outputPath(filename);
}

const upcoming = [
  {
    prediction_id: 4101,
    game_id: 410,
    sport: "NFL",
    home_team: "Seattle Seahawks",
    away_team: "New England Patriots",
    game_date: "2026-10-11T20:25:00Z",
    market: "spread",
    selection: "HOME",
    display_selection: "Seattle Seahawks -3.5",
    line_value: -3.5,
    american_odds: -110,
    sportsbook: "DraftKings",
    odds_observed_at: "2026-10-10T15:00:00Z",
    model_version: "NPI-4.0",
    npi_score: 121.5,
    confidence_score: 68,
    simulation_probability: 57.1,
    projected_edge: 2.4,
    risk_level: "MEDIUM",
    reasoning: null,
    recommendation_eligible: true,
  },
  {
    prediction_id: 4102,
    game_id: 410,
    sport: "NFL",
    home_team: "Seattle Seahawks",
    away_team: "New England Patriots",
    game_date: "2026-10-11T20:25:00Z",
    market: "moneyline",
    selection: "AWAY",
    display_selection: "New England Patriots ML",
    line_value: null,
    american_odds: 145,
    sportsbook: "FanDuel",
    odds_observed_at: "2026-10-10T14:45:00Z",
    model_version: "NPI-4.0",
    npi_score: 108,
    confidence_score: 58,
    simulation_probability: 42,
    projected_edge: 1.1,
    risk_level: "HIGH",
    reasoning: null,
    recommendation_eligible: true,
  },
  {
    prediction_id: 4103,
    game_id: 410,
    sport: "NFL",
    home_team: "Seattle Seahawks",
    away_team: "New England Patriots",
    game_date: "2026-10-11T20:25:00Z",
    market: "total",
    selection: "UNDER",
    display_selection: "UNDER 44.5",
    line_value: 44.5,
    american_odds: -105,
    sportsbook: "DraftKings",
    odds_observed_at: "2026-10-10T15:00:00Z",
    model_version: "NPI-4.0",
    npi_score: 116,
    confidence_score: 62,
    simulation_probability: 54,
    projected_edge: 1.8,
    risk_level: "MEDIUM",
    reasoning: null,
    recommendation_eligible: true,
  },
  {
    prediction_id: 4201,
    game_id: 420,
    sport: "NBA",
    home_team: "Miami Heat",
    away_team: "Boston Celtics",
    game_date: "2026-10-11T23:30:00Z",
    market: "spread",
    selection: "AWAY",
    display_selection: "Boston Celtics -2.5",
    line_value: -2.5,
    american_odds: -110,
    sportsbook: "DraftKings",
    odds_observed_at: "2026-10-10T16:00:00Z",
    model_version: "NPI-5.0",
    npi_score: 117,
    confidence_score: 64,
    simulation_probability: 55,
    projected_edge: 1.5,
    risk_level: "MEDIUM",
    reasoning: null,
    recommendation_eligible: true,
  },
  {
    prediction_id: 4202,
    game_id: 420,
    sport: "NBA",
    home_team: "Miami Heat",
    away_team: "Boston Celtics",
    game_date: "2026-10-11T23:30:00Z",
    market: "moneyline",
    selection: "AWAY",
    display_selection: "Boston Celtics ML",
    line_value: null,
    american_odds: -135,
    sportsbook: "DraftKings",
    odds_observed_at: "2026-10-10T16:00:00Z",
    model_version: "NPI-5.0",
    npi_score: 117,
    confidence_score: 64,
    simulation_probability: 55,
    projected_edge: 1.5,
    risk_level: "MEDIUM",
    reasoning: null,
    recommendation_eligible: true,
  },
];

async function mockGameCenterApi(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("golden_key_access_token", "fixture-game-center-preview");
  });
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace("/api/v1", "");
    const data: Record<string, unknown> = {
      "/users/me": {
        id: 12,
        username: "Game Center fixture",
        email: "fixture@example.test",
        role: "user",
        is_active: true,
      },
      "/subscriptions/me": {
        entitlement_key: "premium",
        plan: "pro_monthly",
        status: "active",
        active: true,
        starts_at: null,
        ends_at: null,
        provider_subscriptions: [],
      },
      "/product/predictions/upcoming": {
        sport: null,
        start_date: "2026-10-10T00:00:00Z",
        end_date: "2026-10-24T00:00:00Z",
        count: upcoming.length,
        predictions: upcoming,
      },
      "/product/performance": {
        total_predictions: 3,
        wins: 1,
        losses: 1,
        pushes: 1,
        accuracy: 50,
        profit_loss: 0,
        market_performance: [],
        sport_performance: [],
        recent_results: [
          {
            prediction_id: 501,
            game_id: 410,
            sport: "NFL",
            game_date: "2026-10-06T20:25:00Z",
            home_team: "Seattle Seahawks",
            away_team: "New England Patriots",
            market: "spread",
            display_selection: "Seattle Seahawks -3.5",
            npi_score: 121.5,
            outcome: "WIN",
            home_score: 24,
            away_score: 17,
          },
          {
            prediction_id: 502,
            game_id: 420,
            sport: "NBA",
            game_date: "2026-10-05T23:30:00Z",
            home_team: "Miami Heat",
            away_team: "Boston Celtics",
            market: "spread",
            display_selection: "Boston Celtics -2.5",
            npi_score: 117,
            outcome: "LOSS",
            home_score: 102,
            away_score: 99,
          },
          {
            prediction_id: 503,
            game_id: 430,
            sport: "NCAAF",
            game_date: "2026-10-04T19:00:00Z",
            home_team: "Alabama Crimson Tide",
            away_team: "Georgia Bulldogs",
            market: "total",
            display_selection: "UNDER 44.5",
            npi_score: 116,
            outcome: "PUSH",
            home_score: 24,
            away_score: 21,
          },
        ],
      },
      "/product/me/saved-picks": { count: 0, picks: [] },
    };
    return route.fulfill({
      status: path in data ? 200 : 404,
      contentType: "application/json",
      body: JSON.stringify(data[path] ?? { detail: "Unmocked Game Center fixture endpoint" }),
    });
  });
}

test("mobile Game Center matches the fixture layout without horizontal overflow", async ({ page }) => {
  await mockGameCenterApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/games");

  await expect(page.getByRole("heading", { name: "Game Center" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Football games" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Basketball games" })).toHaveCount(0);
  const football = page.locator('[data-testid="game-card"][data-sport="NFL"]');
  await expect(football.getByText("Seattle Seahawks")).toBeVisible();
  await expect(football.getByText("New England Patriots")).toBeVisible();
  for (const part of ["badge", "name", "side"]) {
    const away = await football.getByTestId(`team-${part}-away`).boundingBox();
    const home = await football.getByTestId(`team-${part}-home`).boundingBox();
    expect(away).not.toBeNull();
    expect(home).not.toBeNull();
    expect(Math.abs(away!.y - home!.y)).toBeLessThan(1);
    if (part === "badge" || part === "name") {
      expect(away!.width).toBe(home!.width);
      expect(away!.height).toBe(home!.height);
    }
  }
  await expect(football.getByTestId("game-center-matchup")).toHaveCSS("background-image", /game-center-football\.svg/);
  await expect(page.locator('[data-sport="NBA"]').getByTestId("game-center-matchup"))
    .toHaveCSS("background-image", /game-center-basketball\.svg/);
  await expect(football.getByTestId("market-tile-spread")).toContainText("SEA -3.5");
  await expect(football.getByTestId("market-tile-moneyline")).toContainText("NE +145");
  await expect(football.getByTestId("market-tile-total")).toContainText("UNDER 44.5");
  await expect(football.getByRole("link", { name: /View Game Analysis/ })).toContainText("View pick analysis");
  await expect(page.getByTestId("recent-model-result")).toHaveCount(3);
  await expect(page.getByTestId("recent-model-results")).toContainText("WIN");
  await expect(page.getByTestId("recent-model-results")).toContainText("LOSS");
  await expect(page.getByTestId("recent-model-results")).toContainText("PUSH");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);

  await page.getByTestId("game-center").evaluate((element) => {
    const label = document.createElement("div");
    label.textContent = "DESIGN PREVIEW · FIXTURE DATA";
    label.setAttribute("data-testid", "fixture-preview-label");
    label.style.cssText = "position:fixed;top:8px;left:50%;transform:translateX(-50%);width:fit-content;padding:4px 8px;border:1px solid #00d4ff;border-radius:999px;color:#00d4ff;background:#07131e;font:700 10px sans-serif;letter-spacing:.12em;z-index:1300";
    element.append(label);
  });
  await page.screenshot({
    path: previewPath("fixture-game-center-mobile-v3.png"),
    fullPage: false,
    animations: "disabled",
  });

  await page.locator('[data-sport="NBA"]').evaluate((card) => {
    window.scrollTo(0, window.scrollY + card.getBoundingClientRect().top - 160);
  });
  await page.screenshot({
    path: previewPath("fixture-game-center-mobile-basketball-v3.png"),
    fullPage: false,
    animations: "disabled",
  });

  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  const lastResult = page.getByTestId("recent-model-result").last();
  await expect(lastResult).toBeInViewport();
  const resultBox = await lastResult.boundingBox();
  const navBox = await page.locator('[data-safe-area="bottom"]').boundingBox();
  expect(resultBox).not.toBeNull();
  expect(navBox).not.toBeNull();
  expect(resultBox!.y + resultBox!.height).toBeLessThanOrEqual(navBox!.y);
});

test("desktop Game Center uses a balanced card grid and preserves league filters", async ({ page }) => {
  await mockGameCenterApi(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/games");

  await expect(page.getByRole("heading", { name: "Game Center" })).toBeVisible();
  const cards = page.getByTestId("game-card");
  await expect(cards).toHaveCount(2);
  const footballBox = await cards.nth(0).boundingBox();
  const basketballBox = await cards.nth(1).boundingBox();
  expect(footballBox).not.toBeNull();
  expect(basketballBox).not.toBeNull();
  expect(Math.abs(footballBox!.x - basketballBox!.x)).toBeGreaterThan(100);
  await expect(page.getByTestId("sport-filter-nfl")).toBeVisible();
  await expect(page.getByTestId("sport-filter-nba")).toBeVisible();
  await expect(page.getByTestId("fixed-brand-header").getByRole("img")).toBeVisible();
  for (const card of await cards.all()) {
    for (const part of ["badge", "name", "side"]) {
      const away = await card.getByTestId(`team-${part}-away`).boundingBox();
      const home = await card.getByTestId(`team-${part}-home`).boundingBox();
      expect(away).not.toBeNull();
      expect(home).not.toBeNull();
      expect(Math.abs(away!.y - home!.y)).toBeLessThan(1);
      if (part === "badge" || part === "name") {
        expect(away!.height).toBe(home!.height);
      }
    }
  }

  await page.getByTestId("game-center").evaluate((element) => {
    const label = document.createElement("div");
    label.textContent = "DESIGN PREVIEW · FIXTURE DATA";
    label.setAttribute("data-testid", "fixture-preview-label");
    label.style.cssText = "position:fixed;top:8px;left:50%;transform:translateX(-50%);width:fit-content;padding:4px 8px;border:1px solid #00d4ff;border-radius:999px;color:#00d4ff;background:#07131e;font:700 10px sans-serif;letter-spacing:.12em;z-index:1300";
    element.append(label);
  });
  await page.screenshot({
    path: previewPath("fixture-game-center-desktop-v3.png"),
    fullPage: false,
    animations: "disabled",
  });
});
