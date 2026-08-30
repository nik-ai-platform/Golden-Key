import { expect, test } from "@playwright/test";

const prediction = {
  prediction_id: 57,
  game_id: 101,
  sport: "WNBA",
  home_team: "Las Vegas Aces",
  away_team: "Minnesota Lynx",
  game_date: "2026-06-15T19:00:00Z",
  market: "moneyline",
  selection: "Minnesota Lynx",
  model_version: "NPI-4.0",
  npi_score: 168,
  confidence_score: 82.5,
  simulation_probability: 79.2,
  projected_edge: 6.4,
  risk_level: "Low",
  reasoning: "The production model favors Minnesota across the strongest factors.",
};

async function mockProductApi(page: import("@playwright/test").Page) {
  let saved = false;

  await page.route("**/api/v1/auth/login", (route) => route.fulfill({ json: { access_token: "test-token", token_type: "bearer" } }));
  await page.route("**/api/v1/users/me", (route) => route.fulfill({ json: { id: 1, username: "tester", email: "tester@example.com", premium: false } }));
  await page.route("**/api/v1/version", (route) => route.fulfill({ json: { api_version: "v1" } }));
  await page.route("**/api/v1/product/performance", (route) => route.fulfill({ json: { total_predictions: 20, wins: 14, losses: 5, pushes: 1, accuracy: 70, profit_loss: 125.5 } }));
  await page.route("**/api/v1/product/predictions/today**", (route) => route.fulfill({ json: { sport: null, count: 1, predictions: [prediction] } }));
  await page.route("**/api/v1/product/games/101", (route) => route.fulfill({ json: { game_id: 101, sport: "WNBA", home_team: prediction.home_team, away_team: prediction.away_team, game_date: prediction.game_date, predictions: [prediction] } }));
  await page.route("**/api/v1/users/save-prediction", (route) => {
    saved = true;
    return route.fulfill({ json: { id: 1, prediction_id: prediction.prediction_id } });
  });
  await page.route("**/api/v1/product/me/saved-picks", (route) => route.fulfill({ json: { count: saved ? 1 : 0, picks: saved ? [{ saved_pick_id: 1, prediction_id: 57, game_id: 101, market: "moneyline", selection: "Minnesota Lynx", confidence_score: 82.5, outcome: null }] : [] } }));
}

test("completes the authenticated product workflow", async ({ page }) => {
  await mockProductApi(page);

  await page.goto("/login");
  await page.getByLabel("Email").fill("tester@example.com");
  await page.getByLabel("Password").fill("password123");
  await page.getByRole("button", { name: "Sign In" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Today's edge" })).toBeVisible();
  await expect(page.getByText("API online · v1")).toBeVisible();

  await page.goto("/games");
  await page.getByRole("button", { name: "WNBA" }).click();
  await expect(page).toHaveURL(/sport=WNBA/);
  await page.getByRole("button", { name: "View analysis" }).click();
  await expect(page).toHaveURL(/\/games\/101$/);

  await page.getByRole("button", { name: "Save pick" }).click();
  await expect(page.getByRole("button", { name: "Saved", exact: true })).toBeDisabled();
  await page.goto("/saved-picks");
  await expect(page.getByText("Minnesota Lynx")).toBeVisible();

  await page.goto("/performance");
  await expect(page.getByRole("heading", { name: "Performance" })).toBeVisible();
  await expect(page.getByText("70.00%")).toBeVisible();

  await page.goto("/profile");
  await expect(page.getByText("tester@example.com")).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goto("/saved-picks");
  await expect(page).toHaveURL(/\/login$/);
});

test("shows friendly not-found states", async ({ page }) => {
  await mockProductApi(page);
  await page.addInitScript(() => localStorage.setItem("golden_key_access_token", "test-token"));
  await page.route("**/api/v1/product/games/999", (route) => route.fulfill({ status: 404, json: { detail: "Game not found" } }));

  await page.goto("/games/999");
  await expect(page.getByRole("heading", { name: "Page not found" })).toBeVisible({ timeout: 10_000 });
  await page.goto("/does-not-exist");
  await expect(page.getByRole("heading", { name: "Page not found" })).toBeVisible();
});

test("redirects when an authenticated session expires", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("golden_key_access_token", "expired-token"));
  await page.route("**/api/v1/users/me", (route) => route.fulfill({ status: 401, json: { detail: "Expired" } }));

  await page.goto("/profile");
  await expect(page).toHaveURL(/\/login$/);
});
