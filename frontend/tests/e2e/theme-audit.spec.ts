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

function dailyCardPick(
  role: "TOP_SPREAD" | "TOP_MONEYLINE" | "TOP_TOTAL" | "VALUE_PLAY" | "NEXT_BEST",
  label: string,
  predictionId: number,
  market: string,
  displaySelection: string,
) {
  return {
    role,
    label,
    ranking_score: 84,
    ranking_reasons: ["Strong model signal", "Positive projected edge"],
    prediction: {
      ...prediction,
      prediction_id: predictionId,
      game_id: predictionId,
      market,
      display_selection: displaySelection,
      npi_score: 168 - (predictionId - 60) * 3,
    },
  };
}

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
  await page.route("**/api/v1/product/daily-card**", (route) =>
    route.fulfill({
      json: {
        sport: null,
        generated_at: "2026-09-02T12:00:00Z",
        slate_date: "2026-09-10",
        count: 6,
        best_bet: {
          role: "BEST_BET",
          label: "Best Bet",
          ranking_score: 88,
          ranking_reasons: ["82.5% confidence", "6.4% projected edge"],
          prediction,
        },
        featured_picks: [
          dailyCardPick("TOP_SPREAD", "Top Spread", 60, "spread", "Buffalo Bills -2.5"),
          dailyCardPick("TOP_MONEYLINE", "Moneyline Value", 61, "moneyline", "Chicago Bears ML"),
          dailyCardPick("TOP_TOTAL", "Top Total", 62, "total", "OVER 44.5"),
          dailyCardPick("VALUE_PLAY", "Value Play", 63, "spread", "Miami Dolphins +4.5"),
        ],
        next_best: [
          dailyCardPick("NEXT_BEST", "Next Best Pick", 64, "spread", "Denver Broncos -1.5"),
        ],
      },
    }),
  );
  await page.route("**/api/v1/product/predictions/today**", (route) =>
    route.fulfill({
      json: {
        sport: null,
        slate_date: "2026-09-10",
        count: predictions.length,
        predictions,
      },
    }),
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
  await page.route("**/api/v1/product/performance-intelligence**", (route) =>
    route.fulfill({
      json: {
        period_days: 30,
        generated_at: "2026-09-02T12:00:00Z",
        overall: {
          total_bets: 3,
          wins: 1,
          losses: 1,
          pushes: 1,
          win_rate: 50,
          units_won: 0.9,
          roi: 30,
        },
        by_market: [],
        by_sport: [],
        by_npi_band: [],
        by_confidence_band: [],
        by_odds_band: [],
        by_side_type: [],
        by_model_version: [],
      },
    }),
  );
}

async function expectDarkPage(page: import("@playwright/test").Page) {
  await expect(page.getByRole("button", { name: "Switch to light mode" })).toBeVisible();
  expect(
    await page.evaluate(() => getComputedStyle(document.body).backgroundColor),
  ).toBe("rgb(9, 11, 15)");
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth),
  ).toBe(true);
}

async function expectCompactMetrics(
  page: import("@playwright/test").Page,
  expectedColumns: number,
) {
  const container = page.getByTestId("pick-metrics").first();
  const supportingMetrics = container.getByTestId("supporting-metrics");

  await expect(container).toBeVisible();
  for (const label of ["NPI", "Confidence", "Model Probability", "Risk"]) {
    await expect(container.getByText(label, { exact: true })).toBeVisible();
  }
  expect(
    await supportingMetrics.evaluate(
      (element) => getComputedStyle(element).gridTemplateColumns.split(" ").length,
    ),
  ).toBe(expectedColumns);
  expect(
    await supportingMetrics.evaluate((element) =>
      Array.from(element.children).every(
        (child) =>
          child.scrollWidth <= child.clientWidth &&
          child.scrollHeight <= child.clientHeight,
      ),
    ),
  ).toBe(true);
  expect(
    await supportingMetrics.evaluate((element) => {
      const cells = Array.from(element.children).map((child) =>
        child.getBoundingClientRect(),
      );
      return cells.every((cell, index) =>
        cells.slice(index + 1).every(
          (other) =>
            cell.right <= other.left ||
            other.right <= cell.left ||
            cell.bottom <= other.top ||
            other.bottom <= cell.top,
        ),
      );
    }),
  ).toBe(true);
}

async function expectDashboardMetrics(page: import("@playwright/test").Page) {
  const container = page.getByTestId("pick-metrics").first();
  const primaryMetrics = container.locator(":scope > div").first();

  await expect(container).toBeVisible();
  for (const label of ["Confidence", "Model Probability"]) {
    await expect(container.getByText(label, { exact: true })).toBeVisible();
  }
  expect(
    await primaryMetrics.evaluate(
      (element) => getComputedStyle(element).gridTemplateColumns.split(" ").length,
    ),
  ).toBe(1);
  expect(
    await container.evaluate((element) => element.scrollWidth <= element.clientWidth),
  ).toBe(true);
}

test("login supports dark mode without preset credentials", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByLabel("Email")).toHaveValue("");
  await expect(page.getByLabel("Password")).toHaveValue("");
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  await expectDarkPage(page);
  await expect(page.locator(".MuiCard-root")).toHaveCSS("background-color", "rgb(17, 21, 27)");
  await page.screenshot({
    path: "test-results/theme-login-dark.png",
    fullPage: true,
    animations: "disabled",
  });
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
      if (["/dashboard", "/games/101"].includes(route)) {
        if (route === "/dashboard") {
          await expectDashboardMetrics(page);
          for (const heading of ["Best Bet", "Market Leaders", "Model Intelligence", "Today's Games"]) {
            await expect(page.getByRole("heading", { name: heading })).toBeVisible();
          }
        } else {
          await expectCompactMetrics(page, viewport.name === "desktop" ? 3 : 2);
        }
        await page.screenshot({
          path: `test-results/theme-${route === "/dashboard" ? "dashboard" : "game-analysis"}-dark-${viewport.name}.png`,
          fullPage: true,
          animations: "disabled",
        });
      }
      if (["/games/101", "/saved-picks"].includes(route)) {
        for (const outcome of ["WIN", "LOSS", "PUSH"]) {
          await expect(page.getByText(outcome, { exact: true }).first()).toBeVisible();
        }
      }
    }

    await page.screenshot({
      path: `test-results/theme-profile-dark-${viewport.name}.png`,
      fullPage: true,
      animations: "disabled",
    });
  });
}

for (const viewport of [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test(`compact pick metrics render cleanly in light mode on ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.addInitScript(() => {
      localStorage.setItem("golden_key_access_token", "theme-token");
      localStorage.setItem("golden-key-theme", "light");
    });
    await mockProductApi(page);

    for (const route of ["/dashboard", "/games/101"]) {
      await page.goto(route);
      await expect(page.getByRole("button", { name: "Switch to dark mode" })).toBeVisible();
      if (route === "/dashboard") {
        await expectDashboardMetrics(page);
      } else {
        await expectCompactMetrics(page, viewport.name === "desktop" ? 3 : 2);
      }
      expect(
        await page.evaluate(() =>
          document.documentElement.scrollWidth <= document.documentElement.clientWidth,
        ),
      ).toBe(true);
      await page.screenshot({
        path: `test-results/theme-${route === "/dashboard" ? "dashboard" : "game-analysis"}-light-${viewport.name}.png`,
        fullPage: true,
        animations: "disabled",
      });
    }
  });
}