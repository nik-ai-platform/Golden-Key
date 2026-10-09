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
  total_predictions: 6, wins: 2, losses: 2, pushes: 2, accuracy: 50, profit_loss: 0,
  market_performance: [], sport_performance: [],
  recent_results: (["WIN", "LOSS", "PUSH", "WIN", "LOSS", "PUSH"] as const).map((outcome, index) => ({
    prediction_id: 90 + index, game_id: 9 + index, sport: "NFL", game_date: `2026-10-0${8 - index}T17:00:00Z`,
    home_team: "Buffalo Bills", away_team: "Miami Dolphins", market: index === 0 ? "total" : "spread",
    display_selection: index === 0 ? "Miami Dolphins @ Buffalo Bills UNDER 47.5" : `Buffalo Bills -${index + 0.5}`,
    npi_score: 172, outcome,
    home_score: 24, away_score: 17,
  })),
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

for (const width of [320, 390, 430, 600, 900, 1200, 1440]) {
  test(`dashboard branding, data and responsive clearance at ${width}px`, async ({ page }) => {
    await previewApi(page);
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "THE GAME. THE DATA. YOUR EDGE." })).toBeVisible();
    await expect(page.getByText("Upcoming matchups", { exact: true })).toHaveCount(0);
    await expect(page.getByText("Reported model version", { exact: true })).toHaveCount(0);
    await expect(page.getByTestId("upcoming-matchup-count")).toHaveCount(0);
    await expect(page.getByTestId("reported-model-version")).toHaveCount(0);
    const brandArtwork = page.getByRole("img", { name: /Complete Bear A Hand Sports brand artwork/ });
    await expect(brandArtwork).toBeVisible();
    await expect(brandArtwork).toHaveAttribute("src", "/bear-a-hand-complete-brand.jpg");
    expect(await brandArtwork.evaluate((image: HTMLImageElement) => image.naturalWidth)).toBe(3000);
    const bannerBox = (await page.getByTestId("brand-artwork-banner").boundingBox())!;
    const artworkBox = (await brandArtwork.boundingBox())!;
    const headerBox = (await page.getByTestId("fixed-brand-header").boundingBox())!;
    const controlsBox = (await page.getByTestId("header-controls").boundingBox())!;
    const mainBox = (await page.getByRole("main").boundingBox())!;
    expect(artworkBox.width / artworkBox.height).toBeCloseTo(1.2, 1);
    expect(artworkBox.width).toBeLessThanOrEqual(bannerBox.width);
    expect(artworkBox.height).toBeLessThanOrEqual(bannerBox.height);
    expect(controlsBox.y + controlsBox.height).toBeLessThanOrEqual(bannerBox.y);
    expect(mainBox.y).toBeGreaterThanOrEqual(headerBox.y + headerBox.height);
    const wordmark = page.locator('img[alt="Bear A Hand Sports wordmark"]');
    await expect(wordmark).toHaveAttribute("src", "/bear-a-hand-wordmark.png");
    expect(await wordmark.evaluate((image: HTMLImageElement) => image.naturalWidth)).toBe(1200);
    if (width < 600) {
      await page.getByRole("button", { name: "Open navigation" }).click();
      await expect(page.getByRole("img", { name: "Bear A Hand Sports wordmark" })).toBeVisible();
      await page.keyboard.press("Escape");
    } else {
      await expect(page.getByRole("img", { name: "Bear A Hand Sports wordmark" })).toBeVisible();
    }
    await expect(page.getByRole("heading", { name: "Model Outcomes" })).toBeVisible();
    const outcomes = page.getByTestId("dashboard-outcomes-placement");
    const picks = page.getByTestId("dashboard-picks-panel");
    await expect(outcomes.getByTestId("dashboard-recent-result")).toHaveCount(5);
    await expect(outcomes.getByRole("link", { name: "View all results" })).toHaveAttribute("href", "/performance");
    const recentRows = outcomes.getByTestId("dashboard-recent-result");
    for (const [index, result] of performance.recent_results.slice(0, 5).entries()) {
      await expect(recentRows.nth(index)).toContainText(result.display_selection);
      await expect(recentRows.nth(index)).toContainText(result.outcome);
    }
    await expect(outcomes.getByText(performance.recent_results[5].display_selection, { exact: true })).toHaveCount(0);
    const heroBox = (await page.getByTestId("dashboard-hero").boundingBox())!;
    const outcomesBox = (await outcomes.boundingBox())!;
    const picksBox = (await picks.boundingBox())!;
    if (width < 600) {
      expect(outcomesBox.y).toBeGreaterThanOrEqual(heroBox.y + heroBox.height);
      expect(outcomesBox.y - (heroBox.y + heroBox.height)).toBeLessThanOrEqual(17);
      expect(picksBox.y).toBeGreaterThanOrEqual(outcomesBox.y + outcomesBox.height);
    } else if (width >= 1200) {
      expect(outcomesBox.x).toBeGreaterThanOrEqual(picksBox.x + picksBox.width);
      expect(outcomesBox.y).toBe(picksBox.y);
    }
    expect(await outcomes.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
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
      const lastContent = await page.getByRole("main").locator("footer").boundingBox();
      const navigation = await page.getByTestId("mobile-navigation-shell").boundingBox();
      expect(lastContent!.y + lastContent!.height).toBeLessThan(navigation!.y);
      await page.getByRole("button", { name: "Open navigation" }).click();
      await expect(page.getByRole("img", { name: "Bear A Hand Sports wordmark" }).last()).toBeVisible();
      await page.keyboard.press("Escape");
    }
    if (width === 390 || width === 430 || width === 1440) {
      await page.evaluate(() => {
        const label = document.createElement("div");
        label.textContent = "LOCAL DESIGN PREVIEW - SYNTHETIC TEST DATA";
        label.style.cssText = "grid-column:1/-1;background:#a4ef18;color:#060d14;text-align:center;font:700 11px sans-serif;padding:3px;";
        document.querySelector('[data-testid="dashboard-hero"]')!.prepend(label);
        window.scrollTo(0, 0);
      });
      await page.screenshot({ path: `${process.env.CYAN_SCREENSHOT_DIR ?? "customer-launch-artifacts"}\\mobile-outcomes-dashboard-${width}.png`, fullPage: true });
      await page.screenshot({ path: `${process.env.CYAN_SCREENSHOT_DIR ?? "customer-launch-artifacts"}\\mobile-outcomes-viewport-${width}.png` });
      await outcomes.evaluate((element) => {
        const label = document.createElement("div");
        label.textContent = "LOCAL PREVIEW - SYNTHETIC TEST DATA";
        label.style.cssText = "background:#a4ef18;color:#060d14;text-align:center;font:700 11px sans-serif;padding:3px;";
        element.prepend(label);
        window.scrollTo(0, window.scrollY + element.getBoundingClientRect().top - 72);
      });
      await page.screenshot({ path: `${process.env.CYAN_SCREENSHOT_DIR ?? "customer-launch-artifacts"}\\mobile-outcomes-panel-${width}.png` });
    }
    if (width < 600) {
      const allResults = outcomes.getByRole("link", { name: "View all results" });
      await allResults.scrollIntoViewIfNeeded();
      await allResults.focus();
      await expect(allResults).toBeFocused();
      const linkBox = (await allResults.boundingBox())!;
      const navigation = (await page.getByTestId("mobile-navigation-shell").boundingBox())!;
      expect(linkBox.y + linkBox.height).toBeLessThan(navigation.y);
    }
    await page.getByRole("button", { name: "Switch to light mode" }).click();
    await page.reload();
    await expect(page.getByRole("button", { name: "Switch to dark mode" })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  });
}

