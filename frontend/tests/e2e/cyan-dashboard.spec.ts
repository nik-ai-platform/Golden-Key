import { expect, test, type Page } from "@playwright/test";
import type { DailyCardResponse, Performance, Prediction } from "../../src/types/product";

const prediction: Prediction = {
  prediction_id: 101, game_id: 10, sport: "NFL",
  home_team: "Buffalo Bills", away_team: "Miami Dolphins",
  game_date: "2026-10-11T17:00:00Z", market: "spread", selection: "HOME",
  display_selection: "Buffalo Bills -3.5", line_value: -3.5, american_odds: -108,
  sportsbook: "Test sportsbook", odds_observed_at: "2026-10-09T00:00:00Z",
  model_version: "NPI-5.0", npi_score: 172, confidence_score: 78,
  simulation_probability: 58, projected_edge: 4, risk_level: "MEDIUM",
  reasoning: "Synthetic test fixture, not a live recommendation.", recommendation_eligible: true,
};
const total: Prediction = {
  ...prediction, prediction_id: 102, market: "total", selection: "UNDER",
  display_selection: "Miami Dolphins @ Buffalo Bills UNDER 47.5", line_value: 47.5,
  american_odds: -112,
};
const moneyline: Prediction = {
  ...prediction, prediction_id: 103, market: "moneyline", selection: "AWAY",
  display_selection: "Miami Dolphins ML", line_value: null, american_odds: 145,
};
const dailyCard: DailyCardResponse = {
  sport: null, generated_at: "2026-10-09T00:00:00Z", slate_date: "2026-10-11", count: 3,
  best_bet: { role: "BEST_BET", label: "Best Bet", ranking_reasons: ["Test ranking"], prediction },
  featured_picks: [
    { role: "TOP_SPREAD", label: "Top Spread", ranking_reasons: [], prediction },
    { role: "TOP_MONEYLINE", label: "Moneyline Value", ranking_reasons: [], prediction: moneyline },
    { role: "TOP_TOTAL", label: "Top Total", ranking_reasons: [], prediction: total },
  ],
  next_best: [],
};
const performance: Performance = {
  total_predictions: 3, wins: 1, losses: 1, pushes: 1, accuracy: 50, profit_loss: 0,
  market_performance: [], sport_performance: [],
  recent_results: [{
    prediction_id: 90, game_id: 9, sport: "NFL", game_date: "2026-10-08T17:00:00Z",
    home_team: "Buffalo Bills", away_team: "Miami Dolphins", market: "spread",
    display_selection: "Buffalo Bills -3.5", npi_score: 172, outcome: "WIN",
    home_score: 24, away_score: 17,
  }],
};

async function previewApi(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("golden_key_access_token", "local-mocked-token");
  });
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace("/api/v1", "");
    const responses: Record<string, unknown> = {
      "/users/me": { id: 1, username: "Design preview", email: "preview@example.test", role: "user", is_active: true, premium: true },
      "/subscriptions/me": { entitlement_key: "premium", plan: "pro_monthly", status: "active", active: true, starts_at: null, ends_at: null, provider_subscriptions: [] },
      "/product/daily-card": dailyCard,
      "/product/predictions/upcoming": { sport: null, start_date: "2026-10-09T00:00:00Z", end_date: "2026-10-23T00:00:00Z", count: 3, predictions: [prediction, total, moneyline] },
      "/product/performance": performance,
      "/product/me/saved-picks": { count: 0, picks: [] },
    };
    if (Object.hasOwn(responses, path)) return route.fulfill({ json: responses[path] });
    return route.fulfill({ status: 404, json: { detail: "Unmocked design-preview API" } });
  });
}

for (const width of [320, 390, 600, 900, 1200, 1440]) {
  test(`cyan dashboard preserves data and responsive clearance at ${width}px`, async ({ page }) => {
    await previewApi(page);
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "THE GAME. THE DATA. YOUR EDGE." })).toBeVisible();
    await expect(page.getByTestId("upcoming-matchup-count")).toHaveText("1");
    await expect(page.getByTestId("reported-model-version")).toHaveText("NPI-5.0");
    await expect(page.getByRole("heading", { name: "Model Outcomes" })).toBeVisible();
    await expect(page.getByTestId("npi-pick-label-102")).toContainText("UNDER 47.5");
    await expect(page.getByText("68%", { exact: true })).toHaveCount(0);
    await expect(page.getByRole("img", { name: /Bear holding a glowing globe/ })).toBeVisible();
    expect(await page.getByText("Bear A Hand Sports", { exact: true }).first().evaluate((element) => getComputedStyle(element).fontFamily)).toContain("Newsreader Variable");
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    for (const sport of ["All", "NFL", "NBA", "NCAAF", "NCAAB", "WNBA"]) {
      await expect(page.getByRole("button", { name: sport, exact: true })).toBeAttached();
    }
    const explore = page.getByRole("link", { name: "Explore picks" });
    await explore.focus();
    await expect(explore).toBeFocused();
    await explore.click();
    const totals = page.getByTestId("game-10-total-row");
    await expect(totals).toHaveCount(1);
    const reasoning = page.getByRole("link", { name: /Read total reasoning/ });
    await reasoning.focus();
    await expect(reasoning).toBeFocused();
    await expect(reasoning).toHaveAttribute("href", "/games/10");
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    if (width < 600) {
      const lastContent = await page.getByRole("link", { name: "View full performance" }).boundingBox();
      const navigation = await page.getByTestId("mobile-navigation-shell").boundingBox();
      expect(lastContent!.y + lastContent!.height).toBeLessThan(navigation!.y);
    }
    if (width === 390 || width === 1440) {
      await page.evaluate(() => {
        const label = document.createElement("div");
        label.textContent = "LOCAL DESIGN PREVIEW - SYNTHETIC TEST DATA";
        label.style.cssText = "grid-column:1/-1;background:#a4ef18;color:#060d14;text-align:center;font:700 11px sans-serif;padding:3px;";
        document.querySelector('[data-testid="dashboard-hero"]')!.prepend(label);
        window.scrollTo(0, 0);
      });
      await page.screenshot({ path: `${process.env.CYAN_SCREENSHOT_DIR ?? "customer-launch-artifacts"}\\cyan-dashboard-${width}.png`, fullPage: true });
      await page.screenshot({ path: `${process.env.CYAN_SCREENSHOT_DIR ?? "customer-launch-artifacts"}\\cyan-dashboard-viewport-${width}.png` });
    }
    await page.getByRole("button", { name: "Switch to light mode" }).click();
    await page.reload();
    await expect(page.getByRole("button", { name: "Switch to dark mode" })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  });
}
