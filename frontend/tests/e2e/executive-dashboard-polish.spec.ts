import { expect, test } from "@playwright/test";

const prediction = {
  prediction_id: 1, game_id: 10, sport: "NFL",
  home_team: "Philadelphia Eagles", away_team: "Dallas Cowboys",
  game_date: "2026-10-06T23:30:00Z", market: "spread", selection: "HOME",
  display_selection: "Philadelphia Eagles -3.5", line_value: -3.5,
  american_odds: -110, npi_score: 188, confidence_score: 91,
  simulation_probability: 61, projected_edge: 8, risk_level: "LOW",
  model_version: "NPI-4.0", reasoning: null,
};
const total = {
  ...prediction, prediction_id: 2, market: "total", selection: "UNDER",
  display_selection: "Dallas Cowboys @ Philadelphia Eagles — UNDER 47.5", line_value: 47.5,
};
const moneyline = {
  ...prediction, prediction_id: 3, market: "moneyline", selection: "AWAY",
  display_selection: "Dallas Cowboys ML", line_value: null, american_odds: 130,
};
const longTeam = {
  ...prediction, prediction_id: 4, game_id: 11, sport: "NBA",
  away_team: "Portland Trail Blazers", home_team: "Minnesota Timberwolves",
  display_selection: "Minnesota Timberwolves -3.5",
};
const pick = (item: typeof prediction | typeof moneyline, role: string, label: string) => ({
  prediction: item, role, label, ranking_score: 88,
  ranking_reasons: ["NPI 188.0 / 200", "91.0% confidence"],
});

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/**", async route => {
    const url = route.request().url();
    if (url.includes("/users/me")) {
      await route.fulfill({ json: { id: 1, username: "preview", email: "preview@example.com", role: "user", is_active: true, premium: true } });
    } else if (url.includes("/product/daily-card")) {
      await route.fulfill({ json: {
        count: 4, slate_date: "2026-10-06",
        best_bet: pick(prediction, "BEST_BET", "Best Bet"),
        featured_picks: [pick(total, "TOP_TOTAL", "Top Total"), pick(moneyline, "TOP_MONEYLINE", "Moneyline Value")],
        next_best: [pick(longTeam, "NEXT_BEST", "Next Best Pick")],
      } });
    } else if (url.includes("/product/predictions/upcoming")) {
      await route.fulfill({ json: { count: 4, predictions: [prediction, total, moneyline, longTeam] } });
    } else if (url.includes("/product/me/saved-picks")) {
      await route.fulfill({ json: { count: 0, picks: [] } });
    } else {
      await route.fulfill({ status: 404, json: { detail: "Unmocked preview request" } });
    }
  });
  await page.addInitScript(() => localStorage.setItem("golden_key_access_token", "local-preview-token"));
});

for (const width of [320, 390, 600, 900, 1440]) {
  test(`preserves compact layout, association, and clearance at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/dashboard");
    const games = page.getByTestId("sportsbook-game");
    await expect(games).toHaveCount(2);
    await page.evaluate(() => document.fonts.ready);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);

    for (const id of [10, 11]) {
      const game = page.locator(`[data-testid="sportsbook-game"][data-game-id="${id}"]`);
      const link = game.getByRole("link", { name: /View analysis for/ });
      await expect(link).toHaveCount(1);
      await expect(link).toHaveAttribute("href", `/games/${id}`);
      await expect(game.getByTestId(`game-${id}-header`).getByRole("link")).toHaveCount(1);
      await expect(game.getByTestId(`game-${id}-total-row`)).toHaveCount(1);
      await expect(game.getByTestId(`game-${id}-total-value`)).toHaveCount(1);
      if (width < 900) {
        const baselineHeight = width === 320 ? 277.578125 : 269.140625;
        const height = (await game.boundingBox())!.height;
        expect(1 - height / baselineHeight).toBeGreaterThanOrEqual(0.12);
        expect(1 - height / baselineHeight).toBeLessThanOrEqual(0.15);
        expect((await link.boundingBox())!.height).toBeGreaterThanOrEqual(44);
        await expect(link).toContainText("View matchup analysis");
      } else {
        await expect(game).toHaveCSS("display", "grid");
      }
    }
    if (width < 900) {
      await expect(page.getByTestId("game-10-home-team-row").getByTestId("game-10-spread-value")).toHaveText("-3.5 -110");
      await expect(page.getByTestId("game-10-away-team-row").getByTestId("game-10-moneyline-value")).toHaveText("+130");
    } else {
      await expect(page.getByTestId("game-10-total-value").locator("span")).toHaveCSS("font-size", "13.44px");
      const row = page.getByTestId("npi-pick-label-1").locator("..");
      expect((await row.boundingBox())!.width).toBeLessThanOrEqual(640);
      await expect(page.getByTestId("npi-pick-label-1").locator("p")).toHaveCSS("font-size", "17px");
    }

    if (width < 600) {
      const nav = page.getByTestId("mobile-navigation-shell");
      for (const action of await nav.getByRole("button").all()) {
        expect((await action.boundingBox())!.height).toBeGreaterThanOrEqual(44);
      }
      expect((await nav.boundingBox())!.height).toBe(59);
      const safeArea = await nav.evaluate(element => Array.from(document.styleSheets).some(sheet =>
        Array.from(sheet.cssRules).some(rule => rule instanceof CSSStyleRule &&
          !rule.selectorText.includes("::") && element.matches(rule.selectorText) &&
          rule.style.getPropertyValue("padding-bottom") === "env(safe-area-inset-bottom)"),
      ));
      expect(safeArea).toBe(true);
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      const footer = (await page.locator("footer").boundingBox())!;
      expect(footer.y + footer.height).toBeLessThan((await nav.boundingBox())!.y);
      await page.setViewportSize({ width, height: 650 });
      expect((await nav.boundingBox())!.height).toBe(59);
    }
  });
}

test("the single mobile analysis action supports keyboard and pointer navigation", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/dashboard");
  const link = page.getByTestId("game-10-header").getByRole("link", {
    name: "View analysis for Dallas Cowboys at Philadelphia Eagles",
  });
  await link.focus();
  await expect(link).toBeFocused();
  await expect(link).toHaveCSS("outline-style", "solid");
  await link.press("Enter");
  await expect(page).toHaveURL(/\/games\/10$/);
  await page.goto("/dashboard");
  await link.click();
  await expect(page).toHaveURL(/\/games\/10$/);
});
