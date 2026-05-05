import React from "react";
import { Box, Container } from "@chakra-ui/react";
import { MotionVStack } from "@ui/motionPrimitives";
import { spacing } from "@theme/tokens";

/**
 * Section - small layout primitive to enforce vertical rhythm across public pages
 * Props:
 *  - pt, pb: padding top/bottom (responsive or number)
 *  - center: if true, wraps children in a centered MotionVStack
 */
const Section = React.forwardRef(({ children, pt, pb, center = false, ...props }, ref) => {
  const defaultPt = { base: spacing["8xl"], md: spacing["10xl"] };
  const defaultPb = { base: spacing["6xl"], md: spacing["8xl"] };

  return (
    <Box
      ref={ref}
      position="relative"
      zIndex={1}
      pt={pt ?? defaultPt}
      pb={pb ?? defaultPb}
      {...props}
    >
      <Container maxW="full" px={{ base: 4, md: 6, lg: 8 }}>
        {center ? (
          <MotionVStack spacing={spacing.lg} align="center" textAlign="center">
            {children}
          </MotionVStack>
        ) : (
          children
        )}
      </Container>
    </Box>
  );
});

Section.displayName = "Section";

export default Section;