for (const width of [390, 430, 1440]) {
  test(`outcome loading, error retry and empty states stay independent at ${width}px`, async ({ page }) => {
    await previewApi(page);
    let state: "loading" | "error" | "empty" = "loading";
    let releaseLoading!: () => void;
    const waiting = new Promise<void>((resolve) => { releaseLoading = resolve; });
    await page.route("**/api/v1/product/performance", async (route) => {
      if (state === "loading") await waiting;
      if (state === "error") return route.fulfill({ status: 503, json: { detail: "Test unavailable" } });
      return route.fulfill({ json: { ...performance, total_predictions: 0, wins: 0, losses: 0, pushes: 0, recent_results: [] } });
    });
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/dashboard");
    const outcomes = page.getByTestId("dashboard-outcomes-placement");
    await expect(outcomes.getByText("Loading model outcomes...")).toBeVisible();
    await expect(page.getByTestId("sportsbook-games-board")).toBeVisible();
    state = "error";
    releaseLoading();
    await expect(outcomes.getByText("Unable to load model outcomes.")).toBeVisible({ timeout: 15000 });
    const retry = outcomes.getByRole("button", { name: "Retry" });
    await retry.focus();
    await expect(retry).toBeFocused();
    state = "empty";
    await retry.click();
    await expect(outcomes.getByText("No recent settled picks.")).toBeVisible();
    await expect(outcomes.getByTestId("dashboard-recent-result")).toHaveCount(0);
    await expect(outcomes.getByRole("link", { name: "View all results" })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    expect(await outcomes.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
  });
}
