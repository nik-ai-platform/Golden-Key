import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/**", async (route) => {
    if (route.request().url().includes("/users/me")) {
      await route.fulfill({ json: { id: 1, username: "education-preview", email: "preview@example.com", role: "user", is_active: true } });
    } else {
      await route.fulfill({ status: 404, json: { detail: "Unmocked education preview request" } });
    }
  });
  await page.addInitScript(() => localStorage.setItem("golden_key_access_token", "local-education-token"));
});

for (const width of [320, 390, 600, 900, 1440]) {
  test(`education is readable and navigable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/how-it-works");
    await expect(page.getByRole("heading", { level: 1, name: "How to read a pick" })).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    for (const name of ["What the numbers mean", "Why NPI depends on the market", "About NPI score ranges", "What “projected edge” compares", "How Risk Level is labeled", "How picks are chosen", "A note on uncertainty"]) {
      const section = page.getByRole("region", { name });
      await section.scrollIntoViewIfNeeded();
      await expect(section).toBeVisible();
      const bounds = (await section.boundingBox())!;
      expect(bounds.x).toBeGreaterThanOrEqual(0);
      expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
    }
    await expect(page.getByRole("region", { name: "About NPI score ranges" })).toContainText("There are no named NPI strength levels");
    await expect(page.getByRole("region", { name: "What the numbers mean" })).toContainText("Confidence is not win probability");
    await expect(page.getByRole("navigation", { name: "On this page" }).getByRole("link", { name: "How picks are chosen" })).toHaveAttribute("href", "#how-picks-are-chosen");
    if (width < 600) {
      const nav = page.getByTestId("mobile-navigation-shell");
      await expect(nav.getByRole("button")).toHaveCount(6);
      await page.locator("footer").scrollIntoViewIfNeeded();
      const footer = (await page.locator("footer").boundingBox())!;
      expect(footer.y + footer.height).toBeLessThan((await nav.boundingBox())!.y);
      await page.getByRole("button", { name: "Open navigation" }).focus();
      await page.keyboard.press("Enter");
    }
    const link = page.getByRole("link", { name: "How It Works" });
    await expect(link).toBeVisible();
    await expect(link).toHaveAttribute("aria-current", "page");
    await link.focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/how-it-works$/);
  });
}
