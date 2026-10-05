import { defineConfig, devices } from "@playwright/test";

// The screenshot gallery (e2e/gallery.spec.ts): the real backend, as in the end-to-end tests, but one
// fresh instance per device so that both start from the claim page and run side by side. Every screen
// is saved in light and dark. `pnpm run shots`.
const stamp = Date.now();
const SERVERS = [
  { name: "phone", port: 8791, device: devices["Pixel 7"] },
  {
    name: "tablet",
    port: 8793,
    device: {
      ...devices["Desktop Chrome"],
      viewport: { width: 820, height: 1180 },
      isMobile: true,
      hasTouch: true,
    },
  },
  {
    name: "desktop",
    port: 8792,
    device: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } },
  },
];

export default defineConfig({
  testDir: "e2e",
  testMatch: /gallery\.spec\.ts/,
  outputDir: "test-results-gallery", // not test-results: a journey run at the same time would be wiped
  timeout: 300_000,
  expect: { timeout: 15_000 },
  fullyParallel: true,
  workers: SERVERS.length,
  reporter: "list",
  use: { locale: "en-GB", trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: SERVERS.map((server) => ({
    name: server.name,
    use: { ...server.device, baseURL: `http://127.0.0.1:${server.port}` },
  })),
  webServer: SERVERS.map((server) => ({
    command: "uv run nevus serve",
    cwd: "../backend",
    url: `http://127.0.0.1:${server.port}/healthz`,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      NEVUS_DATA_DIR: process.env.NEVUS_E2E_DATA ?? `/tmp/nevus-gallery-${stamp}-${server.name}`,
      NEVUS_PORT: String(server.port),
      NEVUS_BIND: "127.0.0.1",
      NEVUS_ALLOWED_HOSTS: "localhost",
      NEVUS_LOG_LEVEL: "warning",
      NEVUS_STATIC_DIR: `${process.cwd()}/dist`,
      NEVUS_JOB_POLL_SECONDS: "0.3",
      NEVUS_WEB_PUSH: "1",
    },
  })),
});
