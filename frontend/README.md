# Frontend Architecture Layers

## Layer scheme
- `app` — application bootstrap, routing, global providers.
- `pages` — screen-level composition and route entry pages.
- `features` — business capabilities grouped by user scenario.
- `entities` — domain entities and their reusable logic (when explicitly extracted).
- `shared` — cross-cutting reusable modules:
  - `ui`
  - `api-client`
  - `lib`
  - `config`

## Mapping for current structure
- `src/API/*` → `shared/api`
- `src/ui/*` → `shared/ui`
- `src/features/*` remains feature-oriented modules

## Import boundaries
- Cross-feature imports are allowed only via public entrypoints.
- Public entrypoint for each feature is `src/features/<feature>/index.js`.
- Direct imports from another feature internals are forbidden.

Examples:
- ✅ `@features/auth`
- ❌ `@features/auth/components/AuthModal`
