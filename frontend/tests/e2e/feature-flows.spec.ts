import { expect, test } from "@playwright/test";

test("predictions applies winner and confidence filters with sort controls", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("golden_key_access_token", "seed-token");
  });

  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 10,
        username: "analyst",
        email: "analyst@nik.ai",
        role: "analyst",
        is_active: true,
      }),
    });
  });

  const predictionPayload = [
    {
      game_id: 901,
      game_date: "2026-07-24T18:00:00Z",
      home_team: "Boston Celtics",
      away_team: "Miami Heat",
      winner: "HOME",
      confidence: 82.3,
      nik_power_index: 114.2,
      home_npi: 114.2,
      away_npi: 107.8,
      model_version: "NPI-v2",
    },
  ];

  const capturedUrls: string[] = [];
  await page.route("**/api/v1/predictions**", async (route) => {
    capturedUrls.push(route.request().url());
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(predictionPayload),
    });
  });

  await page.goto("/predictions");

  await expect(page.getByRole("heading", { name: "Predictions" })).toBeVisible();
  await expect(page.getByText("Boston Celtics")).toBeVisible();

  await page.getByLabel("Winner Filter").fill("home");
  await page.getByLabel("Min Confidence").fill("70");
  await page.getByLabel("Sort By").click();
  await page.getByRole("option", { name: "Nik Power Index" }).click();
  await page.getByLabel("Order").click();
  await page.getByRole("option", { name: "Asc" }).click();

  await page.getByRole("button", { name: "Apply" }).click();

  await expect.poll(() => capturedUrls.length).toBeGreaterThan(1);

  const latestUrl = capturedUrls[capturedUrls.length - 1];
  expect(latestUrl).toContain("winner=home");
  expect(latestUrl).toContain("min_confidence=70");
  expect(latestUrl).toContain("sort_by=nik_power_index");
  expect(latestUrl).toContain("sort_order=asc");
});

test("games page renders upcoming, live, and completed sections", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("golden_key_access_token", "seed-token");
  });

  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 20,
        username: "viewer",
        email: "viewer@nik.ai",
        role: "viewer",
        is_active: true,
      }),
    });
  });

  await page.route("**/api/v1/games**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: 100,
          sport: "Basketball",
          league: "NBA",
          home_team_id: 1,
          away_team_id: 2,
          game_date: "2099-01-01T01:00:00Z",
          home_score: null,
          away_score: null,
          winner_team_id: null,
        },
        {
          id: 200,
          sport: "Basketball",
          league: "NBA",
          home_team_id: 3,
          away_team_id: 4,
          game_date: "2024-01-01T01:00:00Z",
          home_score: null,
          away_score: null,
          winner_team_id: null,
        },
        {
          id: 300,
          sport: "Basketball",
          league: "NBA",
          home_team_id: 5,
          away_team_id: 6,
          game_date: "2024-01-01T01:00:00Z",
          home_score: 110,
          away_score: 98,
          winner_team_id: 5,
        },
      ]),
    });
  });

  await page.goto("/games");

  await expect(page.getByRole("heading", { name: "Upcoming Games" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Live Games" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Completed Games" })).toBeVisible();

  await expect(page.getByText("2099-01-01T01:00:00Z")).toBeVisible();
  await expect(page.getByText("100", { exact: true })).toBeVisible();
  await expect(page.getByText("200", { exact: true })).toBeVisible();
  await expect(page.getByText("300", { exact: true })).toBeVisible();
});

test("predictions shows server error and recovers on retry", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("golden_key_access_token", "seed-token");
  });

  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 30,
        username: "analyst",
        email: "analyst@nik.ai",
        role: "analyst",
        is_active: true,
      }),
    });
  });

  let predictionCalls = 0;
  await page.route("**/api/v1/predictions**", async (route) => {
    predictionCalls += 1;
    if (predictionCalls <= 4) {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "backend unavailable" }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          game_id: 990,
          game_date: "2026-07-24T20:00:00Z",
          home_team: "Lakers",
          away_team: "Warriors",
          winner: "HOME",
          confidence: 75.5,
          nik_power_index: 109.9,
          home_npi: 109.9,
          away_npi: 104.4,
          model_version: "NPI-v2",
        },
      ]),
    });
  });

  await page.goto("/predictions");

  await expect.poll(() => predictionCalls, { timeout: 15000 }).toBeGreaterThanOrEqual(4);
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible({ timeout: 15000 });
  await page.getByRole("button", { name: "Retry" }).click();

  await expect(page.getByText("Lakers")).toBeVisible();
  await expect(page.getByText("Warriors")).toBeVisible();
});

test("games shows server error and recovers on retry", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("golden_key_access_token", "seed-token");
  });

  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 40,
        username: "viewer",
        email: "viewer@nik.ai",
        role: "viewer",
        is_active: true,
      }),
    });
  });

  let gameCalls = 0;
  await page.route("**/api/v1/games**", async (route) => {
    gameCalls += 1;
    if (gameCalls <= 4) {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "upstream error" }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: 700,
          sport: "Basketball",
          league: "NBA",
          home_team_id: 1,
          away_team_id: 2,
          game_date: "2099-01-01T01:00:00Z",
          home_score: null,
          away_score: null,
          winner_team_id: null,
        },
      ]),
    });
  });

  await page.goto("/games");

  await expect.poll(() => gameCalls, { timeout: 15000 }).toBeGreaterThanOrEqual(4);
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible({ timeout: 15000 });
  await page.getByRole("button", { name: "Retry" }).click();

  await expect(page.getByRole("heading", { name: "Upcoming Games" })).toBeVisible();
  await expect(page.getByText("700", { exact: true })).toBeVisible();
});

