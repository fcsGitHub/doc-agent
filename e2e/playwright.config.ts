import { defineConfig, devices } from "@playwright/test";

process.env.LITELLM_MOCK = process.env.LITELLM_MOCK ?? "true";

export default defineConfig({
  testDir: ".",
  testMatch: ["smoke.test.ts"],
  timeout: 120000,
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        browserName: "chromium",
      },
    },
  ],
  metadata: {
    frontendURL: "http://localhost:3000",
    backendURL: "http://localhost:8000",
    litellmMock: process.env.LITELLM_MOCK,
  },
});
