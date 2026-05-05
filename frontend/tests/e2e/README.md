Playwright E2E smoke tests

Quick start:

- Install dependencies (from repo root):

  npm ci --prefix frontend

- Install Playwright browsers:

  npm --prefix frontend run e2e:install

- Run the smoke tests (expects the frontend server running at http://localhost:3000):

  E2E_BASE_URL=http://localhost:3000 npm --prefix frontend run e2e:run

Notes:
- The test suite is intentionally minimal (one smoke test) so it can be used as a fast check in CI or locally.
- Use `workflow_dispatch` GH Action to run these on-demand in CI (there is a sample workflow under `.github/workflows/playwright-smoke.yml`).
