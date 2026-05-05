const { test, expect } = require('@playwright/test');

test.describe('Basic User Interactions', () => {
  test('homepage loads and shows search interface', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Check for main elements
    await expect(page.locator('input[placeholder*="Спросите"]')).toBeVisible();
    await expect(page.locator('button')).toBeVisible();
  });

  test('can type in search input', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    const searchInput = page.locator('input[placeholder*="Спросите"]').first();
    await searchInput.fill('Test query');

    await expect(searchInput).toHaveValue('Test query');
  });

  test('shows requests counter', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    await expect(page.locator('text=/Осталось запросов/')).toBeVisible();
  });

  test('page is responsive', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 }); // Mobile
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    await expect(page.locator('input[placeholder*="Спросите"]')).toBeVisible();
  });
});
