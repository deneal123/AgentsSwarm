import { Box, keyframes } from "@chakra-ui/react";

/**
 * PageTransition - компонент для плавного появления страниц
 * Использует чистые CSS анимации вместо framer-motion для совместимости с iOS Safari
 */

const fadeInUp = keyframes`
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

export default function PageTransition({ children }) {
  return (
    <Box
      animation={`${fadeInUp} 0.3s ease-out forwards`}
      sx={{
        "@media (prefers-reduced-motion: reduce)": {
          animation: "none",
        },
      }}
    >
      {children}
    </Box>
  );
}

export function PageTransitionItem({ children, ...props }) {
  return <Box {...props}>{children}</Box>;
}
