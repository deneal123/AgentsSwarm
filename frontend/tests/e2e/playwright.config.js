const { defineConfig, devices } = require("@playwright/test");

module.exports = defineConfig({
  testDir: __dirname,
  timeout: 30 * 1000,
  retries: 0,
  use: {
    headless: true,
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    // Save full trace and screenshots for each run to aid debugging in CI/artifacts
    trace: 'on',
    screenshot: 'on',
    video: 'retain-on-failure',
  },
  // Store Playwright report and attachments in repo-level tmp_e2e for CI artifact collection
  outputDir: '../../tmp_e2e/playwright-report',
  // Start a lightweight static server for the built frontend when running tests.
  // This avoids requiring an external step in CI or local runs.
  webServer: {
    command: "npx http-server ../build -p 3000",
    port: 3000,
    reuseExistingServer: true,
    timeout: 30 * 1000,
  },
  projects: [
    // Desktop браузеры
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
    // Мобильные устройства
    {
      name: "mobile-chrome",
      use: { ...devices["Pixel 5"] },
    },
    {
      name: "mobile-safari",
      use: { ...devices["iPhone 12"] },
    },
    // Планшеты
    {
      name: "tablet",
      use: { ...devices["iPad (gen 7)"] },
    },
    // Тест на мобильном с ландшафтной ориентацией
    {
      name: "mobile-landscape",
      use: {
        ...devices["Pixel 5"],
        viewport: { width: 851, height: 393 },
      },
    },
  ],
  // Настройка для новых тестов
  use: {
    ...use,
    // Увеличиваем таймауты для более реалистичных тестов
    actionTimeout: 10000,
    navigationTimeout: 30000,
  },
});
