const { test, expect } = require('@playwright/test');

test('smoke: home page loads and shows AI chat interface', async ({ page }) => {
  const base = process.env.E2E_BASE_URL || 'http://localhost:3000';
  await page.goto(base, { waitUntil: 'domcontentloaded' });

  // Basic smoke assertions
  await expect(page.locator('body')).toBeVisible();

  // Check for main elements of AI chat interface
  await expect(page.locator('[data-testid="search-input"]')).toBeVisible();
  await expect(page.locator('text=/Осталось запросов/')).toBeVisible();

  // Check for animated suggestions
  await expect(page.locator('text=/Что мне сегодня/')).toBeVisible();

  // Check for navigation elements
  await expect(page.locator('nav')).toBeVisible();
});
