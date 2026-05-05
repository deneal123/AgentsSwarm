import React, { useMemo } from "react";
import { Box } from "@chakra-ui/react";
import { useReducedMotion } from "framer-motion";
import { colors } from "@theme/tokens";
import { MotionBox } from "@ui/motionPrimitives";

const COLOR_PALETTES = [
  [colors.brand.primary, colors.brand.secondary],
  [colors.brand.secondary, colors.brand.tertiary],
  [colors.brand.tertiary, colors.brand.primary],
  ["#ff6b6b", "#4ecdc4"],
  ["#ffd93d", "#6bcf7f"],
];

const pseudoRandom = (seed) => {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
};

const deterministicValue = (seedBase, offset, min, max, precision = 0) => {
  const seed = seedBase + offset * 104729;
  const value = pseudoRandom(seed) * (max - min) + min;
  if (precision === 0) {
    return Math.round(value);
  }
  return Number(value.toFixed(precision));
};

export function createGradientParticles(count = 20) {
  return Array.from({ length: count }, (_, index) => {
    const seedBase = (index + 1) * 7919;
    const pickShift = (offset) => deterministicValue(seedBase, offset, -50, 50);
    const paletteIndex = Math.min(
      COLOR_PALETTES.length - 1,
      deterministicValue(seedBase, 6, 0, COLOR_PALETTES.length - 1),
    );

    return {
      id: index,
      size: deterministicValue(seedBase, 1, 100, 300),
      x: deterministicValue(seedBase, 2, 0, 100),
      y: deterministicValue(seedBase, 3, 0, 100),
      duration: deterministicValue(seedBase, 4, 15, 35, 2),
      delay: deterministicValue(seedBase, 5, 0, 5, 2),
      colors: COLOR_PALETTES[paletteIndex],
      xShift: [0, pickShift(7), pickShift(8), 0],
      yShift: [0, pickShift(9), pickShift(10), 0],
    };
  });
}

function GradientParticles() {
  const shouldReduce = useReducedMotion();

  // adapt particle count to viewport width to reduce work on small screens
  const [count, setCount] = React.useState(() => {
    if (typeof window === "undefined") return 12;
    const w = window.innerWidth;
    if (w < 768) return 8;
    if (w < 1280) return 14;
    return 20;
  });

  React.useEffect(() => {
    const onResize = () => {
      const w = window.innerWidth;
      setCount(w < 768 ? 8 : w < 1280 ? 14 : 20);
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const particles = useMemo(() => createGradientParticles(count), [count]);

  if (shouldReduce) return null;

  return (
    <Box
      position="absolute"
      top="0"
      left="0"
      right="0"
      bottom="0"
      overflow="hidden"
      zIndex={0}
      pointerEvents="none"
    >
      {particles.map((particle) => (
        <MotionBox
          key={particle.id}
          position="absolute"
          left={`${particle.x}%`}
          top={`${particle.y}%`}
          w={`${particle.size}px`}
          h={`${particle.size}px`}
          borderRadius="full"
          bg={`radial-gradient(circle, ${particle.colors[0]}30 0%, ${particle.colors[1]}18 40%, transparent 70%)`}
          initial={{
            scale: 0,
            opacity: 0,
            filter: "blur(40px)",
          }}
          animate={{
            scale: [0, 1.4, 1, 1.4, 0],
            opacity: [0, 0.5, 0.35, 0.5, 0],
            x: particle.xShift,
            y: particle.yShift,
          }}
          transition={{
            duration: particle.duration,
            delay: particle.delay,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      ))}
    </Box>
  );
}

export default GradientParticles;
