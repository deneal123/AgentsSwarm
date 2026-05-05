const { test, expect } = require('@playwright/test');

test.describe('Authentication and limits', () => {
  test('guest user can make requests within limit', async ({ page }) => {
    const base = process.env.E2E_BASE_URL || 'http://localhost:3000';

    // Mock successful chat API
    await page.route('**/api/chats/**', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Success response',
          thread_id: 'guest_thread_123'
        }),
      });
    });

    await page.goto(base, { waitUntil: 'domcontentloaded' });

    // Check initial request count
    await expect(page.locator('text=/Осталось запросов: 10/')).toBeVisible();

    // Send a message
    const searchInput = page.locator('input[placeholder*="запрос"]');
    await searchInput.fill('Test message');
    await page.locator('button').filter({ hasText: 'отправить' }).click();

    // Should navigate to chat
    await expect(page).toHaveURL(/.*\/chat\/.*/);

    // Go back to home
    await page.goto(base);

    // Check updated request count
    await expect(page.locator('text=/Осталось запросов: 9/')).toBeVisible();
  });

  test('guest user sees auth modal when limit exceeded', async ({ page }) => {
    const base = process.env.E2E_BASE_URL || 'http://localhost:3000';

    // Mock localStorage with exhausted limit
    await page.addInitScript(() => {
      localStorage.setItem('guest_session', JSON.stringify({
        guestId: 'guest_123',
        requestCount: 10,
        lastRequestDate: new Date().toISOString()
      }));
    });

    // Mock API error for limit exceeded
    await page.route('**/api/chats/**', route => {
      route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Rate limit exceeded',
          message: 'Превышен лимит бесплатных запросов'
        }),
      });
    });

    await page.goto(base, { waitUntil: 'domcontentloaded' });

    // Check that limit is exceeded
    await expect(page.locator('text=/Осталось запросов: 0/')).toBeVisible();

    // Try to send message
    const searchInput = page.locator('input[placeholder*="запрос"]');
    await searchInput.fill('Test message');
    await page.locator('button').filter({ hasText: 'отправить' }).click();

    // Should show auth modal
    await expect(page.locator('text=/Требуется регистрация/')).toBeVisible();
    await expect(page.locator('text=/Превышен лимит/')).toBeVisible();

    // Should have register and login buttons
    await expect(page.locator('button').filter({ hasText: 'Зарегистрироваться' })).toBeVisible();
    await expect(page.locator('button').filter({ hasText: 'Войти в аккаунт' })).toBeVisible();
  });

  test('guest user sees auth modal for calendar generation', async ({ page }) => {
    const base = process.env.E2E_BASE_URL || 'http://localhost:3000';

    // Mock API response indicating calendar requires auth
    await page.route('**/api/chats/**', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Для создания календаря требуется регистрация',
          requires_auth: true,
          thread_id: 'calendar_thread_123'
        }),
      });
    });

    await page.goto(base, { waitUntil: 'domcontentloaded' });

    // Send calendar request
    const searchInput = page.locator('input[placeholder*="запрос"]');
    await searchInput.fill('Создай календарь питания на неделю');
    await page.locator('button').filter({ hasText: 'отправить' }).click();

    // Should show auth modal for calendar feature
    await expect(page.locator('text=/Требуется регистрация/')).toBeVisible();
    await expect(page.locator('text=/календарей требуется регистрация/')).toBeVisible();
  });

  test('auth modal navigation works', async ({ page }) => {
    const base = process.env.E2E_BASE_URL || 'http://localhost:3000';

    // Mock exhausted limit
    await page.addInitScript(() => {
      localStorage.setItem('guest_session', JSON.stringify({
        guestId: 'guest_123',
        requestCount: 10,
        lastRequestDate: new Date().toISOString()
      }));
    });

    await page.route('**/api/chats/**', route => {
      route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Rate limit exceeded' }),
      });
    });

    await page.goto(base, { waitUntil: 'domcontentloaded' });

    // Trigger auth modal
    const searchInput = page.locator('input[placeholder*="запрос"]');
    await searchInput.fill('Test');
    await page.locator('button').filter({ hasText: 'отправить' }).click();

    // Click register button
    await page.locator('button').filter({ hasText: 'Зарегистрироваться' }).click();

    // Should navigate to register page
    await expect(page).toHaveURL(/.*\/register/);
  });

  test('daily limit reset works', async ({ page }) => {
    const base = process.env.E2E_BASE_URL || 'http://localhost:3000';

    // Mock localStorage with yesterday's date
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);

    await page.addInitScript(({ yesterday }) => {
      localStorage.setItem('guest_session', JSON.stringify({
        guestId: 'guest_123',
        requestCount: 10,
        lastRequestDate: yesterday.toISOString()
      }));
    }, { yesterday });

    await page.goto(base, { waitUntil: 'domcontentloaded' });

    // Should show reset limit
    await expect(page.locator('text=/Осталось запросов: 10/')).toBeVisible();
  });

  test('user can register from auth modal', async ({ page }) => {
    const base = process.env.E2E_BASE_URL || 'http://localhost:3000';

    // Mock exhausted limit
    await page.addInitScript(() => {
      localStorage.setItem('guest_session', JSON.stringify({
        guestId: 'guest_123',
        requestCount: 10,
        lastRequestDate: new Date().toISOString()
      }));
    });

    await page.route('**/api/chats/**', route => {
      route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Rate limit exceeded' }),
      });
    });

    await page.goto(base, { waitUntil: 'domcontentloaded' });

    // Trigger auth modal
    const searchInput = page.locator('input[placeholder*="запрос"]');
    await searchInput.fill('Test');
    await page.locator('button').filter({ hasText: 'отправить' }).click();

    // Click register button
    await page.locator('button').filter({ hasText: 'Зарегистрироваться' }).click();

    // Should be on register page
    await expect(page).toHaveURL(/.*\/register/);

    // Should have register form
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('user can login from auth modal', async ({ page }) => {
    const base = process.env.E2E_BASE_URL || 'http://localhost:3000';

    // Mock exhausted limit
    await page.addInitScript(() => {
      localStorage.setItem('guest_session', JSON.stringify({
        guestId: 'guest_123',
        requestCount: 10,
        lastRequestDate: new Date().toISOString()
      }));
    });

    await page.route('**/api/chats/**', route => {
      route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Rate limit exceeded' }),
      });
    });

    await page.goto(base, { waitUntil: 'domcontentloaded' });

    // Trigger auth modal
    const searchInput = page.locator('input[placeholder*="запрос"]');
    await searchInput.fill('Test');
    await page.locator('button').filter({ hasText: 'отправить' }).click();

    // Click login button
    await page.locator('button').filter({ hasText: 'Войти в аккаунт' }).click();

    // Should be on login page
    await expect(page).toHaveURL(/.*\/login/);

    // Should have login form
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });
});