test("analytics renders calibration metrics and bucket chart", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("golden_key_access_token", "seed-token");
  });

  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 50,
        username: "viewer",
        email: "viewer@nik.ai",
        role: "viewer",
        is_active: true,
      }),
    });
  });

  await page.route("**/api/v1/analytics/accuracy", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        overall_accuracy: 77.2,
        sport_accuracy: {
          basketball: { total: 100, correct: 77, accuracy: 77.0 },
        },
        model_accuracy: {
          "NPI-v2": { total: 100, correct: 77, accuracy: 77.0 },
        },
        confidence_accuracy: {},
        dashboard_statistics: {
          overall_accuracy: 77.2,
          recent_predictions: [],
        },
      }),
    });
  });

  await page.route("**/api/v1/analytics/confidence", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        average_confidence: 80.0,
        highest_confidence: 95.0,
        lowest_confidence: 52.0,
        buckets: [
          { label: "70-79", predictions: 30, accuracy: 74.0 },
          { label: "80-89", predictions: 40, accuracy: 79.0 },
        ],
      }),
    });
  });

  await page.route("**/api/v1/analytics/calibration", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        overall_error: 2.9,
        mean_calibration_error: 1.1,
        maximum_error: 5.2,
        bucket_variance: 0.84,
        overall_reliability: 97.1,
        total_predictions: 140,
        buckets: [
          {
            range: "70-79",
            confidence: 75.4,
            accuracy: 73.0,
            error: 2.4,
            predictions: 40,
            wins: 29,
            losses: 11,
          },
          {
            range: "80-89",
            confidence: 84.7,
            accuracy: 82.5,
            error: 2.2,
            predictions: 50,
            wins: 41,
            losses: 9,
          },
        ],
      }),
    });
  });

  await page.route("**/api/v1/analytics/trends/daily", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { period: "2026-07-22", accuracy: 74.0, confidence: 78.0, predictions: 12 },
        { period: "2026-07-23", accuracy: 79.0, confidence: 81.0, predictions: 14 },
      ]),
    });
  });

  await page.route("**/api/v1/analytics/backtesting", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        snapshots_processed: 42,
        evaluations_created: 168,
        model_versions: ["NPI-v2"],
      }),
    });
  });

  await page.goto("/analytics");

  await expect(page.getByRole("heading", { name: "Analytics" })).toBeVisible();
  await expect(page.getByText("Calibration Reliability")).toBeVisible();
  await expect(page.getByText("97.10%")).toBeVisible();
  await expect(page.getByText("Calibration by Confidence Bucket")).toBeVisible();
  await expect(page.getByText("Predicted Confidence")).toBeVisible();
  await expect(page.getByText("Observed Accuracy")).toBeVisible();
});

test("models page renders comparison recommendation", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("golden_key_access_token", "seed-token");
  });

  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 60,
        username: "analyst",
        email: "analyst@nik.ai",
        role: "analyst",
        is_active: true,
      }),
    });
  });

  await page.route("**/api/v1/models", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          model_version: "NPI-v3",
          release_date: null,
          feature_set: [],
          evaluation_metrics: {
            accuracy: 71.8,
            calibration: 2.4,
            average_confidence: 81.2,
            predictions: 2184,
          },
          deployment_status: "active",
          evaluated_at: "2026-07-25T00:00:00+00:00",
        },
        {
          model_version: "NPI-v4",
          release_date: null,
          feature_set: [],
          evaluation_metrics: {
            accuracy: 73.4,
            calibration: 1.3,
            average_confidence: 79.8,
            predictions: 2184,
          },
          deployment_status: "candidate",
          evaluated_at: "2026-07-25T00:00:00+00:00",
        },
      ]),
    });
  });

  await page.route("**/api/v1/models/compare", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        current_model: {
          accuracy: 71.8,
          calibration: 2.4,
          average_confidence: 81.2,
          predictions: 2184,
        },
        candidate_model: {
          accuracy: 73.4,
          calibration: 1.3,
          average_confidence: 79.8,
          predictions: 2184,
        },
        winner: "candidate",
      }),
    });
  });

  await page.route("**/api/v1/analytics/model-learning", async (route) => {
    await page.waitForTimeout(1200);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        current_model: "NPI-v3",
        training_samples: 18421,
        candidate_models: 3,
        best_candidate: "NPI-v4",
      }),
    });
  });

  await page.goto("/models", { waitUntil: "domcontentloaded" });

  await expect(page.getByRole("heading", { name: "Models" })).toBeVisible();
  await expect(page.getByTestId("model-learning-skeleton")).toBeVisible();
  await expect(page.getByTestId("model-learning-skeleton")).not.toBeVisible();
  await expect(page.getByText("Model Learning")).toBeVisible();
  await expect(page.getByText("Current Model").first()).toBeVisible();
  await expect(page.getByText("Training Samples")).toBeVisible();
  await expect(page.getByText("18,421")).toBeVisible();
  await expect(page.getByText("Candidate Models")).toBeVisible();
  await expect(page.getByText("Best Candidate")).toBeVisible();
  await expect(page.getByText("Model Comparison")).toBeVisible();
  await expect(page.getByText("Recommendation")).toBeVisible();
  await expect(page.getByText("Promote Candidate")).toBeVisible();
  await expect(page.getByText("Performance Delta")).toBeVisible();
  await expect(page.getByText("Positive values favor the candidate model.")).toBeVisible();
  await expect(page.getByText("Confidence Delta")).toBeVisible();
});
