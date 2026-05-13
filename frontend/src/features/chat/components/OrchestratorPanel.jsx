import React, { memo, useEffect, useRef, useState } from 'react';
import {
  Accordion,
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Badge,
  Box,
  Collapse,
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
  FiLayers,
  FiMapPin,
  FiMessageSquare,
  FiTool,
  FiXCircle,
  FiZap,
} from 'react-icons/fi';
import { traceRingPulse, traceRingSpin } from '../styles/keyframes';

// ─── Design tokens ────────────────────────────────────────────────────────────

const ACCENT = '#63b3ed';
const ACCENT_SOFT = 'rgba(99,179,237,0.12)';
const PANEL_BORDER = 'rgba(99,179,237,0.4)';
const PANEL_BG = 'linear-gradient(160deg,rgba(255,255,255,0.035) 0%,rgba(99,179,237,0.07) 100%)';

// ─── Status config ────────────────────────────────────────────────────────────

const STATUS_CFG = {
  idle:        { label: 'Ожидание',           color: 'gray',   icon: FiClock,        spinning: false },
  synthesizing:{ label: 'Формирую инструкцию',color: 'blue',   icon: null,           spinning: true  },
  creating:    { label: 'Создаю задачу',       color: 'blue',   icon: null,           spinning: true  },
  running:     { label: 'В работе',            color: 'blue',   icon: null,           spinning: true  },
  completed:   { label: 'Выполнено',           color: 'green',  icon: FiCheckCircle,  spinning: false },
  failed:      { label: 'Ошибка',              color: 'red',    icon: FiAlertCircle,  spinning: false },
  canceled:    { label: 'Отменено',            color: 'orange', icon: FiXCircle,      spinning: false },
};

const STEP_CFG = {
  pending:   { color: 'gray.500',  spinning: false, icon: FiClock       },
  running:   { color: ACCENT,      spinning: true,  icon: null          },
  completed: { color: 'green.400', spinning: false, icon: FiCheckCircle },
  failed:    { color: 'red.400',   spinning: false, icon: FiAlertCircle },
  canceled:  { color: 'orange.400',spinning: false, icon: FiXCircle     },
};

const LEVEL_COLOR = { info: 'rgba(255,255,255,0.78)', warning: '#fbbf24', error: '#f87171' };

const SOURCE_CFG = {
  orchestrator: { color: '#63b3ed', bg: 'rgba(99,179,237,0.12)',  icon: FiCpu,     label: 'orchestrator' },
  planner:      { color: '#b794f4', bg: 'rgba(183,148,244,0.12)', icon: FiLayers,  label: 'planner'      },
  agent:        { color: '#68d391', bg: 'rgba(104,211,145,0.12)', icon: FiZap,     label: 'agent'        },
  runner:       { color: '#76e4f7', bg: 'rgba(118,228,247,0.12)', icon: FiZap,     label: 'runner'       },
  'agent-sdk':  { color: 'rgba(255,255,255,0.4)', bg: 'rgba(255,255,255,0.06)', icon: FiTool, label: 'sdk' },
};
const DEFAULT_SOURCE_CFG = { color: 'rgba(255,255,255,0.4)', bg: 'rgba(255,255,255,0.06)', icon: FiCpu, label: 'sys' };

// ─── Atoms ────────────────────────────────────────────────────────────────────

function Spinner({ size = '14px' }) {
  return (
    <Box w={size} h={size} borderRadius="full" flexShrink={0} sx={{
      border: '2px solid rgba(99,179,237,0.2)',
      borderTopColor: ACCENT,
      borderRightColor: 'rgba(99,179,237,0.6)',
      animation: `${traceRingSpin} 0.8s linear infinite, ${traceRingPulse} 1.6s ease-in-out infinite`,
    }} />
  );
}

function SectionLabel({ children }) {
  return (
    <Text fontSize="10px" fontWeight="700" color="rgba(255,255,255,0.35)"
      textTransform="uppercase" letterSpacing="0.09em" mb={2} px={1}>
      {children}
    </Text>
  );
}

// ─── Reasoning block (collapsible, opt-in) ────────────────────────────────────

