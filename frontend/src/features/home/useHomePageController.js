import { useMemo } from "react";
import { colors } from "@theme/tokens";
import useHealth from "../../hooks/useHealth";
import { useAuth } from "@context/AuthContext";

const HERO_GAP = { base: 6, md: 8, lg: 12 };
const SECTION_PADDING = { base: 4, md: 6, lg: 8 };

export default function useHomePageController() {
  const { isAuthenticated } = useAuth();
  const health = useHealth(12000, { enabled: isAuthenticated });

  const layout = useMemo(
    () => ({
      hero: {
        gridProps: {
          columns: { base: 1, lg: 2 },
          spacing: HERO_GAP,
          alignItems: "start",
        },
      },
      sections: {
        hero: {
          w: "100%",
          pt: { base: 10, md: 16 },
          pb: { base: 12, md: 18 },
        },
        metrics: {
          w: "100%",
          py: { base: 12, md: 14 },
        },
        benefits: {
          w: "100%",
          py: { base: 12, md: 16 },
          bg: `linear-gradient(180deg, ${colors.background.darkPrimary} 0%, ${colors.blur.light} 50%, ${colors.background.darkPrimary} 100%)`,
        },
        slider: {
          w: "100%",
          py: { base: 14, md: 18 },
          bg: colors.background.darkPrimary,
        },
      },
      containers: {
        hero: { maxW: "1400px", px: SECTION_PADDING },
        metrics: { maxW: "1100px", px: SECTION_PADDING },
        divider: { maxW: "100%", px: 0 },
      },
    }),
    [],
  );

  return {
    isAuthenticated,
    health,
    layout,
  };
}
