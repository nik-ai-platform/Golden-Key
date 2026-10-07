import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "customer-launch.spec.ts",
  timeout: 60_000,
  fullyParallel: false,
  retries: 0,
  outputDir: "./customer-launch-artifacts",
  use: { baseURL: "http://127.0.0.1:4197", trace: "retain-on-failure" },
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 4197 --strictPort",
    url: "http://127.0.0.1:4197",
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
