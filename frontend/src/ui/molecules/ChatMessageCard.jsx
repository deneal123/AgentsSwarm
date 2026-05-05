import React from 'react';
import { Box, Text } from '@chakra-ui/react';
import { MotionBox } from '@ui/motionPrimitives';
import MessageRenderer from '@features/chat/components/MessageRenderer';
import { colors } from '@theme/tokens';

function ChatMessageCard({ message, index = 0 }) {
  const isUser = message.type === 'user';

  return (
    <Box
      display="flex"
      justifyContent={isUser ? 'flex-end' : 'flex-start'}
      w="100%"
      py={1}
    >
      <MotionBox
        initial={{ opacity: 0, y: 10, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.2, delay: Math.min(index * 0.02, 0.16) }}
        p={{ base: 3, md: 4 }}
        borderRadius="2xl"
        bg={isUser ? 'rgba(47,116,255,0.18)' : 'rgba(255,255,255,0.08)'}
        maxW={{ base: '94%', md: '84%' }}
        minW={{ base: 'auto', md: '220px' }}
        border="1px solid"
        borderColor={isUser ? 'rgba(47,116,255,0.4)' : 'rgba(255,255,255,0.1)'}
        boxShadow={isUser ? '0 8px 24px rgba(47,116,255,0.22)' : '0 8px 24px rgba(0,0,0,0.22)'}
      >
        {message.type === 'agent' ? (
          <MessageRenderer
            content={message.content}
            isTyping={message.isTyping}
            typingProgress={message.typingProgress}
            messageType={message.type}
          />
        ) : (
          <Text color={colors.text.primary} fontSize="sm" lineHeight="1.65" whiteSpace="pre-wrap">
            {message.content}
          </Text>
        )}

        <Text color={colors.text.tertiary} fontSize="xs" mt={2} textAlign={isUser ? 'right' : 'left'}>
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </Text>
      </MotionBox>
    </Box>
  );
}

export default ChatMessageCard;
