import React from "react";
import { Box, usePrefersReducedMotion } from "@chakra-ui/react";
import { MotionBox } from "@ui/motionPrimitives";
import { colors } from "@theme/tokens";

/**
 * FloatingOrbs - Animated floating gradient orbs for background decoration
 */
function FloatingOrbs({ count = 3, ...props }) {
  const prefersReducedMotion = usePrefersReducedMotion();

  const orbs = [
    {
      size: { base: "300px", md: "500px", lg: "600px" },
      top: "-15%",
      left: "-10%",
      colors: [colors.brand.primary, colors.brand.secondary],
      delay: 0,
      duration: 20,
    },
    {
      size: { base: "250px", md: "400px", lg: "500px" },
      top: "60%",
      right: "-15%",
      colors: [colors.brand.secondary, colors.brand.tertiary],
      delay: 2,
      duration: 25,
    },
    {
      size: { base: "200px", md: "350px", lg: "450px" },
      bottom: "-10%",
      left: "30%",
      colors: [colors.brand.tertiary, colors.brand.primary],
      delay: 4,
      duration: 22,
    },
  ].slice(0, count);

  return (
    <Box position="absolute" inset={0} overflow="hidden" pointerEvents="none" zIndex={0} {...props}>
      {orbs.map((orb, index) => (
        <MotionBox
          key={index}
          position="absolute"
          w={orb.size}
          h={orb.size}
          top={orb.top}
          left={orb.left}
          right={orb.right}
          bottom={orb.bottom}
          borderRadius="full"
          bg={`radial-gradient(circle, ${orb.colors[0]}40 0%, ${orb.colors[1]}20 50%, transparent 70%)`}
          filter="blur(80px)"
          animate={
            prefersReducedMotion
              ? {}
              : {
                  x: [0, 30, -20, 0],
                  y: [0, -40, 20, 0],
                  scale: [1, 1.1, 0.95, 1],
                }
          }
          transition={{
            duration: orb.duration,
            repeat: Infinity,
            ease: "easeInOut",
            delay: orb.delay,
          }}
        />
      ))}
    </Box>
  );
}

export default FloatingOrbs;