function ReasoningBlock({ text }) {
  const [open, setOpen] = useState(false);
  if (!text) return null;
  return (
    <Box border="1px solid rgba(168,85,247,0.25)" borderRadius="10px" overflow="hidden">
      {/* Header — always visible, clicking toggles body */}
      <HStack
        px={3} py={2} spacing={2} cursor="pointer"
        bg={open ? 'rgba(168,85,247,0.07)' : 'rgba(168,85,247,0.04)'}
        _hover={{ bg: 'rgba(168,85,247,0.09)' }}
        onClick={() => setOpen((v) => !v)}
        transition="background 0.15s"
      >
        <Icon as={FiMessageSquare} boxSize={3} color="rgba(192,132,252,0.8)" flexShrink={0} />
        <Text fontSize="10px" fontWeight="700" color="rgba(192,132,252,0.8)"
          textTransform="uppercase" letterSpacing="0.09em" flex="1">
          Рассуждения модели
        </Text>
        <Badge fontSize="9px" px={1.5} borderRadius="full"
          bg="rgba(168,85,247,0.15)" color="rgba(192,132,252,0.7)"
          border="1px solid rgba(168,85,247,0.2)" textTransform="none">
          {open ? 'скрыть' : 'показать'}
        </Badge>
      </HStack>
      <Collapse in={open} animateOpacity>
        <Box
          px={3} py={2.5}
          bg="rgba(168,85,247,0.03)"
          borderTop="1px solid rgba(168,85,247,0.15)"
          maxH="260px" overflowY="auto"
          sx={{
            '&::-webkit-scrollbar': { w: '3px' },
            '&::-webkit-scrollbar-track': { bg: 'transparent' },
            '&::-webkit-scrollbar-thumb': { bg: 'rgba(168,85,247,0.25)', borderRadius: '3px' },
          }}
        >
          <Text
            fontSize="12px"
            color="rgba(255,255,255,0.45)"
            lineHeight="1.7"
            whiteSpace="pre-wrap"
            fontStyle="italic"
          >
            {text}
          </Text>
        </Box>
      </Collapse>
    </Box>
  );
}

// ─── Plan step ────────────────────────────────────────────────────────────────

function PlanStep({ step }) {
  const cfg = STEP_CFG[step.status] || STEP_CFG.pending;
  return (
    <HStack spacing={3} px={1} py={1.5} align="center"
      borderBottom="1px solid rgba(255,255,255,0.04)" _last={{ borderBottom: 'none' }}>
      {cfg.spinning ? <Spinner size="13px" /> : <Icon as={cfg.icon} color={cfg.color} boxSize={3.5} flexShrink={0} />}
      <Text fontSize="12px" fontWeight="600" color="rgba(255,255,255,0.82)" flex="1" noOfLines={1}>
        {step.description || step.agent || `Шаг ${step.id}`}
      </Text>
      {step.agent && (
        <Badge px={2} py={0} borderRadius="full" fontSize="10px" fontWeight="600"
          textTransform="none" background={ACCENT_SOFT} color={ACCENT}
          border="1px solid rgba(99,179,237,0.22)" flexShrink={0}>
          {step.agent}
        </Badge>
      )}
      <Badge fontSize="10px" borderRadius="full" flexShrink={0} textTransform="none"
        colorScheme={
          step.status === 'completed' ? 'green' :
          step.status === 'running'   ? 'blue'  :
          step.status === 'failed'    ? 'red'   :
          step.status === 'canceled'  ? 'orange': 'gray'
        }>
        {step.status || 'pending'}
      </Badge>
    </HStack>
  );
}

// ─── Event row ────────────────────────────────────────────────────────────────

