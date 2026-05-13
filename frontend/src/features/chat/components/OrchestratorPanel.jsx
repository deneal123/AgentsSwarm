import React, { memo, useState } from 'react';
import {
  Accordion,
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Badge,
  Box,
  Grid,
  HStack,
  Icon,
  Image,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
  Text,
  Tooltip,
  useDisclosure,
  VStack,
} from '@chakra-ui/react';
import {
  FiAlertCircle,
  FiCheckCircle,
  FiClock,
  FiCpu,
  FiImage,
  FiLoader,
  FiMapPin,
  FiXCircle,
} from 'react-icons/fi';
import { traceRingPulse, traceRingSpin } from '../styles/keyframes';

// ─── Constants ──────────────────────────────────────────────────────────────

const PANEL_BORDER = 'rgba(99, 179, 237, 0.45)';
const PANEL_BG = 'linear-gradient(160deg, rgba(255,255,255,0.04) 0%, rgba(99,179,237,0.08) 100%)';
const ACCENT = '#63b3ed';
const ACCENT_SOFT = 'rgba(99,179,237,0.15)';

const STATUS_CONFIG = {
  idle: { label: 'Ожидание', color: 'gray', icon: FiClock },
  synthesizing: { label: 'Формирую инструкцию', color: 'blue', icon: FiLoader, spinning: true },
  creating: { label: 'Создаю задачу', color: 'blue', icon: FiLoader, spinning: true },
  running: { label: 'В работе', color: 'blue', icon: FiLoader, spinning: true },
  completed: { label: 'Выполнено', color: 'green', icon: FiCheckCircle },
  failed: { label: 'Ошибка', color: 'red', icon: FiAlertCircle },
  canceled: { label: 'Отменено', color: 'orange', icon: FiXCircle },
};

const STEP_STATUS_CONFIG = {
  pending: { icon: FiClock, color: 'gray.400' },
  running: { icon: FiLoader, color: ACCENT, spinning: true },
  completed: { icon: FiCheckCircle, color: 'green.400' },
  failed: { icon: FiAlertCircle, color: 'red.400' },
  canceled: { icon: FiXCircle, color: 'orange.400' },
};

const LEVEL_COLORS = {
  info: 'rgba(255,255,255,0.65)',
  warning: '#fbbf24',
  error: '#f87171',
};

// ─── Sub-components ──────────────────────────────────────────────────────────

function SpinnerRing({ size = '14px', color = ACCENT }) {
  return (
    <Box
      w={size}
      h={size}
      borderRadius="full"
      flexShrink={0}
      sx={{
        border: `2px solid rgba(99,179,237,0.22)`,
        borderTopColor: color,
        borderRightColor: `rgba(99,179,237,0.7)`,
        animation: `${traceRingSpin} 0.8s linear infinite, ${traceRingPulse} 1.6s ease-in-out infinite`,
      }}
    />
  );
}

function PlanStep({ step }) {
  const cfg = STEP_STATUS_CONFIG[step.status] || STEP_STATUS_CONFIG.pending;
  return (
    <HStack spacing={3} px={1} py={1.5} align="center">
      {cfg.spinning ? (
        <SpinnerRing size="13px" />
      ) : (
        <Icon as={cfg.icon} color={cfg.color} boxSize={3.5} flexShrink={0} />
      )}
      <VStack align="start" spacing={0} flex="1" minW="0">
        <HStack spacing={2}>
          <Text fontSize="12px" fontWeight="600" color="rgba(255,255,255,0.85)" noOfLines={1}>
            {step.description || step.agent || `Шаг ${step.id}`}
          </Text>
          {step.agent && (
            <Badge
              px={1.5}
              py={0}
              borderRadius="full"
              fontSize="10px"
              fontWeight="600"
              textTransform="none"
              background={ACCENT_SOFT}
              color={ACCENT}
              border={`1px solid rgba(99,179,237,0.25)`}
            >
              {step.agent}
            </Badge>
          )}
        </HStack>
      </VStack>
      <Badge
        px={2}
        borderRadius="full"
        fontSize="10px"
        colorScheme={
          step.status === 'completed' ? 'green'
          : step.status === 'running' ? 'blue'
          : step.status === 'failed' ? 'red'
          : step.status === 'canceled' ? 'orange'
          : 'gray'
        }
        textTransform="none"
        flexShrink={0}
      >
        {step.status || 'pending'}
      </Badge>
    </HStack>
  );
}

