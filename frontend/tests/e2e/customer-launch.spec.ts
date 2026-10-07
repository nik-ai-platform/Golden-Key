import { expect, test, type Page } from "@playwright/test";

const plans = {
  currency: "USD", trial_days: 7,
  plans: [
    { id: "pro_monthly", name: "Bear A Hand Pro Monthly", amount_minor: 1000, interval: "month" },
    { id: "pro_annual", name: "Bear A Hand Pro Annual", amount_minor: 7999, interval: "year" },
  ], premium_benefits: ["Full picks and game analysis"],
};
const free = { entitlement_key: "premium", plan: "free", status: "inactive", active: false, starts_at: null, ends_at: null, provider_subscriptions: [] };

async function mocks(page: Page, authenticated: boolean, options: { accessError?: boolean; activation?: boolean; expired?: boolean; premium?: "active" | "trialing" } = {}) {
  const apiRequests: string[] = [];
  let accessRequests = 0;
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.startsWith("/api/v1/")) {
      apiRequests.push(url.pathname);
      const path = url.pathname.replace("/api/v1", "");
      if (path === "/subscriptions/plans") return route.fulfill({ json: plans });
      if (path === "/users/me" || path === "/product/profile") return route.fulfill({ json: { id: 1, username: "Local preview", email: "local@example.test", role: "user", is_active: true, premium: true } });
      if (path === "/subscriptions/me") {
        accessRequests++;
        if (options.accessError) return route.fulfill({ status: 503, json: { detail: "Mock unavailable" } });
        return route.fulfill({ json: {
          ...free,
          ...(options.premium ? { active: true, plan: "pro_monthly", status: "active" } : {}),
          ...(options.activation && accessRequests >= 2 ? { active: true, plan: "pro_monthly", status: "active" } : {}),
          provider_subscriptions: options.premium || options.expired ? [{ provider: "stripe", plan: "pro_monthly", status: options.premium ?? "canceled", current_period_end: null, trial_end: null, cancel_at_period_end: false }] : [],
        } });
      }
      if (path === "/product/preview") return route.fulfill({ json: {
        sport: null, count: 1, games: [{ game_id: 10, sport: "NBA", league: "NBA", home_team: "Home Team", away_team: "Away Team", start_time: "2026-10-08T23:00:00Z", status: "scheduled",
          selection: "MUST NEVER SHOW", odds: -110 }],
      } });
      if (path === "/auth/email-verification") return route.fulfill({ json: { message: "Neutral response" } });
      if (path === "/auth/register") return route.fulfill({ json: { id: 2, username: "Synthetic signup", email: "signup@example.test", is_active: true, role: "viewer" } });
      return route.fulfill({ status: 404, json: { detail: "Unmocked launch API request" } });
    }
    if (url.origin === "http://127.0.0.1:4197") return route.continue();
    return route.abort("blockedbyclient");
  });
  await page.addInitScript((hasSession) => {
    localStorage.clear();
    if (hasSession) localStorage.setItem("golden_key_access_token", "local-mocked-token");
  }, authenticated);
  return apiRequests;
}

