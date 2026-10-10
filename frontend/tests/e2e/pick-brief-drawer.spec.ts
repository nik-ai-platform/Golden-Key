import { expect, test, type Page } from "@playwright/test";
import type { GameDetail } from "../../src/types/product";

const game: GameDetail = {
  game_id: 101,
  sport: "NFL",
  home_team: "Seattle Seahawks",
  away_team: "New England Patriots",
  game_date: "2026-10-11T20:00:00Z",
  home_score: null,
  away_score: null,
  predictions: [{
    prediction_id: 7001,
    game_id: 101,
    sport: "NFL",
    home_team: "Seattle Seahawks",
    away_team: "New England Patriots",
    game_date: "2026-10-11T20:00:00Z",
    market: "spread",
    selection: "HOME",
    display_selection: "Seattle Seahawks -3.5",
    line_value: -3.5,
    american_odds: -110,
    sportsbook: "DraftKings",
    odds_observed_at: "2026-10-09T20:30:00Z",
    model_version: "NPI-5.0",
    npi_score: 158.4,
    confidence_score: 76.5,
    simulation_probability: 61.2,
    projected_edge: 5.4,
    risk_level: "MEDIUM",
    reasoning: "Spread model. NPI Score: 158.4/200 Model Probability: 61.2% Key Advantages: Home Advantage applied, Spread difficulty evaluated: 3.5 Risk Factors: No historical rule matched",
    recommendation_eligible: true,
    signal_breakdown: {
      model_version: "NPI-5.0",
      prediction_recorded_at: "2026-10-09T20:30:00Z",
      factors: [
        {
          factor_name: "Home Advantage",
          weight: 20,
          factor_score: 20,
          predicted_side: "HOME",
          recorded_at: "2026-10-09T20:30:00Z",
        },
        {
          factor_name: "Spread Value",
          weight: 35,
          factor_score: 22.75,
          predicted_side: "HOME",
          recorded_at: "2026-10-09T20:30:00Z",
        },
      ],
      frozen_odds: {
        snapshot_id: 1010,
        sportsbook: "DraftKings",
        spread_home: -3.5,
        spread_away: 3.5,
        spread_home_price: -110,
        spread_away_price: -110,
        moneyline_home: -165,
        moneyline_away: 145,
        total: 44.5,
        total_over_price: -110,
        total_under_price: -110,
        recorded_at: "2026-10-09T20:30:00Z",
      },
      recorded_explanation: "Spread model. NPI Score: 158.4/200 Model Probability: 61.2% Key Advantages: Home Advantage applied, Spread difficulty evaluated: 3.5 Risk Factors: No historical rule matched",
    },
  }],
};

async function mockCustomerApi(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("golden_key_access_token", "local-pick-brief-preview");
  });
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace("/api/v1", "");
    const responses: Record<string, unknown> = {
      "/users/me": {
        id: 1,
        username: "Design preview",
        email: "preview@example.test",
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
      "/product/games/101": game,
    };
    return route.fulfill({
      status: Object.hasOwn(responses, path) ? 200 : 404,
      json: responses[path] ?? { detail: "Unmocked preview endpoint" },
    });
  });
}

async function savePreviewScreenshot(page: Page, filename: string) {
  const directory = process.env.DESIGN_PREVIEW_DIR;
  if (directory) {
    await page.screenshot({
      path: `${directory}\\${filename}`,
      fullPage: true,
      animations: "disabled",
    });
  }
}

test("mobile drawer is floating, keyboard-operable, scroll-locked, and role-filtered", async ({ page }) => {
  await mockCustomerApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/games/101");
  await expect(page.getByRole("heading", { name: "Understanding This Pick" })).toBeVisible();

  await page.getByRole("button", { name: "Open navigation" }).click();
  const drawer = page.locator(".MuiDrawer-paper").last();
  const navigation = page.getByRole("navigation", { name: "Mobile navigation" });
  await expect(drawer).toBeVisible();
  await expect(navigation.getByRole("img", { name: "Bear A Hand Sports wordmark" })).toBeVisible();
  await expect(navigation.getByRole("link", { name: "Games" })).toHaveAttribute("aria-current", "page");
  await expect(navigation.getByRole("link", { name: "How It Works" })).toBeVisible();
  await expect(navigation.getByRole("link", { name: "Worker Health" })).toHaveCount(0);
  await expect(navigation.getByRole("link")).toHaveCount(7);
  await expect(navigation.getByRole("link", { name: /NFL|NBA|WNBA|NCAAF|NCAAB/ })).toHaveCount(0);
  await expect(navigation.locator("img")).toHaveCount(1);
  await expect(page.getByText("Analyst Desk", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Close navigation" })).toBeVisible();
  await expect.poll(async () => drawer.evaluate((element) => element.contains(document.activeElement))).toBe(true);
  expect(await page.evaluate(() => document.body.style.overflow)).toBe("hidden");

  await page.getByRole("button", { name: "Close navigation" }).focus();
  await page.keyboard.press("Tab");
  await expect.poll(async () =>
    navigation.getByRole("link", { name: "Dashboard" }).evaluate((element) => element === document.activeElement),
  ).toBe(true);
  await savePreviewScreenshot(page, "mobile-floating-drawer.png");

  await page.keyboard.press("Escape");
  await expect(drawer).toBeHidden();
  await expect.poll(async () => page.evaluate(() => document.body.style.overflow)).toBe("");

  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.locator(".MuiBackdrop-root").click({ position: { x: 1, y: 400 } });
  await expect(drawer).toBeHidden();
});

test("desktop pick brief expands exact-version evidence and frozen odds without contribution bars", async ({ page }) => {
  await mockCustomerApi(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/games/101");
  const brief = page.getByRole("region", { name: "Understanding this spread pick" });
  await expect(brief.getByText("Pick Brief", { exact: true })).toBeVisible();
  await expect(page.getByText("Analyst Desk", { exact: true })).toHaveCount(0);
  await expect(brief.getByText("New England Patriots @ Seattle Seahawks")).toBeVisible();
  await expect(brief.getByText("Seattle Seahawks -3.5")).toBeVisible();
  await expect(brief.getByText(/Quoted odds -110 · DraftKings/)).toBeVisible();
  await expect(brief.getByText("Home Advantage applied", { exact: true })).toBeVisible();
  await expect(brief.getByText("No historical rule matched", { exact: true })).toBeVisible();
  await expect(brief.getByText("No pick-specific uncertainty was recorded.")).toHaveCount(0);
  await expect(brief.getByRole("button", { name: "Learn about NPI" })).toBeVisible();

  const breakdownToggle = brief.getByRole("button", { name: "View signal breakdown" });
  await breakdownToggle.click();
  await expect(breakdownToggle).toHaveAttribute("aria-expanded", "true");
  await expect(brief.locator(".MuiAccordion-root")).toHaveClass(/Mui-expanded/);
  await expect(brief.getByText("Recorded model factors · NPI-5.0")).toBeVisible();
  await expect(brief.getByText("20 / 20")).toBeVisible();
  await expect(brief.getByText("Frozen sportsbook inputs")).toBeVisible();
  await expect(brief.getByText(/Snapshot 1010 · DraftKings/)).toBeVisible();
  await expect(brief.getByRole("progressbar")).toHaveCount(0);
  expect(await page.evaluate(() =>
    document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  )).toBe(true);
  await savePreviewScreenshot(page, "desktop-pick-brief-breakdown.png");
});
