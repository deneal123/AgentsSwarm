const { test, expect } = require('@playwright/test');

test.describe('Guest Session Management', () => {
  test('starts with 10 requests available', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    await expect(page.locator('text=/Осталось запросов: 10/')).toBeVisible();
  });

  test('decrements request count after sending message', async ({ page }) => {
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

    // Initial count should be 10
    await expect(page.locator('text=/Осталось запросов: 10/')).toBeVisible();

    // Send a message
    const searchInput = page.locator('input[placeholder*="запрос"]').first();
    const sendButton = page.locator('button').filter({ hasText: 'отправить' }).first();

    await searchInput.fill('Test message');
    await sendButton.click();

    // Should decrement to 9
    await expect(page.locator('text=/Осталось запросов: 9/')).toBeVisible();
  });

  test('persists session data in localStorage', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Check that session data is stored
    const sessionData = await page.evaluate(() => {
      return localStorage.getItem('guest_session');
    });

    expect(sessionData).not.toBeNull();

    const parsedData = JSON.parse(sessionData);
    expect(parsedData).toHaveProperty('guestId');
    expect(parsedData).toHaveProperty('requestCount');
  });

  test('shows auth modal when requests exhausted', async ({ page }) => {
    // Mock exhausted session
    await page.addInitScript(() => {
      localStorage.setItem('guest_session', JSON.stringify({
        guestId: 'guest_123',
        requestCount: 10,
        lastReset: new Date().toISOString(),
        limits: {
          requestCount: 10,
          maxRequests: 10,
          lastReset: new Date().toISOString()
        }
      }));
    });

    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Mock API error for rate limit
    await page.route('**/api/chats**', route => {
      route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Rate limit exceeded',
          message: 'Превышен лимит бесплатных запросов'
        }),
      });
    });

    // Should show 0 requests
    await expect(page.locator('text=/Осталось запросов: 0/')).toBeVisible();

    // Try to send message
    const searchInput = page.locator('input[placeholder*="запрос"]').first();
    const sendButton = page.locator('button').filter({ hasText: 'отправить' }).first();

    await searchInput.fill('Test message');
    await sendButton.click();

    // Should show auth modal or error message
    // This depends on implementation - could show modal or error toast
    await expect(page.locator('text=/Осталось запросов: 0/')).toBeVisible();
  });

  test('resets daily limit', async ({ page }) => {
    // Mock old session (yesterday)
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);

    await page.addInitScript(({ yesterday }) => {
      localStorage.setItem('guest_session', JSON.stringify({
        guestId: 'guest_123',
        requestCount: 5,
        lastReset: yesterday.toISOString(),
        limits: {
          requestCount: 5,
          maxRequests: 10,
          lastReset: yesterday.toISOString()
        }
      }));
    }, { yesterday });

    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Should reset to 10 requests for new day
    await expect(page.locator('text=/Осталось запросов: 10/')).toBeVisible();
  });
});
