import React, { useRef, useState, useCallback, memo } from "react";
import { Box, usePrefersReducedMotion } from "@chakra-ui/react";
import { colors, borderRadius, gradients } from "@theme/tokens";

// Intensity presets for tilt effect
const INTENSITY_PRESETS = {
  subtle: { maxTilt: 3, scale: 1.005, glareOpacity: 0.08 },
  medium: { maxTilt: 5, scale: 1.01, glareOpacity: 0.12 },
  strong: { maxTilt: 8, scale: 1.02, glareOpacity: 0.18 },
};

/**
 * TiltCard - Card with 3D tilt effect on hover
 * Мемоизированный компонент для предотвращения лишних перерендеров
 */
const TiltCard = memo(function TiltCard({
  children,
  intensity = "subtle",
  maxTilt: customMaxTilt,
  glareEnable = true,
  scale: customScale,
  borderGradient = true,
  // cardRadius allows consumers to override the base radius used by the card
  cardRadius = borderRadius["2xl"],
  // Support legacy react-tilt style props (filter from DOM)
  tiltMaxAngleX,
  tiltMaxAngleY,
  tiltReverse,
  tiltEnable,
  glareMaxOpacity,
  glareBorderRadius,
  glarePosition,
  glareReverse,
  perspective,
  transitionSpeed,
  gyroscope,
  ...props
}) {
  const cardRef = useRef(null);
  const [transform, setTransform] = useState("");
  const [glareStyle, setGlareStyle] = useState({});
  const prefersReducedMotion = usePrefersReducedMotion();

  // Get values from preset or use custom/legacy values
  const preset = INTENSITY_PRESETS[intensity] || INTENSITY_PRESETS.subtle;
  // Support both maxTilt and tiltMaxAngleX for backward compatibility
  const maxTilt = customMaxTilt ?? tiltMaxAngleX ?? preset.maxTilt;
  const scale = customScale ?? preset.scale;
  const glareOpacity = glareMaxOpacity ?? preset.glareOpacity;

  // Мемоизированный обработчик движения мыши
  const handleMouseMove = useCallback(
    (e) => {
      if (prefersReducedMotion || !cardRef.current) return;

      const rect = cardRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      const rotateX = ((y - centerY) / centerY) * -maxTilt;
      const rotateY = ((x - centerX) / centerX) * maxTilt;

      setTransform(
        `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(${scale}, ${scale}, ${scale})`,
      );

      if (glareEnable) {
        const glareX = (x / rect.width) * 100;
        const glareY = (y / rect.height) * 100;
        setGlareStyle({
          background: `radial-gradient(circle at ${glareX}% ${glareY}%, rgba(255,255,255,${glareOpacity}) 0%, transparent 60%)`,
          opacity: 1,
        });
      }
    },
    [prefersReducedMotion, maxTilt, scale, glareEnable, glareOpacity],
  );

  // Мемоизированный обработчик ухода мыши
  const handleMouseLeave = useCallback(() => {
    setTransform("");
    setGlareStyle({ opacity: 0 });
  }, []);

  return (
    <Box
      ref={cardRef}
      position="relative"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{ transform, transformStyle: "preserve-3d" }}
      transition="transform 0.2s ease-out"
      willChange="transform"
      borderRadius={cardRadius}
      {...props}
    >
      {/* Gradient border */}
      {borderGradient && (
        <Box
          position="absolute"
          inset="-1px"
          borderRadius="inherit"
          bg={`linear-gradient(135deg, ${colors.brand.primary}40, ${colors.brand.secondary}30, ${colors.brand.tertiary}40)`}
          opacity={transform ? 0.6 : 0.3}
          transition="opacity 0.3s ease"
          zIndex={-1}
          filter="blur(1px)"
        />
      )}

      {/* Card content */}
      <Box
        position="relative"
        bg={`linear-gradient(145deg, rgba(10,12,20,0.95), rgba(5,5,10,0.9))`}
        borderRadius="inherit"
        overflow="hidden"
        border="1px solid rgba(255,255,255,0.08)"
        style={{ transform: "translateZ(10px)" }}
      >
        {/* Glare overlay */}
        {glareEnable && (
          <Box
            position="absolute"
            inset={0}
            pointerEvents="none"
            transition="opacity 0.3s ease"
            borderRadius="inherit"
            {...glareStyle}
          />
        )}

        {/* Inner glow */}
        <Box
          position="absolute"
          inset={0}
          bg={gradients.midnightMesh}
          opacity={0.2}
          pointerEvents="none"
          borderRadius="inherit"
        />

        {children}
      </Box>
    </Box>
  );
});

export default TiltCard;
