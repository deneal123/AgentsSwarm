import React from "react";
import { Box, VStack } from "@chakra-ui/react";
import { borderRadius } from "@theme/tokens";

/**
 * AuthFormCard - лаконичная карточка для форм авторизации
 */
const AuthFormCard = ({ children, maxW = "480px", ...rest }) => {
  return (
    <Box
      maxW={maxW}
      mx="auto"
      position="relative"
      w="full"
      _before={{
        content: '""',
        position: "absolute",
        top: "-1px",
        left: "22px",
        right: "22px",
        height: "2px",
        background: "linear-gradient(90deg, transparent, rgba(239, 68, 68, 0.7), transparent)",
        borderRadius: "999px",
      }}
      {...rest}
    >
      <Box
        position="relative"
        bg="rgba(16, 16, 16, 0.9)"
        backdropFilter="blur(8px)"
        borderRadius={borderRadius["2xl"]}
        border="1px solid rgba(255, 255, 255, 0.14)"
        p={{ base: 4, sm: 5, md: 8 }}
        boxShadow="0 18px 40px rgba(0, 0, 0, 0.5)"
        zIndex={1}
      >
        <VStack spacing={{ base: 4, md: 6 }} position="relative" zIndex={1}>
          {children}
        </VStack>
      </Box>
    </Box>
  );
};

export default AuthFormCard;
