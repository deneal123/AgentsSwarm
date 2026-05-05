import React from 'react';
import {
  Accordion,
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Badge,
  Box,
  HStack,
  Icon,
  Text,
  VStack,
} from '@chakra-ui/react';
import { FiAlertCircle, FiCheckCircle } from 'react-icons/fi';
import { colors } from '@theme/tokens';
import TraceEventRow from './TraceEventRow';
import { traceRingPulse, traceRingSpin } from '../../styles/keyframes';

function TraceSessionCard({ session, isCompactTrace, isExpanded, onToggleExpanded }) {
  const sessionEvents = session.events || [];
  const visibleTraceEvents = isCompactTrace ? sessionEvents.slice(-6) : sessionEvents;
  const hiddenTraceEventsCount = Math.max(0, sessionEvents.length - visibleTraceEvents.length);
  const isRunning = session.status === 'running';
  const isError = session.status === 'error';

  return (
    <Box w="100%" maxW="980px" border="1px solid rgba(239, 68, 68, 0.45)" borderRadius="2xl" bg="linear-gradient(160deg, rgba(255, 255, 255, 0.04) 0%, rgba(239, 68, 68, 0.08) 100%)" boxShadow="0 10px 26px rgba(4, 8, 16, 0.28), inset 0 1px 0 rgba(255,255,255,0.08)" overflow="hidden" position="relative">
      <Box position="absolute" top={0} left={0} right={0} h="1px" bg="linear-gradient(90deg, rgba(239,68,68,0.95) 0%, rgba(248,113,113,0.95) 100%)" />
      <Accordion allowToggle index={isExpanded ? 0 : -1} onChange={(nextIndex) => onToggleExpanded(typeof nextIndex === 'number' && nextIndex >= 0)}>
        <AccordionItem border="none">
          <h2>
            <AccordionButton py={3} px={4} _hover={{ bg: 'rgba(239, 68, 68, 0.12)' }}>
              <HStack flex="1" justify="space-between" spacing={3}>
                <HStack spacing={2} align="center" minW={0}>
                  {isRunning ? (
                    <Box w="14px" h="14px" borderRadius="full" flexShrink={0} sx={{ border: '2px solid rgba(239,68,68,0.22)', borderTopColor: 'rgba(248,113,113,0.95)', borderRightColor: 'rgba(239,68,68,0.7)', animation: `${traceRingSpin} 0.8s linear infinite, ${traceRingPulse} 1.6s ease-in-out infinite` }} />
                  ) : <Icon as={isError ? FiAlertCircle : FiCheckCircle} color={isError ? 'red.300' : 'gray.300'} boxSize={4} />}
                  <Badge colorScheme={isError ? 'red' : (isRunning ? 'red' : 'gray')} borderRadius="full" px={2} flexShrink={0} textTransform="uppercase" letterSpacing="0.04em">{isError ? 'Ошибка' : (isRunning ? 'В работе' : 'Готово')}</Badge>
                  <Text fontSize="sm" color={colors.text.primary} fontWeight="600" noOfLines={1}>Подготовка ответа</Text>
                  <Text fontSize="xs" color={colors.text.tertiary} flexShrink={0}>{sessionEvents.length} шаг(ов)</Text>
                </HStack>
                <Text fontSize="xs" color={colors.text.tertiary}>{isExpanded ? 'Свернуть' : 'Развернуть'}</Text>
              </HStack>
              <AccordionIcon color={colors.text.tertiary} />
            </AccordionButton>
          </h2>
          <AccordionPanel px={4} pb={3.5} pt={1.5}>
            {session.title && <Text fontSize="xs" color={colors.text.tertiary} mb={2.5} noOfLines={2}>Запрос: {session.title}</Text>}
            <VStack align="stretch" spacing={2.5}>
              {visibleTraceEvents.map((event, eventIndex) => <TraceEventRow key={event.id} event={event} eventIndex={eventIndex} />)}
              {hiddenTraceEventsCount > 0 && <Text fontSize="xs" color={colors.text.tertiary} textAlign="center">В мобильном режиме скрыто шагов: {hiddenTraceEventsCount}</Text>}
            </VStack>
          </AccordionPanel>
        </AccordionItem>
      </Accordion>
    </Box>
  );
}

export default TraceSessionCard;
