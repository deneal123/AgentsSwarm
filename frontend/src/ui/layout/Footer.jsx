import React from "react";
import { Badge, Box, Divider, HStack, Text, VStack } from "@chakra-ui/react";
import { useLocation } from "react-router-dom";
import { PROJECT_VERSION } from "@constants";
import BrandMark from "./BrandMark";

function Footer() {
  const location = useLocation();
  const isAuthPage = location.pathname === "/login" || location.pathname === "/register";

  return (
    <Box as="footer" position="relative" w="100%" overflow="hidden" bg="rgba(7, 7, 7, 0.98)">
      <Box
        position="absolute"
        inset={0}
        pointerEvents="none"
        bg="linear-gradient(180deg, rgba(7,7,7,0.88) 0%, rgba(7,7,7,1) 100%)"
      />
      <Box
        position="absolute"
        top="-45%"
        right="-12%"
        w="360px"
        h="360px"
        borderRadius="full"
        bg="radial-gradient(circle, rgba(239, 68, 68, 0.14) 0%, transparent 70%)"
        filter="blur(80px)"
        pointerEvents="none"
      />
      <Box
        position="absolute"
        top={0}
        left={0}
        right={0}
        h="1px"
        bg="linear-gradient(90deg, transparent, rgba(239,68,68,0.55), transparent)"
      />

      <Box
        position="relative"
        zIndex={1}
        maxW={isAuthPage ? "none" : "1400px"}
        mx="auto"
        px={isAuthPage ? 5 : { base: 4, md: 6, lg: 8 }}
        py={{ base: 8, md: 10 }}
      >
        <VStack align="stretch" spacing={6}>
          <HStack justify="space-between" align={{ base: "flex-start", md: "center" }} flexWrap="wrap" gap={4}>
            <VStack align="flex-start" spacing={3} maxW="620px">
              <BrandMark />
              <Text fontSize="sm" color="rgba(255,255,255,0.65)" lineHeight="1.7">
                Единое окно для всех задач искусственного интеллекта (ИИ).
              </Text>
            </VStack>

            <HStack spacing={3} align="center">
              <Badge
                px={3}
                py={1.5}
                borderRadius="full"
                bg="rgba(255, 255, 255, 0.08)"
                border="1px solid rgba(255, 255, 255, 0.14)"
                color="rgba(255, 255, 255, 0.82)"
                fontWeight="500"
                textTransform="none"
              >
                v{PROJECT_VERSION}
              </Badge>
              <Badge
                px={3}
                py={1.5}
                borderRadius="full"
                bg="rgba(239, 68, 68, 0.16)"
                border="1px solid rgba(239, 68, 68, 0.35)"
                color="#ef4444"
                fontWeight="600"
                textTransform="none"
              >
                Online
              </Badge>
            </HStack>
          </HStack>

          <Divider borderColor="rgba(255,255,255,0.1)" />
        </VStack>
      </Box>
    </Box>
  );
}

export default Footer;
