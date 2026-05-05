import React from "react";
import { Box, HStack, Icon, Text, VStack } from "@chakra-ui/react";
import Logo from "@ui/assets/common/Logo";
import { borderRadius } from "@theme/tokens";
import { AUTH_BRAND_LABEL, AUTH_THEME } from "@features/auth/constants";

function AuthPageHeader({ icon, title, description }) {
  return (
    <VStack align="stretch" spacing={1}>
      <Text fontSize="xs" letterSpacing="0.18em" textTransform="uppercase" color={AUTH_THEME.mutedText}>
        {AUTH_BRAND_LABEL}
      </Text>
      <HStack spacing={3} align="center">
        <Logo boxSize="28px" priority />
        <Box p={2} borderRadius={borderRadius.md} border="1px solid rgba(239, 68, 68, 0.45)" bg="rgba(239, 68, 68, 0.12)">
          <Icon as={icon} color={AUTH_THEME.accent} boxSize={4} />
        </Box>
        <Text fontSize={{ base: "xl", md: "2xl" }} fontWeight="500" color="white">
          {title}
        </Text>
      </HStack>
      <Text fontSize="sm" color={AUTH_THEME.mutedText}>
        {description}
      </Text>
    </VStack>
  );
}

export default AuthPageHeader;
