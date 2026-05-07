import React from 'react';
import { Box } from '@chakra-ui/react';

function ChatSidebar({ isCollapsed, children }) {
  return (
    <Box
      as="aside"
      display={{ base: 'none', lg: 'flex' }}
      flexDirection="column"
      w={isCollapsed ? '0' : '272px'}
      minW={isCollapsed ? '0' : '272px'}
      overflow="hidden"
      borderRight={isCollapsed ? 'none' : '1px solid'}
      borderColor="whiteAlpha.200"
      transition="all 0.24s cubic-bezier(0.4,0,0.2,1)"
    >
      {!isCollapsed && children}
    </Box>
  );
}

export default ChatSidebar;
