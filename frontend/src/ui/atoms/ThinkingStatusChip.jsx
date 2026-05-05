import React from 'react';
import { HStack, Text, Box } from '@chakra-ui/react';
import { TypingPulse } from '@ui/atoms/MessageAnimations';
import { colors } from '@theme/tokens';

function ThinkingStatusChip({ isVisible = false, label = 'Агент формирует ответ...' }) {
  if (!isVisible) return null;

  return (
    <HStack
      spacing={2}
      px={3}
      py={2}
      borderRadius="full"
      bg="rgba(255,255,255,0.06)"
      border="1px solid rgba(255,255,255,0.12)"
      w="fit-content"
      maxW="100%"
    >
      <Box display="flex" alignItems="center" justifyContent="center" minW="20px">
        <TypingPulse isActive size="sm" intensity="subtle" style="dots" />
      </Box>
      <Text color={colors.text.secondary} fontSize="xs" noOfLines={1}>
        {label}
      </Text>
    </HStack>
  );
}

export default ThinkingStatusChip;
