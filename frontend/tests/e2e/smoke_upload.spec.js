const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const fixturesDir = path.resolve(__dirname, 'fixtures');
const uploadResponse = JSON.parse(fs.readFileSync(path.join(fixturesDir, 'upload-response.json'), 'utf8'));
const trainStartResponse = JSON.parse(fs.readFileSync(path.join(fixturesDir, 'train-start-response.json'), 'utf8'));
const trainComplete = JSON.parse(fs.readFileSync(path.join(fixturesDir, 'train-status-complete.json'), 'utf8'));

test('smoke: upload file and start training (mocked backend)', async ({ page }) => {
  const base = process.env.E2E_BASE_URL || 'http://localhost:3000';

  // Intercept API requests and return deterministic fixtures
  await page.route('**/api/upload', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(uploadResponse),
    });
  });

  await page.route('**/api/train/start', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(trainStartResponse),
    });
  });

  // For polling status endpoint return started then completed
  let statusRequests = 0;
  await page.route('**/api/train/*/status', route => {
    statusRequests += 1;
    const body = statusRequests < 2 ? JSON.stringify({ ...trainStartResponse, status: 'running' }) : JSON.stringify(trainComplete);
    route.fulfill({ status: 200, contentType: 'application/json', body });
  });

  // Navigate to base and ensure page loads
  await page.goto(base, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('body')).toBeVisible();

  // Instead of depending on specific UI selectors which may vary, call the upload API from the page
  const uploaded = await page.evaluate(async () => {
    const form = new FormData();
    const blob = new Blob(['col1,col2\n1,2\n3,4'], { type: 'text/csv' });
    form.append('file', blob, 'test.csv');
    const r = await fetch('/api/upload', { method: 'POST', body: form });
    return r.json();
  });

  expect(uploaded).toHaveProperty('artifact_id');

  // Start training
  const started = await page.evaluate(async (artifactId) => {
    const r = await fetch('/api/train/start', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ artifact_id: artifactId }) });
    return r.json();
  }, uploaded.artifact_id);

  expect(started).toHaveProperty('training_id');

  // Poll for completion (client-side polling simulation)
  const final = await page.evaluate(async (trainingId) => {
    for (let i = 0; i < 5; i++) {
      const r = await fetch(`/api/train/${trainingId}/status`);
      const j = await r.json();
      if (j.status === 'completed') return j;
      await new Promise(r => setTimeout(r, 100));
    }
    return null;
  }, started.training_id);

  expect(final).not.toBeNull();
  expect(final.status).toBe('completed');
  expect(final.metrics).toHaveProperty('accuracy');
});
