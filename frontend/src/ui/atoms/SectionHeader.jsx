import React from "react";
import { HStack, VStack, Box } from "@chakra-ui/react";
import { Title, Body } from "@ui/atoms/Typography";
import { spacing, colors } from "@theme/tokens";

/**
 * SectionHeader - reusable header for content sections
 * props:
 *  - title: string or node
 *  - description: optional string or node
 *  - action: optional node (e.g., button)
 */
function SectionHeader({ title, description, action, align = "center", ...props }) {
  const isCenter = align === "center";
  return (
    <HStack
      justifyContent={isCenter ? "center" : "space-between"}
      w="full"
      align="start"
      {...props}
    >
      <VStack
        align={isCenter ? "center" : "flex-start"}
        spacing={spacing.sm}
        maxW={isCenter ? "900px" : "auto"}
        textAlign={isCenter ? "center" : "left"}
      >
        <Title variant="medium" fontSize={{ base: "28px", md: "36px" }}>
          {title}
        </Title>
        {description && (
          <Body variant="medium" color={colors.text.tertiary} maxW={isCenter ? "700px" : "100%"}>
            {description}
          </Body>
        )}
      </VStack>

      {action && <Box ml={4}>{action}</Box>}
    </HStack>
  );
}

export default SectionHeader;
