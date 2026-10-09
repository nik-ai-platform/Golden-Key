import { defineConfig } from "@playwright/test";
import customerLaunch from "./playwright.customer-launch.config";

export default defineConfig({
  ...customerLaunch,
  testMatch: ["customer-launch.spec.ts", "cyan-dashboard.spec.ts"],
  workers: 1,
  webServer: {
    command: "npm run preview -- --host 127.0.0.1 --port 4197 --strictPort",
    url: "http://127.0.0.1:4197",
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
