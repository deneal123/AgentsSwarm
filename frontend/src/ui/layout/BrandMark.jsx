import React from "react";
import { HStack, Text, VStack } from "@chakra-ui/react";
import Logo from "@ui/assets/common/Logo";

import { PROJECT_NAME } from "@constants";

function BrandMark({ size = "md", showSubtitle = true, iconOnly = false }) {
  const iconSize = size === "sm" ? "28px" : "34px";

  if (iconOnly) {
    return <Logo boxSize={iconSize} />;
  }

  return (
    <HStack spacing={3} align="center">
      <Logo boxSize={iconSize} />
      <VStack spacing={0} align="flex-start">
        <Text fontSize={size === "sm" ? "lg" : "xl"} fontWeight="600" color="white" lineHeight="1">
          {PROJECT_NAME}
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
