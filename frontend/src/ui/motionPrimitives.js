import React from "react";
import { motion } from "framer-motion";
import { Box, VStack, Flex } from "@chakra-ui/react";

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
