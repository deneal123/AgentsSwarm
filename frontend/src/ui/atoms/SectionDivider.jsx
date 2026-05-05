import React from "react";
import { Box } from "@chakra-ui/react";
import { useReducedMotion } from "framer-motion";
import { MotionBox } from "@ui/motionPrimitives";
import { colors } from "@theme/tokens";
import { keyframes } from "@emotion/react";

// Keyframe анимации
const pulseGlow = keyframes`
  0%, 100% { opacity: 0.4; filter: blur(20px); }
  50% { opacity: 0.8; filter: blur(30px); }
`;

const energyFlow = keyframes`
  0% { background-position: 0% 50%; }
  100% { background-position: 200% 50%; }
`;

const sparkle = keyframes`
  0%, 100% { opacity: 0; transform: scale(0) translateY(0); }
  20% { opacity: 1; transform: scale(1) translateY(-5px); }
  40% { opacity: 1; transform: scale(1.2) translateY(-15px); }
  60% { opacity: 0.8; transform: scale(1) translateY(-25px); }
  80% { opacity: 0.3; transform: scale(0.8) translateY(-35px); }
`;

/**
 * SectionDivider - Decorative animated divider between sections
 * Full viewport width with edge fade effects
 * @param {string} variant - Style variant: "electric", "lightning"
 */
