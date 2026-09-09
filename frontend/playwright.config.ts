import crypto from "node:crypto";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));
const backendRoot = path.resolve(frontendRoot, "../backend");
const runtimeId = crypto.createHash("sha256").update(frontendRoot.toLowerCase()).digest("hex").slice(0, 12);
const runtimeRoot = path.join(os.tmpdir(), `store-admin-e2e-${runtimeId}`);
const databasePath = path.join(runtimeRoot, "store-e2e.db").replaceAll("\\", "/");
const mediaRoot = path.join(runtimeRoot, "media");
const databaseUrl = `sqlite:///${databasePath}`;
const apiBaseUrl = "http://127.0.0.1:8013/api/v1";

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "**/*.spec.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 30_000,
  expect: { timeout: 8_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:5193",
    locale: "fa-IR",
    timezoneId: "Asia/Tehran",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "python ../backend/tests/e2e/start_backend.py",
      cwd: frontendRoot,
      url: "http://127.0.0.1:8013/ready",
      timeout: 60_000,
      reuseExistingServer: false,
      env: {
        ...process.env,
        E2E_RUNTIME_ROOT: runtimeRoot,
        DATABASE_URL: databaseUrl,
        MEDIA_ROOT: mediaRoot,
        SECRET_KEY: "e2e-only-secret-never-use-outside-tests",
        DEFAULT_ADMIN_USERNAME: "e2e-admin",
        DEFAULT_ADMIN_PASSWORD: "e2e-password-123",
        DEFAULT_ADMIN_FULL_NAME: "مدیر تست مرورگر",
        BALE_POLLING_FALLBACK: "false",
      },
    },
    {
      command: "pnpm exec vite --host 127.0.0.1 --port 5193 --strictPort",
      cwd: frontendRoot,
      url: "http://127.0.0.1:5193/admin",
      timeout: 60_000,
      reuseExistingServer: false,
      env: { ...process.env, VITE_API_BASE_URL: apiBaseUrl },
    },
  ],
  projects: [
    {
      name: "desktop-chrome",
      use: { ...devices["Desktop Chrome"], channel: "chrome", viewport: { width: 1440, height: 900 } },
    },
    {
      name: "mobile-chrome-390x844",
      use: {
        ...devices["Desktop Chrome"],
        channel: "chrome",
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
});
