import React from "react";
import { Box, keyframes } from "@chakra-ui/react";
import { Outlet, useLocation } from "react-router-dom";
import Header from "./Header";
import Footer from "./Footer";
import { colors, spacing } from "@theme/tokens";
import { ScrollToTop } from "@shared/ui/atoms";
import { isChatRoute, shouldUseFullWidthLayout } from "@routes/routeState";

// CSS animation for page transitions - works on iOS Safari
const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
`;

function PublicLayout() {
  const location = useLocation();
  const isWorkspacePage = isChatRoute(location.pathname);
  const isFullWidthPage = shouldUseFullWidthLayout(location.pathname);

  return (
    <Box position="relative" bg={colors.background.darkPrimary} w="100%">
      <ScrollToTop />

      {/* Background gradient - pointer-events: none is critical! */}
      <Box
        position="fixed"
        top={0}
        left={0}
        right={0}
        bottom={0}
        bg="linear-gradient(180deg, rgba(5,5,5,0.9) 0%, rgba(5,5,5,0.75) 35%, rgba(5,5,5,0.95) 100%)"
        opacity={0.9}
        pointerEvents="none"
        zIndex={0}
      />

      {!isWorkspacePage && (
        <Box position="sticky" top={0} zIndex={100}>
          <Header />
        </Box>
      )}

      {/* Main content - uses CSS animation instead of framer-motion */}
      <Box
        as="main"
        position="relative"
        zIndex={1}
        key={location.pathname}
        animation={`${fadeIn} 0.3s ease-out forwards`}
        sx={{ "@media (prefers-reduced-motion: reduce)": { animation: "none" } }}
      >
        {isFullWidthPage ? (
          <Outlet />
        ) : (
          <Box
            maxW="6xl"
            mx="auto"
            py={{ base: 10, md: 14 }}
            px={{ base: spacing.md, md: spacing.lg, lg: spacing[13] }}
          >
            <Outlet />
          </Box>
        )}
      </Box>

      {!isWorkspacePage && (
        <Box position="relative" zIndex={1}>
          <Footer />
        </Box>
      )}
    </Box>
  );
}

export default PublicLayout;