function EventRow({ event }) {
  const color = LEVEL_COLORS[event.level] || LEVEL_COLORS.info;
  const ts = event.ts ? new Date(event.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '';
  return (
    <HStack spacing={2} align="flex-start" py={1}>
      <Text fontSize="10px" color="rgba(255,255,255,0.3)" flexShrink={0} mt="1px" fontFamily="mono">
        {ts}
      </Text>
      <Text fontSize="10px" color="rgba(99,179,237,0.7)" flexShrink={0} fontFamily="mono">
        {event.source || 'sys'}
      </Text>
      <Text fontSize="12px" color={color} lineHeight="1.4" flex="1" wordBreak="break-word">
        {event.message}
      </Text>
    </HStack>
  );
}

function ImageGallery({ images }) {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedIdx, setSelectedIdx] = useState(0);

  if (!images || images.length === 0) return null;

  const openImage = (idx) => {
    setSelectedIdx(idx);
    onOpen();
  };

  const getImageSrc = (img) => {
    const data = img.data || img;
    if (typeof data === 'string') {
      if (data.startsWith('data:') || data.startsWith('http')) return data;
      return `data:image/png;base64,${data}`;
    }
    return null;
  };

  return (
    <>
      <Box>
        <HStack spacing={2} mb={2.5} px={1}>
          <Icon as={FiImage} boxSize={3} color={ACCENT} />
          <Text fontSize="10.5px" fontWeight="700" color="rgba(255,255,255,0.5)" textTransform="uppercase" letterSpacing="0.08em">
            Карты и визуализации
          </Text>
        </HStack>
        <Grid templateColumns="repeat(auto-fill, minmax(130px, 1fr))" gap={2}>
          {images.map((img, idx) => {
            const src = getImageSrc(img);
            if (!src) return null;
            return (
              <Tooltip key={img.id || idx} label={img.label || `Изображение ${idx + 1}`} placement="top">
                <Box
                  borderRadius="10px"
                  overflow="hidden"
                  border={`1px solid rgba(99,179,237,0.25)`}
                  cursor="pointer"
                  onClick={() => openImage(idx)}
                  _hover={{ borderColor: ACCENT, transform: 'scale(1.03)', transition: 'all 0.15s' }}
                  transition="all 0.15s"
                  bg="rgba(0,0,0,0.3)"
                >
                  <Image
                    src={src}
                    alt={img.label || `Map ${idx + 1}`}
                    w="100%"
                    h="90px"
                    objectFit="cover"
                    fallback={
                      <Box h="90px" display="flex" alignItems="center" justifyContent="center">
                        <Icon as={FiMapPin} color={ACCENT} boxSize={5} />
                      </Box>
                    }
                  />
                  <Text
                    fontSize="10px"
                    color="rgba(255,255,255,0.55)"
                    px={2}
                    py={1}
                    noOfLines={1}
                    fontWeight="500"
                  >
                    {img.label || `Карта ${idx + 1}`}
                  </Text>
                </Box>
              </Tooltip>
            );
          })}
        </Grid>
      </Box>

      <Modal isOpen={isOpen} onClose={onClose} size="4xl" isCentered>
        <ModalOverlay backdropFilter="blur(8px)" bg="rgba(0,0,0,0.7)" />
        <ModalContent bg="rgba(10,10,18,0.97)" border={`1px solid ${PANEL_BORDER}`} borderRadius="20px">
          <ModalHeader color="white" fontSize="14px" fontWeight="600">
            {images[selectedIdx]?.label || `Изображение ${selectedIdx + 1}`}
          </ModalHeader>
          <ModalCloseButton color="rgba(255,255,255,0.5)" />
          <ModalBody pb={6}>
            <Box display="flex" justifyContent="center">
              <Image
                src={getImageSrc(images[selectedIdx])}
                alt={images[selectedIdx]?.label}
                maxH="70vh"
                objectFit="contain"
                borderRadius="12px"
              />
            </Box>
            {images.length > 1 && (
              <HStack mt={3} justify="center" spacing={2} flexWrap="wrap">
                {images.map((img, idx) => {
                  const src = getImageSrc(img);
                  if (!src) return null;
                  return (
                    <Box
                      key={img.id || idx}
                      w="60px"
                      h="45px"
                      borderRadius="8px"
                      overflow="hidden"
                      cursor="pointer"
                      border={`2px solid ${idx === selectedIdx ? ACCENT : 'transparent'}`}
                      onClick={() => setSelectedIdx(idx)}
                      _hover={{ borderColor: ACCENT }}
                      transition="border 0.15s"
                    >
                      <Image src={src} w="100%" h="100%" objectFit="cover" />
                    </Box>
                  );
                })}
              </HStack>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

function OrchestratorPanelComponent({ orchestratorState, isExpanded: defaultExpanded = true }) {
  const { status, taskId, instruction, plan, events, images } = orchestratorState;
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.idle;
  const isRunning = status === 'synthesizing' || status === 'creating' || status === 'running';

  // Show only last 30 events to avoid overflow, most recent at bottom
  const visibleEvents = events.slice(-30);

  return (
    <Box
      w="100%"
      maxW="980px"
      border={`1px solid ${PANEL_BORDER}`}
      borderRadius="2xl"
      bg={PANEL_BG}
      boxShadow="0 10px 26px rgba(4,8,16,0.28), inset 0 1px 0 rgba(255,255,255,0.06)"
      overflow="hidden"
      position="relative"
    >
      {/* Blue top accent line (vs red for trace panel) */}
      <Box position="absolute" top={0} left={0} right={0} h="1px" bg={`linear-gradient(90deg, ${ACCENT} 0%, rgba(99,179,237,0.6) 100%)`} />

      <Accordion allowToggle index={isExpanded ? 0 : -1} onChange={(idx) => setIsExpanded(typeof idx === 'number' && idx >= 0)}>
        <AccordionItem border="none">
          <h2>
            <AccordionButton py={3} px={4} _hover={{ bg: 'rgba(99,179,237,0.08)' }}>
              <HStack flex="1" justify="space-between" spacing={3}>
                <HStack spacing={2} align="center" minW={0}>
                  {isRunning ? (
                    <SpinnerRing />
                  ) : (
                    <Icon as={cfg.icon} color={cfg.color === 'green' ? 'green.300' : cfg.color === 'red' ? 'red.300' : ACCENT} boxSize={4} />
                  )}
                  <Icon as={FiCpu} boxSize={3.5} color={ACCENT} opacity={0.7} />
                  <Text fontSize="13px" fontWeight="700" color="white" letterSpacing="-0.01em">
                    Рой роботов
                  </Text>
                  <Badge colorScheme={cfg.color} borderRadius="full" px={2} textTransform="none" fontSize="10px" letterSpacing="0.02em">
                    {cfg.label}
                  </Badge>
                  {taskId && (
                    <Text fontSize="10px" color="rgba(255,255,255,0.35)" fontFamily="mono" noOfLines={1}>
                      {taskId.slice(0, 12)}…
                    </Text>
                  )}
                </HStack>
                <HStack spacing={3} flexShrink={0}>
                  {images.length > 0 && (
                    <HStack spacing={1}>
                      <Icon as={FiImage} boxSize={3} color={ACCENT} />
                      <Text fontSize="10px" color={ACCENT}>{images.length}</Text>
                    </HStack>
                  )}
                  <Text fontSize="11px" color="rgba(255,255,255,0.35)">{isExpanded ? 'Свернуть' : 'Развернуть'}</Text>
                </HStack>
              </HStack>
              <AccordionIcon color="rgba(255,255,255,0.35)" />
            </AccordionButton>
          </h2>

          <AccordionPanel px={4} pb={4} pt={1}>
            <VStack align="stretch" spacing={4}>

              {/* Instruction */}
              {instruction && (
                <Box
                  bg="rgba(99,179,237,0.06)"
                  border="1px solid rgba(99,179,237,0.15)"
                  borderRadius="10px"
                  px={3}
                  py={2.5}
                >
                  <Text fontSize="10px" fontWeight="700" color={ACCENT} textTransform="uppercase" letterSpacing="0.08em" mb={1}>
                    Инструкция оркестратору
                  </Text>
                  <Text fontSize="12px" color="rgba(255,255,255,0.75)" lineHeight="1.6">
                    {instruction}
                  </Text>
                </Box>
              )}

              {/* Plan */}
              {plan.length > 0 && (
                <Box>
                  <Text fontSize="10px" fontWeight="700" color="rgba(255,255,255,0.4)" textTransform="uppercase" letterSpacing="0.08em" mb={2} px={1}>
                    План выполнения
                  </Text>
                  <VStack align="stretch" spacing={0} divider={<Box borderTop="1px solid rgba(255,255,255,0.04)" />}>
                    {plan.map((step) => (
                      <PlanStep key={step.id} step={step} />
                    ))}
                  </VStack>
                </Box>
              )}

              {/* Live events */}
              {visibleEvents.length > 0 && (
                <Box>
                  <Text fontSize="10px" fontWeight="700" color="rgba(255,255,255,0.4)" textTransform="uppercase" letterSpacing="0.08em" mb={2} px={1}>
                    Поток событий
                  </Text>
                  <Box
                    bg="rgba(0,0,0,0.25)"
                    border="1px solid rgba(255,255,255,0.06)"
                    borderRadius="10px"
                    px={3}
                    py={2}
                    maxH="200px"
                    overflowY="auto"
                    sx={{
                      '&::-webkit-scrollbar': { w: '4px' },
                      '&::-webkit-scrollbar-track': { bg: 'transparent' },
                      '&::-webkit-scrollbar-thumb': { bg: 'rgba(255,255,255,0.12)', borderRadius: '4px' },
                    }}
                  >
                    <VStack align="stretch" spacing={0}>
                      {visibleEvents.map((ev) => (
                        <EventRow key={ev.id || ev.ts} event={ev} />
                      ))}
                    </VStack>
                  </Box>
                </Box>
              )}

              {/* Image gallery */}
              {images.length > 0 && <ImageGallery images={images} />}

              {/* Empty running state */}
              {isRunning && visibleEvents.length === 0 && !instruction && (
                <HStack spacing={2} px={1} py={1}>
                  <SpinnerRing size="12px" />
                  <Text fontSize="12px" color="rgba(255,255,255,0.4)">
                    Подключаемся к оркестратору...
                  </Text>
                </HStack>
              )}
            </VStack>
          </AccordionPanel>
        </AccordionItem>
      </Accordion>
    </Box>
  );
}

const OrchestratorPanel = memo(OrchestratorPanelComponent);
export default OrchestratorPanel;
