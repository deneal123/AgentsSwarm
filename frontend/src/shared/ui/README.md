# UI Kit Rules

- All reusable UI components must be placed in `src/shared/ui`.
- Feature components must not import other feature internals directly.
- Cross-feature usage is allowed only through each feature public API (`features/<feature>/index.js`).
- Feature styling must use tokens from `src/theme/tokens.js` and semantic classes from `src/xy-theme.css`.
- Direct raw colors (`#fff`, `rgb(...)`, `rgba(...)`) and literal spacing in feature components are запрещены.

## Required token usage examples

```jsx
import { Box } from '@chakra-ui/react';
import { colors, spacing, borderRadius } from '@theme/tokens';

<Box bg={colors.background.surface} px={spacing.lg} py={spacing.md} borderRadius={borderRadius.lg} />
```

```jsx
import { PrimaryButton, SecondaryButton, Title, Body } from '@ui';

<Title variant="medium">Заголовок</Title>
<Body variant="medium">Текст секции</Body>
<PrimaryButton size="md">Продолжить</PrimaryButton>
<SecondaryButton size="md">Отмена</SecondaryButton>
```
