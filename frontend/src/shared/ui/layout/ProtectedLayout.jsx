import React from "react";
import { Box, keyframes } from "@chakra-ui/react";
import { Outlet, useLocation } from "react-router-dom";
import Header from "./Header";
import Footer from "./Footer";
import LayoutContext from "@context/LayoutContext";
import { gradients, colors, spacing } from "@theme/tokens";
import { ScrollToTop } from "@shared/ui/atoms";

// CSS animation for page transitions - works on iOS Safari
const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
`;

function ProtectedLayout() {
  const location = useLocation();
  const [layoutVariant, setLayoutVariant] = React.useState("container");
  const [isFooterVisible, setFooterVisible] = React.useState(true);

  React.useEffect(() => {
    setLayoutVariant("container");
    setFooterVisible(true);
  }, [location.pathname]);

  const layoutContextValue = React.useMemo(
    () => ({
      variant: layoutVariant,
      setVariant: setLayoutVariant,
      isFooterVisible,
      setFooterVisible,
    }),
    [layoutVariant, isFooterVisible],
  );


  return (
    <LayoutContext.Provider value={layoutContextValue}>
      <Box position="relative" bg={colors.background.darkPrimary} w="100%">
        <ScrollToTop />

        {/* Background layers - pointer-events: none is critical! */}
        <Box
          position="fixed"
          top={0}
          left={0}
          right={0}
          bottom={0}
          bg={gradients.midnightMesh}
          opacity={0.55}
          pointerEvents="none"
          zIndex={0}
        />
        <Box
          position="fixed"
          top={0}
          left={0}
          right={0}
          bottom={0}
          bg="linear-gradient(180deg, rgba(5,5,5,0.95), rgba(5,5,5,0.8))"
          pointerEvents="none"
          zIndex={0}
        />

        {/* Header */}
        <Box position="sticky" top={0} zIndex={100}>
          <Header />
        </Box>

        {/* Main content - uses CSS animation instead of framer-motion */}
        <Box
          as="main"
          position="relative"
          zIndex={1}
          key={location.pathname}
          animation={`${fadeIn} 0.25s ease-out forwards`}
          sx={{ "@media (prefers-reduced-motion: reduce)": { animation: "none" } }}
        >
          {layoutVariant === "full" ? (
            <Outlet />
          ) : (
            <Box
              maxW="6xl"
              mx="auto"
              px={{ base: spacing.md, md: spacing.lg, lg: spacing[13] }}
              py={{ base: 8, md: 10 }}
            >
              <Outlet />
            </Box>
          )}
        </Box>

        {/* Footer */}
        {isFooterVisible && (
          <Box position="relative" zIndex={1}>
            <Footer />
          </Box>
        )}
      </Box>
    </LayoutContext.Provider>
  );
}

export default ProtectedLayout;
