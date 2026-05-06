# Deprecated API compatibility layer

This directory is a temporary compatibility layer.

## Current contract
- Use `src/shared/api` and `src/shared/api/*` for all new imports.
- `src/API/index.js` remains only for backward compatibility during migration.

## Removal plan
1. Keep only `src/API/index.js` as a minimal re-export entrypoint.
2. Remove all `src/API/*` deep module imports in the app code.
3. Remove `src/API/index.js` after one release cycle without incoming `src/API` imports.
4. Keep import checks in CI to prevent reintroduction of `src/API/*` imports.
