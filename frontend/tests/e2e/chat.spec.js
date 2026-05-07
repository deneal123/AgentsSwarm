const { test, expect } = require('@playwright/test');

test.describe('Chat functionality', () => {
  test('user can send message and receive AI response', async ({ page }) => {
    const base = process.env.E2E_BASE_URL || 'http://localhost:3000';

    // Intercept chat API calls
    await page.route('**/api/chats/**', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'AI response received',
          thread_id: 'test_thread_123'
        }),
      });
    });

    await page.route('**/api/chats/test_thread_123/ws', route => {
      // Mock WebSocket connection
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'connected' }),
      });
    });

    await page.goto(base, { waitUntil: 'domcontentloaded' });

    // Find search input
    const searchInput = page.locator('[data-testid="search-input"]').or(
      page.locator('input[placeholder*="запрос"]')
    );

    await expect(searchInput).toBeVisible();

    // Type a message
    await searchInput.fill('Расскажи о здоровом питании');

    // Click send button
    const sendButton = page.locator('button').filter({ hasText: 'отправить' }).or(
      page.locator('[data-testid="send-button"]')
    );

    await sendButton.click();

    // Should navigate to chat page
    await expect(page).toHaveURL(/.*\/chat\/.*/);

    // Should show loading or typing indicator
    await expect(page.locator('text=/печатает/').or(page.locator('[data-testid="typing-indicator"]'))).toBeVisible();

    // Mock AI response via WebSocket simulation
    await page.evaluate(() => {
      // Simulate receiving AI response
      window.postMessage({
        type: 'ai_response',
        data: 'Здоровое питание включает в себя сбалансированное потребление овощей, фруктов, белков и углеводов.'
      }, '*');
    });

    // Should show AI response
    await expect(page.locator('text=/Здоровое питание/')).toBeVisible();
  });

  test('guest user sees remaining requests counter', async ({ page }) => {
    const base = process.env.E2E_BASE_URL || 'http://localhost:3000';
    await page.goto(base, { waitUntil: 'domcontentloaded' });

    // Check for remaining requests counter
    await expect(page.locator('text=/Осталось запросов/')).toBeVisible();
  });

  test('user can access voice recording', async ({ page }) => {
    const base = process.env.E2E_BASE_URL || 'http://localhost:3000';
    await page.goto(base, { waitUntil: 'domcontentloaded' });

    // Navigate to chat
    const searchInput = page.locator('input[placeholder*="запрос"]');
    await searchInput.fill('Test message');
    await page.locator('button').filter({ hasText: 'отправить' }).click();

    await expect(page).toHaveURL(/.*\/chat\/.*/);

    // Should have voice recording option
    const voiceButton = page.locator('button').filter({ hasText: /голос/ }).or(
      page.locator('[data-testid="voice-button"]')
    );

    await expect(voiceButton).toBeVisible();
  });

  test('user can switch between chat threads', async ({ page }) => {
    const base = process.env.E2E_BASE_URL || 'http://localhost:3000';
    await page.goto(base, { waitUntil: 'domcontentloaded' });

    // Start first chat
    const searchInput = page.locator('input[placeholder*="запрос"]');
    await searchInput.fill('First chat');
    await page.locator('button').filter({ hasText: 'отправить' }).click();

    await expect(page).toHaveURL(/.*\/chat\/.*/);

    // Go back to home
    await page.goto(base);

    // Start second chat
    await searchInput.fill('Second chat');
    await page.locator('button').filter({ hasText: 'отправить' }).click();

    // Should be in different chat thread
    await expect(page).toHaveURL(/.*\/chat\/.*/);
    await expect(page.url()).not.toContain('first-chat');
  });

  test('restores active chat session after page refresh', async ({ page }) => {
    const base = process.env.E2E_BASE_URL || 'http://localhost:3000';
    await page.goto(base, { waitUntil: 'domcontentloaded' });

    const searchInput = page.locator('input[placeholder*="запрос"]');
    await searchInput.fill('Session restore test');
    await page.locator('button').filter({ hasText: 'отправить' }).click();

    await expect(page).toHaveURL(/.*\/chat\/.*/);
    const chatUrlBeforeReload = page.url();

    await page.reload({ waitUntil: 'domcontentloaded' });

    await expect(page).toHaveURL(chatUrlBeforeReload);
    await expect(page.locator('input[placeholder*="запрос"]').first()).toBeVisible();
  });

  test('user can use keyboard shortcuts', async ({ page }) => {
    const base = process.env.E2E_BASE_URL || 'http://localhost:3000';
    await page.goto(base, { waitUntil: 'domcontentloaded' });

    const searchInput = page.locator('input[placeholder*="запрос"]');

    // Focus input and type
    await searchInput.focus();
    await page.keyboard.type('Test message');

    // Send with Enter
    await page.keyboard.press('Enter');

    // Should navigate to chat
    await expect(page).toHaveURL(/.*\/chat\/.*/);
  });

  test('responsive design works on mobile', async ({ page }) => {
    const base = process.env.E2E_BASE_URL || 'http://localhost:3000';

    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto(base, { waitUntil: 'domcontentloaded' });

    // Check that search interface is visible and usable
    const searchInput = page.locator('input[placeholder*="запрос"]');
    await expect(searchInput).toBeVisible();

    // Check that suggestions are adapted for mobile
    await expect(page.locator('text=/Что мне сегодня/')).toBeVisible();
  });
});
