import React from 'react';
import { HStack } from '@chakra-ui/react';

function ChatHeaderControls({ left, center, right }) {
  return (
    <>
      <HStack spacing={1} w={{ base: 'auto', md: '160px' }}>
        {left}
      </HStack>
      <HStack spacing={2} flex="1" justify="center">
        {center}
      </HStack>
      <HStack w={{ base: 'auto', md: '200px' }} justify="flex-end" spacing={2}>
        {right}
      </HStack>
    </>
  );
}

export default ChatHeaderControls;