function SectionDivider({ variant = "electric" }) {
  const prefersReducedMotion = useReducedMotion();

  // Common edge fade overlay for smooth transitions
  const EdgeFade = () => (
    <>
      <Box
        position="absolute"
        top={0}
        left={0}
        bottom={0}
        w={{ base: "80px", md: "150px", lg: "250px" }}
        bg={`linear-gradient(90deg, ${colors.background.darkPrimary} 0%, ${colors.background.darkPrimary}80 40%, transparent 100%)`}
        zIndex={10}
        pointerEvents="none"
      />
      <Box
        position="absolute"
        top={0}
        right={0}
        bottom={0}
        w={{ base: "80px", md: "150px", lg: "250px" }}
        bg={`linear-gradient(270deg, ${colors.background.darkPrimary} 0%, ${colors.background.darkPrimary}80 40%, transparent 100%)`}
        zIndex={10}
        pointerEvents="none"
      />
    </>
  );

  if (prefersReducedMotion) {
    return (
      <Box position="relative" w="full" h="64px" my={{ base: 8, md: 12 }}>
        <EdgeFade />
        <Box
          position="absolute"
          top="50%"
          left="0"
          right="0"
          h="4px"
          borderRadius="full"
          bg={`linear-gradient(90deg, ${colors.brand.primary}, ${colors.brand.secondary}, ${colors.brand.tertiary})`}
          opacity={0.65}
          style={{ transform: "translateY(-50%)" }}
        />
      </Box>
    );
  }

  if (variant === "electric") {
    return (
      <Box
        position="relative"
        w="full"
        h={{ base: "120px", md: "160px" }}
        my={{ base: 10, md: 14 }}
        overflow="hidden"
      >
        <EdgeFade />

        {/* Ambient glow background */}
        <Box
          position="absolute"
          top="50%"
          left="10%"
          right="10%"
          h="60px"
          transform="translateY(-50%)"
          bg={`radial-gradient(ellipse 80% 50% at 50% 50%, ${colors.brand.primary}30 0%, transparent 70%)`}
          animation={`${pulseGlow} 3s ease-in-out infinite`}
          pointerEvents="none"
        />

        {/* Main energy line with animated gradient */}
        <MotionBox
          position="absolute"
          top="50%"
          left="0"
          right="0"
          h="4px"
          borderRadius="full"
          bg={`linear-gradient(90deg,
            ${colors.brand.primary}00,
            ${colors.brand.primary} 15%,
            ${colors.brand.secondary} 35%,
            ${colors.brand.tertiary} 50%,
            ${colors.brand.secondary} 65%,
            ${colors.brand.primary} 85%,
            ${colors.brand.primary}00)`}
          backgroundSize="200% 100%"
          animation={`${energyFlow} 3s linear infinite`}
          initial={{ scaleX: 0, opacity: 0 }}
          whileInView={{ scaleX: 1, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1, ease: "easeOut" }}
          boxShadow={`
            0 0 20px ${colors.brand.primary}80,
            0 0 40px ${colors.brand.secondary}60,
            0 0 60px ${colors.brand.tertiary}40
          `}
          style={{ transform: "translateY(-50%)" }}
        />

        {/* Secondary thin lines */}
        <Box
          position="absolute"
          top="calc(50% - 15px)"
          left="5%"
          right="5%"
          h="1px"
          bg={`linear-gradient(90deg, transparent, ${colors.brand.secondary}40, transparent)`}
          opacity={0.6}
        />
        <Box
          position="absolute"
          top="calc(50% + 15px)"
          left="5%"
          right="5%"
          h="1px"
          bg={`linear-gradient(90deg, transparent, ${colors.brand.tertiary}40, transparent)`}
          opacity={0.6}
        />

        {/* Sparkle particles */}
        {[...Array(16)].map((_, i) => (
          <Box
            key={i}
            position="absolute"
            top="50%"
            left={`${6 + i * 5.5}%`}
            w="4px"
            h="4px"
            borderRadius="full"
            bg={
              i % 3 === 0
                ? colors.brand.primary
                : i % 3 === 1
                  ? colors.brand.secondary
                  : colors.brand.tertiary
            }
            boxShadow={`0 0 10px ${i % 3 === 0 ? colors.brand.primary : i % 3 === 1 ? colors.brand.secondary : colors.brand.tertiary}`}
            animation={`${sparkle} ${2 + (i % 3) * 0.5}s ease-out infinite`}
            style={{ animationDelay: `${i * 0.2}s` }}
          />
        ))}

        {/* Central pulse orb */}
        <MotionBox
          position="absolute"
          top="50%"
          left="50%"
          w="100px"
          h="100px"
          borderRadius="full"
          bg={`radial-gradient(circle, ${colors.brand.secondary}40 0%, ${colors.brand.primary}20 30%, transparent 70%)`}
          initial={{ scale: 0, opacity: 0 }}
          whileInView={{
            scale: [0, 1.5, 1],
            opacity: [0, 0.8, 0.4],
          }}
          viewport={{ once: true }}
          transition={{ duration: 1.5, ease: "easeOut", delay: 0.5 }}
          style={{ transform: "translate(-50%, -50%)" }}
        />
      </Box>
    );
  }

  if (variant === "lightning") {
    return (
      <Box
        position="relative"
        w="full"
        h={{ base: "120px", md: "160px" }}
        my={{ base: 10, md: 14 }}
        overflow="hidden"
      >
        <EdgeFade />

        {/* Ambient glow */}
        <Box
          position="absolute"
          top="50%"
          left="20%"
          right="20%"
          h="80px"
          transform="translateY(-50%)"
          bg={`radial-gradient(ellipse 100% 60% at 50% 50%, ${colors.brand.tertiary}20 0%, transparent 70%)`}
          animation={`${pulseGlow} 4s ease-in-out infinite`}
          pointerEvents="none"
        />

        {/* Base track lines */}
        <Box
          position="absolute"
          top="50%"
          left="0"
          right="0"
          h="2px"
          bg={`linear-gradient(90deg, transparent 5%, ${colors.border.default}30 20%, ${colors.border.default}30 80%, transparent 95%)`}
          style={{ transform: "translateY(-50%)" }}
        />
        <Box
          position="absolute"
          top="calc(50% - 20px)"
          left="0"
          right="0"
          h="1px"
          bg={`linear-gradient(90deg, transparent 10%, ${colors.border.default}20 30%, ${colors.border.default}20 70%, transparent 90%)`}
        />
        <Box
          position="absolute"
          top="calc(50% + 20px)"
          left="0"
          right="0"
          h="1px"
          bg={`linear-gradient(90deg, transparent 10%, ${colors.border.default}20 30%, ${colors.border.default}20 70%, transparent 90%)`}
        />

        {/* Main lightning bolt */}
        <MotionBox
          position="absolute"
          top="50%"
          w="40%"
          h="6px"
          borderRadius="full"
          bg={`linear-gradient(90deg,
            transparent 0%,
            ${colors.brand.primary}60 5%,
            ${colors.brand.primary} 15%,
            ${colors.brand.secondary} 40%,
            ${colors.brand.tertiary} 60%,
            ${colors.brand.secondary} 85%,
            ${colors.brand.primary}60 95%,
            transparent 100%)`}
          animate={{
            left: ["-40%", "100%"],
          }}
          transition={{
            duration: 2.5,
            ease: "easeInOut",
            repeat: Infinity,
            repeatDelay: 0.5,
          }}
          style={{ transform: "translateY(-50%)" }}
          boxShadow={`
            0 0 30px ${colors.brand.primary},
            0 0 60px ${colors.brand.secondary}80,
            0 0 90px ${colors.brand.tertiary}60
          `}
        />

        {/* Secondary bolt - opposite direction */}
        <MotionBox
          position="absolute"
          top="calc(50% - 20px)"
          w="30%"
          h="4px"
          borderRadius="full"
          bg={`linear-gradient(90deg,
            transparent 0%,
            ${colors.brand.tertiary}60 10%,
            ${colors.brand.tertiary} 30%,
            ${colors.brand.secondary} 50%,
            ${colors.brand.primary} 70%,
            ${colors.brand.tertiary}60 90%,
            transparent 100%)`}
          animate={{
            left: ["100%", "-30%"],
          }}
          transition={{
            duration: 3,
            ease: "easeInOut",
            repeat: Infinity,
            repeatDelay: 1,
            delay: 0.8,
          }}
          style={{ transform: "translateY(-50%)" }}
          boxShadow={`0 0 25px ${colors.brand.tertiary}90`}
        />

        {/* Tertiary bolt */}
        <MotionBox
          position="absolute"
          top="calc(50% + 20px)"
          w="25%"
          h="3px"
          borderRadius="full"
          bg={`linear-gradient(90deg,
            transparent 0%,
            ${colors.brand.secondary}60 10%,
            ${colors.brand.secondary} 30%,
            ${colors.brand.primary} 50%,
            ${colors.brand.tertiary} 70%,
            ${colors.brand.secondary}60 90%,
            transparent 100%)`}
          animate={{
            left: ["-25%", "100%"],
          }}
          transition={{
            duration: 2.2,
            ease: "easeInOut",
            repeat: Infinity,
            repeatDelay: 0.8,
            delay: 1.5,
          }}
          style={{ transform: "translateY(-50%)" }}
          boxShadow={`0 0 20px ${colors.brand.secondary}80`}
        />

        {/* Small energy particles */}
        {[...Array(8)].map((_, i) => {
          const yOffset = ((i % 3) - 1) * 15;
          const direction = i % 2 === 0;
          return (
            <MotionBox
              key={`particle-${i}`}
              position="absolute"
              top={`calc(50% + ${yOffset}px)`}
              w="12%"
              h="2px"
              borderRadius="full"
              bg={`linear-gradient(90deg,
                transparent,
                ${i % 2 === 0 ? colors.brand.secondary : colors.brand.tertiary} 40%,
                ${colors.brand.primary} 50%,
                ${i % 2 === 0 ? colors.brand.tertiary : colors.brand.secondary} 60%,
                transparent)`}
              animate={{
                left: direction ? ["-12%", "100%"] : ["100%", "-12%"],
              }}
              transition={{
                duration: 1.8 + i * 0.2,
                ease: "linear",
                repeat: Infinity,
                repeatDelay: 0.3 + i * 0.15,
                delay: i * 0.25,
              }}
              boxShadow={`0 0 12px ${i % 2 === 0 ? colors.brand.secondary : colors.brand.tertiary}70`}
            />
          );
        })}

        {/* Glowing nodes at center */}
        <Box
          position="absolute"
          top="50%"
          left="50%"
          w="8px"
          h="8px"
          borderRadius="full"
          bg={colors.brand.primary}
          transform="translate(-50%, -50%)"
          boxShadow={`0 0 20px ${colors.brand.primary}, 0 0 40px ${colors.brand.primary}80`}
          animation={`${pulseGlow} 2s ease-in-out infinite`}
        />
      </Box>
    );
  }

  return null;
}

export default SectionDivider;
