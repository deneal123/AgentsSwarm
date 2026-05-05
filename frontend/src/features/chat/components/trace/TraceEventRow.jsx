import React from 'react';
import { Badge, Box, HStack, Text } from '@chakra-ui/react';
import { colors } from '@theme/tokens';
import { traceItemReveal } from '../../styles/keyframes';

function TraceEventRow({ event, eventIndex = 0 }) {
  const badgeScheme = event.kind === 'error' ? 'red' : event.kind === 'done' ? 'gray' : 'red';
  const accentColor = event.kind === 'error' ? 'rgba(255, 107, 107, 0.95)' : event.kind === 'done' ? 'rgba(212, 212, 212, 0.95)' : 'rgba(239, 68, 68, 0.95)';
  const badgeLabel = event.kind === 'error' ? 'Ошибка' : event.kind === 'done' ? 'Готово' : 'Шаг';

  return (
    <Box
      border="1px solid rgba(255, 255, 255, 0.2)"
      borderRadius="xl"
      p={2.5}
      bg="rgba(255, 255, 255, 0.04)"
      position="relative"
      pl={3.5}
      sx={{ animation: `${traceItemReveal} 220ms ease ${Math.min(eventIndex * 35, 210)}ms both` }}
    >
      <Box position="absolute" left="10px" top="11px" bottom="11px" w="2px" borderRadius="full" bg={accentColor} opacity={0.95} />
      <HStack justify="space-between" align="flex-start" spacing={2}>
        <HStack spacing={2} align="center" flex="1" minW={0}>
          <Badge colorScheme={badgeScheme} borderRadius="full" px={2} flexShrink={0}>{badgeLabel}</Badge>
          <Text fontSize="sm" color={colors.text.primary} fontWeight="500" noOfLines={2}>{event.title}</Text>
        </HStack>
        <Text fontSize="10px" color={colors.text.tertiary} flexShrink={0}>
          {new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </Text>
      </HStack>
      {event.detail && <Text mt={1.5} fontSize="xs" color={colors.text.tertiary} lineHeight="1.5">{event.detail}</Text>}
    </Box>
  );
}

export default TraceEventRow;
