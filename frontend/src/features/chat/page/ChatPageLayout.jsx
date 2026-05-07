import React from 'react';
import { Box } from '@chakra-ui/react';
import { CHAT_FONT_FAMILY, CHAT_THEME } from '../constants/theme';

function ChatPageLayout({ children }) {
  return (
    <Box
      h="100vh"
      position="relative"
      bg={CHAT_THEME.pageBg}
      color={CHAT_THEME.textPrimary}
      fontFamily={CHAT_FONT_FAMILY}
      fontSize="15px"
      overflow="hidden"
    >
      {children}
    </Box>
  );
}

export default ChatPageLayout;
