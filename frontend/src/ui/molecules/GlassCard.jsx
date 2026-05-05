import React from "react";
import { Box } from "@chakra-ui/react";
import { colors, borderRadius, blur } from "@theme/tokens";

/**
 * GlassCard - Reusable card component with blur background
 * @param {object} props - Component props
 * @param {React.ReactNode} props.children - Card content
 * @param {string} props.backgroundColor - Custom background color (optional)
 * @param {string} props.blurStrength - Custom blur strength (optional)
 * @param {object} props.rest - Additional Chakra Box props
 */
function GlassCard({ children, backgroundColor, blurStrength, ...rest }) {
  return (
    <Box
      bg={backgroundColor || colors.blur.dark}
      backdropFilter={`blur(${blurStrength || blur.strength.default})`}
      borderRadius={borderRadius.md}
      border="1px solid"
      borderColor={colors.border.default}
      p={{ base: 5, md: 6 }}
      w="full"
      h="auto"
      minH="min-content"
      {...rest}
    >
      {children}
    </Box>
  );
}

export default GlassCard;
