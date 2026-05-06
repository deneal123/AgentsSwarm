import React from "react";
import { motion } from "framer-motion";
import { Box, VStack, Flex } from "@chakra-ui/react";

import { keyframes } from "@emotion/react";

export const motionKeyframes = {
  float: keyframes`0%, 100% { transform: translateY(0) rotate(0deg); } 50% { transform: translateY(-8px) rotate(2deg); }`,
  pulse: keyframes`0%, 100% { opacity: 0.4; transform: scale(1); } 50% { opacity: 0.8; transform: scale(1.1); }`,
  shimmer: keyframes`0% { left: -100%; } 100% { left: 200%; }`,
};

export const motionVariants = {
  staggerContainer: {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.12, delayChildren: 0.1 } },
  },
  riseInItem: {
    hidden: { opacity: 0, y: 40, scale: 0.95 },
    visible: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] } },
  },
};


const RawMotionBox = motion(Box);
const RawMotionVStack = motion(VStack);
const RawMotionFlex = motion(Flex);

// Full animations for everyone - no reduced motion handling
export const MotionBox = React.forwardRef(
  ({ initial, animate, exit, whileHover, whileTap, transition, whileInView, ...props }, ref) => {
    return (
      <RawMotionBox
        ref={ref}
        initial={initial}
        animate={animate}
        exit={exit}
        whileHover={whileHover}
        whileTap={whileTap}
        transition={transition}
        whileInView={whileInView}
        {...props}
      />
    );
  },
);

export const MotionVStack = React.forwardRef(
  ({ initial, animate, exit, whileHover, whileTap, transition, whileInView, ...props }, ref) => {
    return (
      <RawMotionVStack
        ref={ref}
        initial={initial}
        animate={animate}
        exit={exit}
        whileHover={whileHover}
        whileTap={whileTap}
        transition={transition}
        whileInView={whileInView}
        {...props}
      />
    );
  },
);

export const MotionFlex = React.forwardRef(
  ({ initial, animate, exit, whileHover, whileTap, transition, whileInView, ...props }, ref) => {
    return (
      <RawMotionFlex
        ref={ref}
        initial={initial}
        animate={animate}
        exit={exit}
        whileHover={whileHover}
        whileTap={whileTap}
        transition={transition}
        whileInView={whileInView}
        {...props}
      />
    );
  },
);

MotionBox.displayName = "MotionBox";
MotionVStack.displayName = "MotionVStack";
MotionFlex.displayName = "MotionFlex";