for (const width of [320, 390, 600, 900, 1440]) {
  test(`active and trialing accounts cannot repeat checkout at ${width}px`, async ({ page }) => {
    for (const premium of ["active", "trialing"] as const) {
      const requests = await mocks(page, true, { premium });
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/profile");
      await expect(page.getByText(/Premium access is already active/)).toBeVisible();
      await expect(page.getByRole("button", { name: "Choose Monthly" })).toBeDisabled();
      await expect(page.getByRole("button", { name: "Choose Annual" })).toBeDisabled();
      const billing = page.getByRole("button", { name: "Manage Billing" });
      await expect(billing).toBeEnabled();
      await billing.focus();
      await expect(billing).toBeFocused();
      expect(requests).not.toContain("/api/v1/subscriptions/checkout-session");
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
      await page.unroute("**/*");
    }
  });

  test(`public customer information and keyboard links at ${width}px`, async ({ page }) => {
    const requests = await mocks(page, false);
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "A clearer view of the game." })).toBeVisible();
    await expect(page.getByText(/Monthly: \$10.00 \/ month/)).toBeVisible();
    await expect(page.getByText(/Annual: \$79.99 \/ year/)).toBeVisible();
    await expect(page.getByText(/7-day trial/)).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    const education = page.getByRole("link", { name: "Metric education", exact: true });
    await education.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: "How to Read Your Picks" })).toBeVisible();
    for (const [path, title] of [
      ["/terms", "Terms of service"], ["/privacy", "Privacy notice"],
      ["/responsible-gaming", "Responsible gaming"], ["/disclaimer", "Prediction disclaimer"], ["/support", "Support"],
    ]) {
      await page.goto(path);
      await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
      await expect(page.getByText(/Operational draft for attorney review/)).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    }
    expect(requests.filter((path) => path !== "/api/v1/subscriptions/plans")).toEqual([]);
    await page.screenshot({ path: `customer-launch-artifacts\\public-support-${width}.png`, fullPage: true });
  });

  test(`free slate and Premium guards at ${width}px`, async ({ page }) => {
    const requests = await mocks(page, true);
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Free Preview dashboard" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Away Team at Home Team" })).toBeVisible();
    await expect(page.getByText("MUST NEVER SHOW")).toHaveCount(0);
    await expect(page.getByText("-110", { exact: true })).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    await page.screenshot({ path: `customer-launch-artifacts\\free-dashboard-${width}.png`, fullPage: true });
    for (const path of ["/games", "/games/10", "/saved-picks", "/parlays", "/performance"]) {
      await page.goto(path);
      await expect(page.getByRole("heading", { name: "Premium feature" })).toBeVisible();
      const upgrade = page.getByRole("link", { name: "Explore Premium" });
      await upgrade.focus();
      await page.keyboard.press("Enter");
      await expect(page).toHaveURL(/\/profile$/);
      await expect(page.getByRole("button", { name: "Choose Monthly" })).toBeVisible();
    }
    expect(requests.some((path) => /\/(predictions|games|parlays|product\/(daily|upcoming|saved|performance))/.test(path))).toBe(false);
  });
}

test("entitlement API failure closes paid data while preserving account navigation", async ({ page }) => {
  await mocks(page, true, { accessError: true });
  await page.goto("/games/10");
  await expect(page.getByText(/Unable to verify Premium access/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Refresh access" })).toBeVisible();
  await page.getByRole("link", { name: "Account and billing" }).click();
  await expect(page).toHaveURL(/\/profile$/);
  await expect(page.getByRole("button", { name: "Choose Monthly" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Choose Monthly" })).toBeDisabled();
});

test("signup uses the registration endpoint without exposing a verification token", async ({ page }) => {
  const requests = await mocks(page, false);
  await page.goto("/register");
  await page.getByRole("textbox", { name: "Username", exact: true }).fill("Synthetic signup");
  await page.getByRole("textbox", { name: "Email", exact: true }).fill("signup@example.test");
  await page.getByLabel(/^Password/).fill("synthetic-signup-password");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(requests).toContain("/api/v1/auth/register");
  expect(requests).not.toContain("/api/v1/onboarding/register");
  await expect(page.getByRole("button", { name: "Sign In", exact: true })).toBeVisible();
});
test("checkout return requires canonical activation and expired billing is retained", async ({ page }) => {
  await mocks(page, true, { activation: true, expired: true });
  await page.goto("/profile?checkout=success");
  await expect(page.getByText(/Processing subscription access/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Manage Billing" })).toBeVisible();
  await expect(page.getByText("Premium access confirmed.")).toBeVisible();
  await expect(page.getByText("Premium active")).toBeVisible();
  await page.getByRole("button", { name: "Resend email verification" }).click();
  await expect(page.getByText(/If this address is eligible/)).toBeVisible();
});

test("unconfirmed checkout times out safely and supports accessible refresh", async ({ page }) => {
  const requests = await mocks(page, true);
  await page.goto("/profile?checkout=success");
  await expect(page.getByText(/Processing subscription access/)).toBeVisible();
  await expect(page.getByText(/Access is not confirmed yet/)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Premium active")).toHaveCount(0);
  const calls = requests.filter((path) => path === "/api/v1/subscriptions/me").length;
  await page.waitForTimeout(2500);
  expect(requests.filter((path) => path === "/api/v1/subscriptions/me")).toHaveLength(calls);
  const refresh = page.getByRole("button", { name: "Refresh access" });
  await refresh.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText(/Processing subscription access/)).toBeVisible();
  await expect(page.getByText("Free Preview access")).toBeVisible();
});

test("canceled and failed checkout returns never grant paid access", async ({ page }) => {
  await mocks(page, true);
  await page.goto("/profile?checkout=canceled");
  await expect(page.getByText(/Checkout was canceled/)).toBeVisible();
  await expect(page.getByText("Free Preview access")).toBeVisible();
  await page.goto("/profile?checkout=failed");
  await expect(page.getByText(/Checkout could not be completed/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Refresh access" })).toBeVisible();
  await expect(page.getByText("Premium active")).toHaveCount(0);
});
