import React from "react";
import { Box, Text } from "@chakra-ui/react";
import { MotionBox } from "@shared/ui/lib/motionPrimitives";
import { colors } from "@theme/tokens";
import { keyframes } from "@emotion/react";

const shimmer = keyframes`
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
`;

const glow = keyframes`
  0%, 100% {
    text-shadow: 0 0 20px ${colors.brand.primary}60,
                 0 0 40px ${colors.brand.primary}40,
                 0 0 60px ${colors.brand.primary}20;
  }
  50% {
    text-shadow: 0 0 30px ${colors.brand.primary}80,
                 0 0 60px ${colors.brand.primary}60,
                 0 0 90px ${colors.brand.primary}40;
  }
`;

/**
 * GradientText - Text with animated gradient effect
 */
export function GradientText({
  children,
  gradient = `linear-gradient(90deg, ${colors.brand.primary}, ${colors.brand.secondary}, ${colors.brand.tertiary}, ${colors.brand.primary})`,
  animate = true,
  ...props
}) {
  return (
    <Text
      as="span"
      bgGradient={gradient}
      bgSize="200% auto"
      bgClip="text"
      display="inline-block"
      animation={animate ? `${shimmer} 4s linear infinite` : undefined}
      {...props}
    >
      {children}
    </Text>
  );
}

/**
 * GlowText - Text with pulsing glow effect
 */
export function GlowText({
  children,
  color = colors.brand.primary,
  glowIntensity = "medium",
  ...props
}) {
  const intensityMap = {
    subtle: `0 0 10px ${color}40`,
    medium: `0 0 20px ${color}60, 0 0 40px ${color}40`,
    strong: `0 0 30px ${color}80, 0 0 60px ${color}60, 0 0 90px ${color}40`,
  };

  return (
    <Text
      as="span"
      color={color}
      animation={`${glow} 3s ease-in-out infinite`}
      textShadow={intensityMap[glowIntensity]}
      {...props}
    >
      {children}
    </Text>
  );
}

/**
 * TypewriterText - Text with typewriter animation effect
 */
export function TypewriterText({ text, speed = 50, delay = 0, ...props }) {
  const [displayText, setDisplayText] = React.useState("");
  const [currentIndex, setCurrentIndex] = React.useState(0);

  React.useEffect(() => {
    const timeout = setTimeout(
      () => {
        if (currentIndex < text.length) {
          setDisplayText(text.slice(0, currentIndex + 1));
          setCurrentIndex((prev) => prev + 1);
        }
      },
      currentIndex === 0 ? delay : speed,
    );

    return () => clearTimeout(timeout);
  }, [currentIndex, text, speed, delay]);

  return (
    <Box display="inline" {...props}>
      {displayText}
      <MotionBox
        as="span"
        display="inline-block"
        w="2px"
        h="1em"
        bg={colors.brand.primary}
        ml={1}
        animate={{ opacity: [1, 0] }}
        transition={{ duration: 0.5, repeat: Infinity, repeatType: "reverse" }}
      />
    </Box>
  );
}

/**
 * RevealText - Text with reveal animation on scroll
 */
export function RevealText({ children, delay = 0, ...props }) {
  return (
    <Box overflow="hidden" display="inline-block">
      <MotionBox
        initial={{ y: "100%" }}
        whileInView={{ y: 0 }}
        viewport={{ once: true }}
        transition={{
          duration: 0.6,
          delay,
          ease: [0.25, 0.46, 0.45, 0.94],
        }}
        {...props}
      >
        {children}
      </MotionBox>
    </Box>
  );
}

const AnimatedTextExports = { GradientText, GlowText, TypewriterText, RevealText };
export default AnimatedTextExports;
