# UI Kit Rules

- All reusable UI components must be placed in `src/shared/ui`.
- Feature components must not import other feature internals directly.
- Cross-feature usage is allowed only through each feature public API (`features/<feature>/index.js`).
- UI styling must use tokens from `src/theme/tokens.js`.
- Motion and visual primitives must be imported from `src/shared/ui/lib`.
