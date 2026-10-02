import { defineConfig, devices } from "@playwright/test";

// End-to-end on a phone-sized Chromium against the real backend serving the built bundle.
// `pnpm build` first; the backend gets a fresh data directory for every run.
const port = 8790;
const dataDir = process.env.NEVUS_E2E_DATA ?? `/tmp/nevus-e2e-${Date.now()}`;

export default defineConfig({
  testDir: "e2e",
  testIgnore: /gallery\.spec\.ts/,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: { baseURL: `http://127.0.0.1:${port}`, trace: "retain-on-failure", locale: "en-GB" },
  projects: [{ name: "phone", use: { ...devices["Pixel 7"] } }],
  webServer: {
    command: "uv run nevus serve",
    cwd: "../backend",
    url: `http://127.0.0.1:${port}/healthz`,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      NEVUS_DATA_DIR: dataDir,
      NEVUS_PORT: String(port),
      NEVUS_BIND: "127.0.0.1",
      NEVUS_ALLOWED_HOSTS: "localhost",
      NEVUS_LOG_LEVEL: "warning",
      NEVUS_STATIC_DIR: `${process.cwd()}/dist`,
      NEVUS_JOB_POLL_SECONDS: "0.3",
      NEVUS_WEB_PUSH: "1",
    },
  },
});
