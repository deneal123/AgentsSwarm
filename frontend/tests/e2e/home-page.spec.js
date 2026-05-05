const { test, expect } = require('@playwright/test');

test.describe('Home Page', () => {
  test('loads successfully', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Check basic elements
    await expect(page.locator('body')).toBeVisible();

    // Check for main search interface
    const searchInput = page.locator('input[placeholder*="запрос"]').or(
      page.locator('[data-testid="search-input"]')
    );
    await expect(searchInput).toBeVisible();

    // Check for send button
    const sendButton = page.locator('button').filter({ hasText: 'отправить' }).or(
      page.locator('[data-testid="send-button"]')
    );
    await expect(sendButton).toBeVisible();
  });

  test('shows remaining requests counter', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Should show requests counter
    await expect(page.locator('text=/Осталось запросов/')).toBeVisible();
  });

  test('allows typing in search input', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    const searchInput = page.locator('input[placeholder*="запрос"]').first();
    await searchInput.fill('Test query');

    await expect(searchInput).toHaveValue('Test query');
  });

  test('navigates to chat on form submission', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Mock API response
    await page.route('**/api/chats**', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'AI response',
          thread_id: 'test_thread_123'
        }),
      });
    });

    const searchInput = page.locator('input[placeholder*="запрос"]').first();
    const sendButton = page.locator('button').filter({ hasText: 'отправить' }).first();

    await searchInput.fill('Hello AI');
    await sendButton.click();

    // Should navigate to chat or show chat interface
    await expect(page.locator('text=/Осталось запросов: 9/')).toBeVisible();
  });
});
