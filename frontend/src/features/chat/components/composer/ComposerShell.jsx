import React from 'react';
import { Box } from '@chakra-ui/react';

function ComposerShell({ children }) {
  return (
    <Box position="relative" w="100%" maxW="100%">
      {children}
    </Box>
  );
}

export default ComposerShell;