function EventRow({ ev }) {
  const msgColor = LEVEL_COLOR[ev.level] || LEVEL_COLOR.info;
  const src = SOURCE_CFG[ev.source] || DEFAULT_SOURCE_CFG;
  const ts = ev.ts
    ? new Date(ev.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : '';

  // Detect completion / error keywords for subtle emphasis
  const msgLower = (ev.message || '').toLowerCase();
  const isComplete = msgLower.includes('completed') || msgLower.includes('завершен');
  const isError = ev.level === 'error' || msgLower.includes('failed') || msgLower.includes('error');

  return (
    <HStack
      spacing={0}
      align="flex-start"
      py={1.5}
      px={2}
      borderRadius="8px"
      borderLeft={isComplete ? '2px solid rgba(104,211,145,0.5)' : isError ? '2px solid rgba(248,113,113,0.5)' : '2px solid transparent'}
      bg={isComplete ? 'rgba(104,211,145,0.04)' : isError ? 'rgba(248,113,113,0.04)' : 'transparent'}
      _hover={{ bg: 'rgba(255,255,255,0.03)' }}
      transition="background 0.1s"
      gap={2}
    >
      {/* Timestamp */}
      <Text fontSize="10px" color="rgba(255,255,255,0.22)" flexShrink={0} mt="2px" fontFamily="mono" minW="54px">
        {ts}
      </Text>

      {/* Source chip */}
      <HStack
        spacing={1}
        px={1.5}
        py={0.5}
        borderRadius="5px"
        bg={src.bg}
        flexShrink={0}
        minW="80px"
        justify="center"
      >
        <Icon as={src.icon} boxSize={2.5} color={src.color} flexShrink={0} />
        <Text fontSize="9px" fontWeight="700" color={src.color} letterSpacing="0.04em" textTransform="uppercase">
          {src.label}
        </Text>
      </HStack>

      {/* Message */}
      <Text fontSize="12.5px" color={msgColor} lineHeight="1.5" flex="1" wordBreak="break-word">
        {ev.message}
      </Text>
    </HStack>
  );
}

// ─── Scrollable event feed ────────────────────────────────────────────────────

function EventFeed({ events }) {
  const scrollRef = useRef(null);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  const visible = events.slice(-60);

  return (
    <Box ref={scrollRef} bg="rgba(0,0,0,0.18)" border="1px solid rgba(255,255,255,0.06)"
      borderRadius="12px" px={1} py={1.5} maxH="260px" overflowY="auto"
      sx={{
        '&::-webkit-scrollbar': { w: '3px' },
        '&::-webkit-scrollbar-track': { bg: 'transparent' },
        '&::-webkit-scrollbar-thumb': { bg: 'rgba(255,255,255,0.1)', borderRadius: '3px' },
      }}>
      <VStack align="stretch" spacing={0}>
        {visible.map((ev) => <EventRow key={ev._id || ev.ts} ev={ev} />)}
      </VStack>
    </Box>
  );
}

// ─── Image gallery ────────────────────────────────────────────────────────────

function ImageGallery({ images }) {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedIdx, setSelectedIdx] = useState(0);

  if (!images || images.length === 0) return null;

  const openImage = (idx) => { setSelectedIdx(idx); onOpen(); };

  return (
    <>
      <Box>
        <HStack spacing={2} mb={2.5} px={1}>
          <Icon as={FiImage} boxSize={3} color={ACCENT} />
          <SectionLabel>Карты и визуализации</SectionLabel>
        </HStack>
        <Grid templateColumns="repeat(auto-fill, minmax(120px, 1fr))" gap={2}>
          {images.map((img, idx) => (
            <Tooltip key={img.id || idx} label={img.label} placement="top">
              <Box borderRadius="10px" overflow="hidden" border="1px solid rgba(99,179,237,0.2)"
                cursor="pointer" onClick={() => openImage(idx)} bg="rgba(0,0,0,0.3)"
                transition="all 0.15s" _hover={{ borderColor: ACCENT, transform: 'scale(1.03)' }}>
                <Image src={img.src} alt={img.label} w="100%" h="80px" objectFit="cover"
                  fallback={
                    <Box h="80px" display="flex" alignItems="center" justifyContent="center">
                      <Icon as={FiMapPin} color={ACCENT} boxSize={4} />
                    </Box>
                  }
                />
                <HStack px={1.5} py={1} spacing={1}>
                  {img.isBest && <Badge fontSize="8px" colorScheme="green" borderRadius="full">★</Badge>}
                  <Text fontSize="10px" color="rgba(255,255,255,0.5)" noOfLines={1} fontWeight="500">
                    {img.label}
                  </Text>
                </HStack>
              </Box>
            </Tooltip>
          ))}
        </Grid>
      </Box>

      <Modal isOpen={isOpen} onClose={onClose} size="4xl" isCentered>
        <ModalOverlay backdropFilter="blur(8px)" bg="rgba(0,0,0,0.75)" />
        <ModalContent bg="rgba(8,10,18,0.98)" border={`1px solid ${PANEL_BORDER}`} borderRadius="20px">
          <ModalHeader color="white" fontSize="14px" fontWeight="600" pr={10}>
            {images[selectedIdx]?.label}
            {images[selectedIdx]?.isBest && (
              <Badge ml={2} colorScheme="green" borderRadius="full" fontSize="10px">Лучший маршрут</Badge>
            )}
          </ModalHeader>
          <ModalCloseButton color="rgba(255,255,255,0.45)" />
          <ModalBody pb={6}>
            <Box display="flex" justifyContent="center">
              <Image src={images[selectedIdx]?.src} alt={images[selectedIdx]?.label}
                maxH="70vh" objectFit="contain" borderRadius="12px" />
            </Box>
            {images.length > 1 && (
              <HStack mt={3} justify="center" spacing={2} flexWrap="wrap">
                {images.map((img, idx) => (
                  <Box key={img.id || idx} w="56px" h="42px" borderRadius="8px" overflow="hidden"
                    cursor="pointer" onClick={() => setSelectedIdx(idx)}
                    border={`2px solid ${idx === selectedIdx ? ACCENT : 'transparent'}`}
                    _hover={{ borderColor: ACCENT }} transition="border 0.15s">
                    <Image src={img.src} w="100%" h="100%" objectFit="cover" />
                  </Box>
                ))}
              </HStack>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
}

// ─── Main panel ───────────────────────────────────────────────────────────────

function OrchestratorPanelComponent({ orchestratorState }) {
  const { status, taskId, instruction, reasoning, plan, events, images } = orchestratorState;
  const [isExpanded, setIsExpanded] = useState(true);

  const cfg = STATUS_CFG[status] || STATUS_CFG.idle;
  const isRunning = cfg.spinning;

  return (
    <Box w="100%" maxW="980px" border={`1px solid ${PANEL_BORDER}`} borderRadius="2xl"
      bg={PANEL_BG} overflow="hidden" position="relative"
      boxShadow="0 10px 26px rgba(4,8,16,0.28), inset 0 1px 0 rgba(255,255,255,0.06)">

      {/* Blue accent line (vs red for GPTHub trace panel) */}
      <Box position="absolute" top={0} left={0} right={0} h="1px"
        bg={`linear-gradient(90deg,${ACCENT} 0%,rgba(99,179,237,0.5) 100%)`} />

      <Accordion allowToggle index={isExpanded ? 0 : -1}
        onChange={(idx) => setIsExpanded(typeof idx === 'number' && idx >= 0)}>
        <AccordionItem border="none">
          <AccordionButton py={3} px={4} _hover={{ bg: 'rgba(99,179,237,0.07)' }}>
            <HStack flex="1" justify="space-between" spacing={3}>
              <HStack spacing={2} align="center" minW={0}>
                {isRunning ? <Spinner /> : cfg.icon
                  ? <Icon as={cfg.icon}
                      color={cfg.color === 'green' ? 'green.300' : cfg.color === 'red' ? 'red.300' : ACCENT}
                      boxSize={4} />
                  : null
                }
                <Icon as={FiCpu} boxSize={3.5} color={ACCENT} opacity={0.7} />
                <Text fontSize="13px" fontWeight="700" color="white" letterSpacing="-0.01em">
                  Рой роботов
                </Text>
                <Badge colorScheme={cfg.color} borderRadius="full" px={2}
                  fontSize="10px" textTransform="none" letterSpacing="0.02em">
                  {cfg.label}
                </Badge>
                {taskId && (
                  <Text fontSize="10px" color="rgba(255,255,255,0.3)" fontFamily="mono" noOfLines={1}>
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
                <Text fontSize="11px" color="rgba(255,255,255,0.3)">
                  {isExpanded ? 'Свернуть' : 'Развернуть'}
                </Text>
              </HStack>
            </HStack>
            <AccordionIcon color="rgba(255,255,255,0.3)" />
          </AccordionButton>

          <AccordionPanel px={4} pb={4} pt={1}>
            <VStack align="stretch" spacing={4}>

              {/* Reasoning — collapsed by default, optional */}
              {reasoning && <ReasoningBlock text={reasoning} />}

              {/* Instruction */}
              {instruction && (
                <Box bg="rgba(99,179,237,0.05)" border="1px solid rgba(99,179,237,0.14)"
                  borderRadius="10px" px={3} py={2.5}>
                  <Text fontSize="10px" fontWeight="700" color={ACCENT}
                    textTransform="uppercase" letterSpacing="0.08em" mb={1}>
                    Инструкция оркестратору
                  </Text>
                  <Text fontSize="12px" color="rgba(255,255,255,0.72)" lineHeight="1.65">
                    {instruction}
                  </Text>
                </Box>
              )}

              {/* Plan */}
              {plan.length > 0 && (
                <Box>
                  <SectionLabel>План выполнения · {plan.length} шаг(а)</SectionLabel>
                  <Box bg="rgba(0,0,0,0.18)" border="1px solid rgba(255,255,255,0.05)"
                    borderRadius="10px" px={2} py={1}>
                    {plan.map((step) => <PlanStep key={step.id} step={step} />)}
                  </Box>
                </Box>
              )}

              {/* Live events */}
              {events.length > 0 && (
                <Box>
                  <SectionLabel>Поток событий · {events.length}</SectionLabel>
                  <EventFeed events={events} />
                </Box>
              )}

              {/* Images */}
              {images.length > 0 && <ImageGallery images={images} />}

              {/* Empty running placeholder */}
              {isRunning && events.length === 0 && !instruction && (
                <HStack spacing={2} px={1} py={1}>
                  <Spinner size="12px" />
                  <Text fontSize="12px" color="rgba(255,255,255,0.35)">
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
