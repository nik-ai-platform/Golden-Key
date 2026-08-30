import { expect, test } from "@playwright/test";

const prediction = {
  prediction_id: 57,
  game_id: 101,
  sport: "NFL",
  home_team: "Seattle Seahawks",
  away_team: "New England Patriots",
  game_date: "2026-09-10T19:00:00Z",
  market: "spread",
  selection: "HOME",
  display_selection: "Seattle Seahawks -3.5",
  line_value: -3.5,
  american_odds: -110,
  model_version: "NPI-4.0",
  npi_score: 168,
  confidence_score: 82.5,
  simulation_probability: 79.2,
  projected_edge: 6.4,
  risk_level: "LOW",
  reasoning: "Seattle projects as the stronger side.",
  outcome: "WIN",
};

const predictions = [
  prediction,
  {
    ...prediction,
    prediction_id: 58,
    market: "moneyline",
    display_selection: "New England Patriots ML",
    outcome: "LOSS",
  },
  {
    ...prediction,
    prediction_id: 59,
    market: "total",
    display_selection: "OVER 44.5",
    outcome: "PUSH",
  },
];

async function mockProductApi(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill({
      json: {
        id: 1,
        username: "theme-tester",
        email: "theme@example.com",
        role: "user",
        is_active: true,
        premium: false,
      },
    }),
  );
  await page.route("**/api/v1/product/predictions/today**", (route) =>
    route.fulfill({ json: { sport: null, count: predictions.length, predictions } }),
  );
  await page.route("**/api/v1/product/games/101", (route) =>
    route.fulfill({
      json: {
        game_id: 101,
        sport: prediction.sport,
        home_team: prediction.home_team,
        away_team: prediction.away_team,
        game_date: prediction.game_date,
        home_score: 24,
        away_score: 17,
        predictions,
      },
    }),
  );
  await page.route("**/api/v1/product/me/saved-picks", (route) =>
    route.fulfill({
      json: {
        count: predictions.length,
        picks: predictions.map((item) => ({
            saved_pick_id: 1,
            ...item,
            matchup: `${prediction.away_team} @ ${prediction.home_team}`,
            home_score: 24,
            away_score: 17,
          })),
      },
    }),
  );
  await page.route("**/api/v1/product/performance", (route) =>
    route.fulfill({
      json: {
        total_predictions: 3,
        wins: 1,
        losses: 1,
        pushes: 1,
        accuracy: 50,
        profit_loss: 90,
        market_performance: [
          { name: "spread", settled: 1, wins: 1, losses: 0, pushes: 0, win_rate: 100 },
        ],
        sport_performance: [
          { name: "NFL", settled: 1, wins: 1, losses: 0, pushes: 0, win_rate: 100 },
        ],
        recent_results: predictions,
      },
    }),
  );
}

async function expectDarkPage(page: import("@playwright/test").Page) {
  await expect(page.getByRole("button", { name: "Switch to light mode" })).toBeVisible();
  expect(
    await page.evaluate(() => getComputedStyle(document.body).backgroundColor),
  ).toBe("rgb(7, 19, 18)");
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth),
  ).toBe(true);
}

test("login supports dark mode without preset credentials", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByLabel("Email")).toHaveValue("");
  await expect(page.getByLabel("Password")).toHaveValue("");
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  await expectDarkPage(page);
  await expect(page.locator(".MuiCard-root")).toHaveCSS("background-color", "rgb(16, 35, 33)");
  await page.screenshot({ path: "test-results/theme-login-dark.png", fullPage: true });
});

for (const viewport of [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test(`active product routes render cleanly in dark mode on ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.addInitScript(() => {
      localStorage.setItem("golden_key_access_token", "theme-token");
      localStorage.setItem("golden-key-theme", "dark");
    });
    await mockProductApi(page);

    for (const route of [
      "/dashboard",
      "/games",
      "/games/101",
      "/saved-picks",
      "/performance",
      "/profile",
    ]) {
      await page.goto(route);
      await expectDarkPage(page);
      await expect(page.locator("main")).toBeVisible();
      if (["/games/101", "/saved-picks", "/performance"].includes(route)) {
        for (const outcome of ["WIN", "LOSS", "PUSH"]) {
          await expect(page.getByText(outcome, { exact: true }).first()).toBeVisible();
        }
      }
    }

    await page.screenshot({
      path: `test-results/theme-profile-dark-${viewport.name}.png`,
      fullPage: true,
    });
  });
}