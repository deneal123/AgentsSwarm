import React, { memo, useMemo } from "react";
import { Box } from "@chakra-ui/react";
import { keyframes } from "@emotion/react";
import { colors, borderRadius, gradients } from "@theme/tokens";
import useInteractiveGlow from "@hooks/useInteractiveGlow";

/**
 * GlowingCard - Card with animated gradient border and glow effect
 * @param {object} props - Component props
 * @param {React.ReactNode} props.children - Card content
 * @param {string} props.intensity - Glow intensity: 'subtle' | 'medium' | 'strong'
 * @param {object} props.rest - Additional Box props
 */
const borderPulse = keyframes`
  0% { opacity: 0.25; transform: scale(0.98); }
  45% { opacity: 0.65; transform: scale(1); }
  100% { opacity: 0.25; transform: scale(0.98); }
`;

const sparkleDrift = keyframes`
  0% { background-position: 0% 0%; }
  100% { background-position: 200% 200%; }
`;

// Выносим интенсивность за пределы компонента для предотвращения пересоздания
const INTENSITY_MAP = {
  subtle: {
    boxShadow: "0 0 18px rgba(47, 116, 255, 0.15)",
    hoverShadow: "0 0 28px rgba(139, 92, 246, 0.45)",
    borderWidth: "3px",
  },
  medium: {
    boxShadow: "0 0 18px rgba(47, 116, 255, 0.25)",
    hoverShadow: "0 0 28px rgba(139, 92, 246, 0.65)",
    borderWidth: "5px",
  },
  strong: {
    boxShadow: "0 0 28px rgba(47, 116, 255, 0.35)",
    hoverShadow: "0 0 45px rgba(139, 92, 246, 0.85)",
    borderWidth: "7px",
  },
};

const GlowingCard = memo(function GlowingCard({ children, intensity = "medium", ...rest }) {
  const { glowRef, glowStyle, onGlowMouseMove, onGlowMouseLeave } = useInteractiveGlow();

  // Мемоизация вычислений цветов
  const { gradientCss, intensityConfig } = useMemo(() => {
    const accentColor = colors.brand.primary;
    const secondaryColor = colors.brand.secondary;
    const tertiaryColor = colors.brand.tertiary;
    const gradientCss = `radial-gradient(circle at var(--glow-x, 50%) var(--glow-y, 50%),
      ${accentColor} 0%,
      ${secondaryColor} 35%,
      ${tertiaryColor} 65%)`;
    return { gradientCss, intensityConfig: INTENSITY_MAP[intensity] };
  }, [intensity]);

  return (
    <Box
      ref={glowRef}
      style={glowStyle}
      role="presentation"
      onMouseMove={onGlowMouseMove}
      onMouseLeave={onGlowMouseLeave}
      bg="transparent"
      borderRadius={borderRadius.md}
      position="relative"
      overflow="hidden"
      boxShadow={intensityConfig.boxShadow}
      transition="box-shadow 0.35s ease, transform 0.35s ease"
      _hover={{ boxShadow: intensityConfig.hoverShadow, transform: "translateY(-2px)" }}
      _before={{
        content: '""',
        position: "absolute",
        inset: 0,
        borderRadius: "inherit",
        padding: intensityConfig.borderWidth,
        background: gradientCss,
        backgroundSize: "220% 220%",
        WebkitMask: "linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)",
        WebkitMaskComposite: "xor",
        maskComposite: "exclude",
        pointerEvents: "none",
        transition: "background 0.3s ease",
        animation: `${borderPulse} ${intensity === "strong" ? 8 : 12}s ease-in-out infinite`,
      }}
      _after={{
        content: '""',
        position: "absolute",
        inset: 0,
        borderRadius: "inherit",
        background: `${gradients.midnightMesh}, radial-gradient(circle at 30% 20%, rgba(255,255,255,0.04), transparent 55%)`,
        mixBlendMode: "overlay",
        opacity: 0.28,
        pointerEvents: "none",
        animation: `${sparkleDrift} 18s linear infinite`,
      }}
      {...rest}
    >
      <Box
        position="relative"
        bg={`linear-gradient(145deg, rgba(5,5,10,0.85), rgba(5,5,5,0.35)), ${gradients.dusk}`}
        backdropFilter="blur(25px) saturate(180%)"
        border="1px solid rgba(255,255,255,0.05)"
        borderRadius={borderRadius.md}
        p={{ base: 5, md: 6 }}
        h="full"
      >
        <Box
          position="absolute"
          inset={0}
          borderRadius="inherit"
          pointerEvents="none"
          bg="linear-gradient(90deg, rgba(255,255,255,0.04), transparent)"
          opacity={0.22}
          transform="translateY(-20%)"
          filter="blur(35px)"
        />
        {children}
      </Box>
    </Box>
  );
});

export default GlowingCard;
