import React from 'react';
import { Box } from '@chakra-ui/react';

function ChatComposer({ children }) {
  return (
    <Box
      p={{ base: 3, md: 4 }}
      borderTop="1px solid"
      borderColor="whiteAlpha.200"
      bg="rgba(10, 14, 25, 0.85)"
      backdropFilter="blur(12px)"
    >
      {children}
    </Box>
  );
}

export default ChatComposer;
