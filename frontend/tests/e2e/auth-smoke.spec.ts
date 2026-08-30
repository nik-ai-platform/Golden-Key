import { expect, test } from "@playwright/test";

test("redirects anonymous user to login", async ({ page }) => {
  await page.goto("/analytics");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Welcome Back" })).toBeVisible();
});

test("login success redirects to dashboard", async ({ page }) => {
  await page.route("**/api/v1/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "fake-jwt-token",
        token_type: "bearer",
      }),
    });
  });

  await page.route("**/api/v1/users/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 1,
        username: "admin",
        email: "admin@nik.ai",
        role: "admin",
        is_active: true,
      }),
    });
  });

  await page.route("**/api/v1/product/predictions/today**", (route) => route.fulfill({
    json: { sport: null, count: 0, predictions: [] },
  }));
  await page.route("**/api/v1/product/performance", (route) => route.fulfill({
    json: { total_predictions: 34, wins: 25, losses: 8, pushes: 1, accuracy: 75.76, profit_loss: 48.25, market_performance: [], sport_performance: [], recent_results: [] },
  }));

  await page.route("**/api/v1/dashboard", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        system_health: "healthy",
        overall_accuracy: 72.5,
        total_predictions: 34,
        recent_predictions: [{ game_id: 12 }],
        top_teams: [],
        model_versions: [{ model: "NPI-v1", accuracy: 72.5 }],
      }),
    });
  });

  await page.route("**/api/v1/analytics/confidence", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        average_confidence: 78.3,
        highest_confidence: 98.1,
        lowest_confidence: 51.4,
        buckets: [],
      }),
    });
  });

  await page.route("**/api/v1/analytics/calibration", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        overall_error: 2.4,
        mean_calibration_error: 1.2,
        maximum_error: 4.1,
        bucket_variance: 0.62,
        overall_reliability: 97.6,
        total_predictions: 120,
        buckets: [],
      }),
    });
  });

  await page.goto("/login");
  await page.getByLabel("Email").fill("admin@nik.ai");
  await page.getByLabel("Password").fill("admin123");
  await page.getByRole("button", { name: "Sign In" }).click();

  await expect(page).toHaveURL(/\/dashboard\/?$/);
  await expect(page.getByRole("heading", { name: "Today's edge" })).toBeVisible();
});

test("dashboard renders expected metrics after authenticated bootstrap", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("golden_key_access_token", "seed-token");
  });

  await page.route("**/api/v1/users/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 2,
        username: "viewer",
        email: "viewer@nik.ai",
        role: "viewer",
        is_active: true,
      }),
    });
  });

  await page.route("**/api/v1/product/predictions/today**", (route) => route.fulfill({
    json: { sport: null, count: 0, predictions: [] },
  }));
  await page.route("**/api/v1/product/performance", (route) => route.fulfill({
    json: { total_predictions: 128, wins: 104, losses: 23, pushes: 1, accuracy: 81.89, profit_loss: 96.4, market_performance: [], sport_performance: [], recent_results: [] },
  }));

  await page.route("**/api/v1/dashboard", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        system_health: "healthy",
        overall_accuracy: 81.25,
        total_predictions: 128,
        recent_predictions: [{ game_id: 1001 }],
        top_teams: [],
        model_versions: [{ model: "NPI-v2", accuracy: 81.25 }],
      }),
    });
  });

  await page.route("**/api/v1/analytics/confidence", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        average_confidence: 84.55,
        highest_confidence: 99.0,
        lowest_confidence: 44.0,
        buckets: [],
      }),
    });
  });

  await page.route("**/api/v1/analytics/calibration", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        overall_error: 3.6,
        mean_calibration_error: 1.8,
        maximum_error: 5.1,
        bucket_variance: 0.91,
        overall_reliability: 96.4,
        total_predictions: 128,
        buckets: [],
      }),
    });
  });

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Today's edge" })).toBeVisible();
  await expect(page.getByText("81.3%")).toBeVisible();
  await expect(page.getByText("128")).toBeVisible();
  await expect(page.getByText("+$96.40")).toBeVisible();
});
