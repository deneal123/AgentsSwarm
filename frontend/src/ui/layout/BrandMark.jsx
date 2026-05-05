import React from "react";
import { Box, HStack, Text, VStack } from "@chakra-ui/react";

const BRAND_NAME = "GPTHub";

function BrandGlyph({ size = "md" }) {
  const map = {
    sm: { outer: "28px", dot: "8px", stripe: "12px" },
    md: { outer: "34px", dot: "10px", stripe: "14px" },
  };

  const current = map[size] || map.md;

  return (
    <Box
      position="relative"
      w={current.outer}
      h={current.outer}
      borderRadius="10px"
      border="1px solid rgba(255, 255, 255, 0.18)"
      bg="linear-gradient(160deg, rgba(24, 24, 24, 0.95), rgba(10, 10, 10, 0.95))"
      display="flex"
      alignItems="center"
      justifyContent="center"
      boxShadow="0 10px 20px rgba(0, 0, 0, 0.4)"
      overflow="hidden"
      flexShrink={0}
    >
      <Box
        position="absolute"
        top="4px"
        right="4px"
        w={current.dot}
        h={current.dot}
        borderRadius="full"
        bg="#ef4444"
      />
      <Box
        position="absolute"
        left="7px"
        bottom="7px"
        w="2px"
        h={current.stripe}
        bg="rgba(239, 68, 68, 0.75)"
        borderRadius="full"
      />
      <Text fontSize={size === "sm" ? "11px" : "13px"} fontWeight="700" color="white">
        GH
      </Text>
    </Box>
  );
}

function BrandMark({ size = "md", showSubtitle = true, iconOnly = false }) {
  if (iconOnly) {
    return <BrandGlyph size={size} />;
  }

  return (
    <HStack spacing={3} align="center">
      <BrandGlyph size={size} />
      <VStack spacing={0} align="flex-start">
        <Text fontSize={size === "sm" ? "lg" : "xl"} fontWeight="600" color="white" lineHeight="1">
          {BRAND_NAME}
        </Text>
        {showSubtitle && (
          <Text
            fontSize="9px"
            letterSpacing="0.18em"
            textTransform="uppercase"
            color="rgba(255, 255, 255, 0.58)"
          >
            AI Workspace
          </Text>
        )}
      </VStack>
    </HStack>
  );
}

export default BrandMark;
