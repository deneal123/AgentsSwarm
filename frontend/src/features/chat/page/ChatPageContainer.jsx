import React, { Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { keyframes } from '@emotion/react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import {
  Badge,
  Box,
  Button,
  Center,
  Drawer,
  DrawerBody,
  DrawerCloseButton,
  DrawerContent,
  DrawerHeader,
  DrawerOverlay,
  Divider,
  Flex,
  HStack,
  Icon,
  IconButton,
  Spinner,
  Switch,
  Text,
  VStack,
  useBreakpointValue,
} from '@chakra-ui/react';
import { getChatModels, sendChatMessage } from '@api/chat';
import { colors } from '@theme/tokens';
import { extractUrlCandidates } from '@utils/urlParser';
import {
  FiAlertCircle,
  FiAlertTriangle,
  FiCopy,
  FiEye,
  FiInfo,
  FiLayers,
  FiRotateCcw,
  FiSearch,
  FiZap,
  FiMenu,
  FiSettings,
} from 'react-icons/fi';
import MessageRenderer from '../components/MessageRenderer';
import ChatPageLayout from './ChatPageLayout';
import { CHAT_SCROLLBAR_SX, CHAT_THEME } from '../constants/theme';
import { useChatTransport, useProfileAndAuthFlow, useSidebarState, useChatSideEffects } from '../hooks';
import { useLayoutControls } from '@app/providers';
import { useChatInitialization } from '../hooks/orchestration/useChatInitialization';
import { useChatThreadRouting } from '../hooks/orchestration/useChatThreadRouting';
import { useChatDrawersState } from '../hooks/orchestration/useChatDrawersState';
import { useChatStreamingLifecycle } from '../hooks/orchestration/useChatStreamingLifecycle';
import { CHAT_UI_CONFIG } from '../config/uiConfig';
import { useTraceSessions } from '../hooks/useTraceSessions';
import { useChatDomainState } from '../hooks/useChatDomainState';
import { useMessageActions } from '../hooks/useMessageActions';
import { useRecentThreads } from '../hooks/useRecentThreads';
import { useChatUiSettings } from '../hooks/useChatUiSettings';
import { clampTraceDetail } from '../utils/trace';
import ModelSelector from '../components/ModelSelector';
import ChatComposerPanel from '../components/composer/ChatComposerPanel';
import ChatSidebarPanel from '../components/ChatSidebarPanel';
import { PROSE_SX } from './proseStyles';
import { ProfileDrawer } from '@features/profile';

const TracePanel = lazy(() => import('../components/trace/TracePanel'));

const dotPulse = keyframes`
  0%, 80%, 100% { opacity: 0.35; transform: scale(0.92); }
  40% { opacity: 1; transform: scale(1); }
`;

const bgAuroraA = keyframes`
  0%, 100% { transform: translate3d(0,0,0) scale(1); }
  50% { transform: translate3d(18px,-14px,0) scale(1.06); }
`;

const bgAuroraB = keyframes`
  0%, 100% { transform: translate3d(0,0,0) scale(1); }
  50% { transform: translate3d(-14px,16px,0) scale(1.04); }
`;

const bgAuroraC = keyframes`
  0%, 100% { transform: translate3d(0,0,0) scale(1); }
  50% { transform: translate3d(10px,12px,0) scale(1.05); }
`;



/**
 * ChatPage - Страница чата с AI агентом
 *
 * Функциональность:
 * - WebSocket соединение для real-time общения
 * - Обработка гостевых сессий и лимитов
 * - Переход из поиска с начальным сообщением
 * - Предложение регистрации при лимитах
 */
function ChatPageContainer() {
  const { setVariant, setFooterVisible } = useLayoutControls();
  useEffect(() => {
    setVariant('full');
    setFooterVisible(false);
  }, [setVariant, setFooterVisible]);

  const location = useLocation();
  const { threadId: routeThreadId } = useParams();
  const init = useChatInitialization(routeThreadId);
  const { threadId, initialMessage, initialManualModel, initialInputType, initialWebSearch, initialDeepResearch, initialFileContext, selectedModelOverride } = init.state;
  const { setSelectedModelOverride } = init.actions;
  const navigate = useNavigate();
  useChatThreadRouting({ routeThreadId, initialMessage, threadId, navigate });
  const sideEffects = useChatSideEffects({ navigate });

  const {
    isAuthenticated, user, logout, incrementRequests, remainingRequests, profileDisclosure, profileData, profileMemoryCount, setProfileMemoryCount, isProfileLoading, resolveSessionUserId, isAuthModalOpen, onAuthModalClose, showAuthModal, modalData, AuthModal, ensureGuestLimit,
  } = useProfileAndAuthFlow();

  const drawers = useChatDrawersState(profileDisclosure);
  const { sidebarDisclosure, memoryDisclosure, settingsDisclosure, memoryFacts } = drawers.state;
  const { setMemoryFacts } = drawers.actions;

  // Open profile drawer when navigated with ?profile=open
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('profile') === 'open') {
      profileDisclosure.onOpen();
      navigate('/', { replace: true });
    }
  }, [location.search, navigate, profileDisclosure]);


  const [hasInitialized, setHasInitialized] = useState(false);
  const { state: domainState, actions: domainActions } = useChatDomainState();
  const { messages, loading: isLoading, error, currentJob } = domainState;
  const { setLoading: setIsLoading, setError, clearError, addMessage, clearMessages, replaceMessages, setCurrentJob, clearCurrentJob } = domainActions;
  const [availableModels, setAvailableModels] = useState([]);
  const [attachedFile, setAttachedFile] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const composerRef = useRef(null);
  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);

  const clearInput = useCallback(() => composerRef.current?.clearInput(), []);

  const { settings: chatUiSettings, setSettings: setChatUiSettings, resetUiSettings: resetPersistedUiSettings } = useChatUiSettings({ initialWebSearch, initialDeepResearch });
  const { webSearchEnabled, deepResearchEnabled, showTracePanel } = chatUiSettings;
  const messagesEndRef = useRef(null);
  const messagesScrollRef = useRef(null);
  const activeWsJobIdRef = useRef('');
  const lastWsReplyFingerprintRef = useRef('');
  const isCompactTrace = useBreakpointValue(CHAT_UI_CONFIG.trace.compactBreakpoint) ?? false;
  const {
    traceSessions,
    tracePanelsExpanded,
    setTracePanelsExpanded,
    traceSessionByAnchor,
    activeOrLatestTraceSession,
    startTraceSession,
    appendTraceEvent,
    finalizeTraceSession,
    resetTraceSessions,
  } = useTraceSessions({ showTracePanel });
  const {
    recentThreads,
    setRecentThreads,
    deletingThreadId,
    upsertRecentThread,
    handleDeleteThread,
  } = useRecentThreads({ navigate, resolveSessionUserId, threadId, setMessages: replaceMessages });
  const { sidebarSearch, setSidebarSearch, isSidebarCollapsed, setIsSidebarCollapsed, filteredRecentThreads } = useSidebarState({ recentThreads });


  const streamingLifecycle = useChatStreamingLifecycle({
    isLoading,
    setIsLoading,
    setError,
    appendTraceEvent,
    finalizeTraceSession,
    addMessage,
    appendStreamChunk: domainActions.updateLastAgentChunk,
    completeLastAgentMessage: domainActions.completeLastAgentMessage,
    finalizeStreamWithContent: domainActions.finalizeStreamWithContent,
    setCurrentJob,
    clearCurrentJob,
    setInputValue: clearInput,
  });
  const { wsCallbacks } = streamingLifecycle.actions;

  const {
    connectionState,
    sendMessage: wsSendMessage,
    cancelJob,
    useWebSocket,
  } = useChatTransport({ threadId, callbacks: wsCallbacks });

  const handleCancelJob = useCallback(async (jobId) => {
    try {
      await cancelJob(jobId);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Не удалось отменить задачу';
      sideEffects.notify({ title: 'Ошибка отмены', description: message, status: 'warning', duration: 3000 });
    } finally {
      setIsLoading(false);
      clearCurrentJob();
    }
  }, [cancelJob, clearCurrentJob, setIsLoading, sideEffects]);

  useEffect(() => {
    const container = messagesScrollRef.current;
    if (!container) return;
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    if (distanceFromBottom < 260) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages]);

  // Load recent threads for sidebar
  useEffect(() => {
    let cancelled = false;
    const loadThreads = async () => {
      try {
        const { getUserChats } = await import('@api/chat');
        const data = await getUserChats(null, 15);
        if (!cancelled) {
          const list = Array.isArray(data) ? data : (data.chats || data.threads || []);
          setRecentThreads(list);
        }
      } catch {
        // silent — sidebar is non-critical
      }
    };
    loadThreads();
    return () => { cancelled = true; };
  }, [setRecentThreads]);

  // Load message history when navigating to an existing thread
  useEffect(() => {
    if (!routeThreadId || initialMessage || !isAuthenticated) return;
    let cancelled = false;
    const loadHistory = async () => {
      try {
        const { getChatHistory } = await import('@api/chat');
        const data = await getChatHistory(routeThreadId, 100);
        if (cancelled) return;
        const rows = data?.messages || [];
        if (rows.length === 0) return;
        const mapped = rows.map((r, i) => ({
          id: `hist_${i}_${r.created_at || i}`,
          type: r.sender === 'user' ? 'user' : 'agent',
          content: r.content || '',
          timestamp: r.created_at || new Date().toISOString(),
          complete: true,
          isTyping: false,
          typingProgress: 1,
        }));
        replaceMessages(mapped);
      } catch (err) {
        if (err?.response?.status === 404) {
          setRecentThreads((prev) => prev.filter((t) => (t.thread_id || t.id || t) !== routeThreadId));
          navigate('/', { replace: true });
        }
      }
    };
    loadHistory();
    return () => { cancelled = true; };
  }, [initialMessage, isAuthenticated, navigate, replaceMessages, routeThreadId, setRecentThreads]);

  const lastUsedModel = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const candidate = messages[i];
      if (candidate?.type === 'agent' && candidate?.metadata?.selected_model) {
        return candidate.metadata.selected_model;
      }
    }
    return '';
  }, [messages]);

  useEffect(() => {
    let cancelled = false;

    const loadModels = async () => {
      try {
        const models = await getChatModels();
        if (cancelled) {
          return;
        }
        setAvailableModels(Array.isArray(models) ? models : []);
      } catch {
        if (!cancelled) {
          setAvailableModels([]);
        }
      }
    };

    loadModels();
    return () => {
      cancelled = true;
    };
  }, []);

  const visibleMessages = useMemo(() => {
    return messages.filter((message) => {
      if (message.type === 'agent') {
        return message.isTyping || message.complete || (message.content && message.content.trim());
      }
      return message.content && message.content.trim();
    });
  }, [messages]);

  const providerStatus = useMemo(() => {
    const latestAgentMessage = [...messages].reverse().find((candidate) => candidate?.type === 'agent');
    if (latestAgentMessage) {
      const meta = latestAgentMessage?.metadata || {};
      if (meta?.provider_unavailable) {
        return {
          unavailable: true,
          error: typeof meta?.provider_error === 'string' ? meta.provider_error : '',
        };
      }
    }
    return { unavailable: false, error: '' };
  }, [messages]);

  useEffect(() => {
    if (!showTracePanel || !traceSessions.length) {
      return;
    }

    const latestSession = activeOrLatestTraceSession;

    if (!latestSession) {
      return;
    }

    if (latestSession.status === 'running') {
      return;
    }

    const collapseTimer = window.setTimeout(() => {
      setTracePanelsExpanded((prev) => ({ ...prev, [latestSession.id]: false }));
    }, CHAT_UI_CONFIG.trace.autoCollapseDelayMs);

    return () => {
      window.clearTimeout(collapseTimer);
    };
  }, [activeOrLatestTraceSession, setTracePanelsExpanded, showTracePanel, traceSessions.length]);

  const handleSendMessageRef = useRef(null);
  const handleSendMessageStable = useCallback((...args) => handleSendMessageRef.current?.(...args), []);
  const { copyMessage, regenerateMessage } = useMessageActions({ messages, actions: { truncateAfter: (count) => replaceMessages(messages.slice(0, count)) }, handleSendMessageRef });

  const renderedMessages = useMemo(() => {
    return visibleMessages.map((message, idx) => {
      const isUser = message.type === 'user';
      const isLastMessage = idx === visibleMessages.length - 1;
      const modelLabel = message.metadata?.selected_model
        || message.metadata?.model
        || (isUser ? null : (lastUsedModel || 'Ассистент'));
      const agentName = message.metadata?.agent_name;
      const timeStr = new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      return (
        <Box
          key={message.id}
          display="flex"
          justifyContent={isUser ? 'flex-end' : 'flex-start'}
          w="100%"
        >
          <Box maxW={{ base: '96%', md: '80%', lg: '72%' }} w={isUser ? 'fit-content' : '100%'}>
            {!isUser && (
              <HStack spacing={2} mb={2} pl={1} align="center">
                <Text fontWeight="700" color="white">AI</Text>
                <Text fontSize="13px" fontWeight="650" color={CHAT_THEME.textPrimary} letterSpacing="-0.005em">
                  {modelLabel}
                </Text>
                {agentName && (
                  <Badge
                    px={2}
                    py={0.5}
                    borderRadius="full"
                    fontSize="10px"
                    fontWeight="600"
                    textTransform="none"
                    background="rgba(239,68,68,0.15)"
                    color="rgba(239,68,68,0.9)"
                    border="1px solid rgba(239,68,68,0.25)"
                  >
                    {agentName}
                  </Badge>
                )}
                <Text fontSize="11px" color={CHAT_THEME.textTertiary} fontWeight="500">
                  {timeStr}
                </Text>
              </HStack>
            )}

            <Box
              px={isUser ? { base: 4, md: 5 } : { base: 0, md: 1 }}
              py={isUser ? { base: 3, md: 3.5 } : 0}
              borderRadius={isUser ? '20px 20px 6px 20px' : 'none'}
              bg={isUser ? CHAT_THEME.userBubble : 'transparent'}
              border={isUser ? `1.5px solid ${CHAT_THEME.userBubbleBorder}` : 'none'}
              boxShadow={isUser ? '0 2px 12px rgba(239,68,68,0.08)' : 'none'}
              fontSize={{ base: '14px', md: '14.5px' }}
              lineHeight="1.72"
              color={CHAT_THEME.textPrimary}
              sx={isUser ? {} : PROSE_SX}
            >
              {isUser ? (
                <Text
                  color={colors.text.primary}
                  whiteSpace="pre-wrap"
                  fontWeight="500"
                  lineHeight="1.6"
                >
                  {message.content}
                </Text>
              ) : (
                <>
                  <MessageRenderer
                    content={message.content}
                    isTyping={message.isTyping}
                    typingProgress={message.typingProgress}
                    messageType={message.type}
                  />
                  {message.metadata?.pptx_b64 && (
                    <Button
                      mt={3}
                      size="sm"
                      colorScheme="red"
                      variant="solid"
                      onClick={() => {
                        const bytes = Uint8Array.from(atob(message.metadata.pptx_b64), (c) => c.charCodeAt(0));
                        const blob = new Blob([bytes], { type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = message.metadata.filename || 'presentation.pptx';
                        a.click();
                        URL.revokeObjectURL(url);
                      }}
                    >
                      📥 Скачать презентацию (.pptx)
                    </Button>
                  )}
                </>
              )}
            </Box>

            {isUser && (
              <Text color={CHAT_THEME.textTertiary} fontSize="11px" mt={1.5} pr={1} textAlign="right" fontWeight="500">
                {timeStr}
              </Text>
            )}
            {!isUser && message.isTyping && !message.content && (
              <HStack spacing="5px" mt={1} pl={1}>
                {[0, 1, 2].map((i) => (
                  <Box
                    key={i}
                    w="7px"
                    h="7px"
                    borderRadius="full"
                    bg="rgba(239,68,68,0.7)"
                    sx={{
                      animation: `${dotPulse} 1.4s ease-in-out infinite`,
                      animationDelay: `${i * 0.18}s`,
                    }}
                  />
                ))}
              </HStack>
            )}
            {!isUser && !message.isTyping && message.content && (
              <HStack spacing={1} mt={2} pl={1}>
                <Box position="relative" display="inline-flex" alignItems="center" role="group">
                  <IconButton
                    aria-label="Скопировать ответ"
                    icon={<FiCopy />}
                    size="xs"
                    variant="ghost"
                    color={CHAT_THEME.textSecondary}
                    borderRadius="8px"
                    _hover={{ bg: CHAT_THEME.panelHover, color: CHAT_THEME.textPrimary }}
                    onClick={() => copyMessage(message.content)}
                  />
                  <Text
                    position="absolute"
                    left="calc(100% + 8px)"
                    top="50%"
                    transform="translateY(-50%)"
                    opacity={0}
                    _groupHover={{ opacity: 1 }}
                    pointerEvents="none"
                    transition="none"
                    fontSize="11px"
                    color={CHAT_THEME.textPrimary}
                    fontWeight="600"
                    bg="rgba(8,8,8,0.96)"
                    border="1px solid rgba(255,255,255,0.14)"
                    borderRadius="8px"
                    px={2}
                    py={1}
                    zIndex={2}
                    whiteSpace="nowrap"
                  >
                    Копировать
                  </Text>
                </Box>
                {isLastMessage && (
                  <Box position="relative" display="inline-flex" alignItems="center" role="group">
                    <IconButton
                      aria-label="Перегенерировать ответ"
                      icon={<FiRotateCcw />}
                      size="xs"
                      variant="ghost"
                      color={CHAT_THEME.textSecondary}
                      borderRadius="8px"
                      _hover={{ bg: CHAT_THEME.panelHover, color: CHAT_THEME.textPrimary }}
                      onClick={() => regenerateMessage(message.id)}
                      isDisabled={isLoading}
                    />
                    <Text
                      position="absolute"
                      left="calc(100% + 8px)"
                      top="50%"
                      transform="translateY(-50%)"
                      opacity={0}
                      _groupHover={{ opacity: 1 }}
                      pointerEvents="none"
                      transition="none"
                      fontSize="11px"
                      color={CHAT_THEME.textPrimary}
                      fontWeight="600"
                      bg="rgba(8,8,8,0.96)"
                      border="1px solid rgba(255,255,255,0.14)"
                      borderRadius="8px"
                      px={2}
                      py={1}
                      zIndex={2}
                      whiteSpace="nowrap"
                    >
                      Перегенерировать
                    </Text>
                  </Box>
                )}
              </HStack>
            )}
          </Box>
        </Box>
      );
    });
  }, [visibleMessages, lastUsedModel, copyMessage, regenerateMessage, isLoading]);

  const sendViaRest = useCallback(async (message, modelForRequest, inputTypeForRequest, options = {}) => {
    appendTraceEvent({
      kind: 'info',
      title: 'Используется HTTP fallback',
      detail: 'WebSocket недоступен, запрос отправлен через REST API',
    }, options.traceSessionId);

    if (!isAuthenticated) {
      incrementRequests();
    }

    if (!options.skipUserAppend) {
      const userMessage = {
        id: options.userMessageId || `user_${Date.now()}_${Math.random()}`,
        type: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      };
      addMessage(userMessage);
    }

    const response = await sendChatMessage(
      threadId,
      message,
      resolveSessionUserId() || null,
      modelForRequest,
      inputTypeForRequest,
      options,
    );
    if (response?.reply) {
      const responseMeta = response?.metadata || {};
      const selectedModel = responseMeta?.selected_model || responseMeta?.model_routing?.selected_model || '';
      if (selectedModel) {
        appendTraceEvent({
          kind: 'done',
          title: `Выбрана модель: ${selectedModel}`,
          detail: responseMeta?.model_routing?.reason || '',
        }, options.traceSessionId);
      }

      if (responseMeta?.fallback_tool_path === 'web_search' || options.webSearch) {
        appendTraceEvent({
          kind: 'done',
          title: 'Вызван инструмент: Поиск в сети',
          detail: 'Собраны внешние источники и добавлены в контекст ответа',
        }, options.traceSessionId);
      }

      if (options.deepResearch) {
        appendTraceEvent({
          kind: 'done',
          title: 'Активирован режим Deep Research',
          detail: 'Использован углубленный сценарий исследования',
        }, options.traceSessionId);
      }

      if (options.fileContext) {
        appendTraceEvent({
          kind: 'done',
          title: 'Контекст из файла применен',
          detail: 'Фрагменты документа использованы при генерации ответа',
        }, options.traceSessionId);
      }

      appendTraceEvent({
        kind: responseMeta?.provider_unavailable ? 'error' : 'done',
        title: responseMeta?.provider_unavailable ? 'Ответ возвращен в деградированном режиме' : 'Ответ сгенерирован',
        detail: responseMeta?.provider_error || '',
      }, options.traceSessionId);

      const agentMessage = {
        id: `agent_${Date.now()}_${Math.random()}`,
        type: 'agent',
        content: response.reply,
        timestamp: new Date().toISOString(),
        metadata: response.metadata,
        file_url: response.file_url,
        complete: true,
        isTyping: false,
        typingProgress: 1,
      };
      addMessage(agentMessage);
      finalizeTraceSession(responseMeta?.provider_unavailable ? 'error' : 'done', options.traceSessionId);
    } else {
      appendTraceEvent({
        kind: 'error',
        title: 'Пустой ответ от REST API',
        detail: 'Ответ не содержит текста',
      }, options.traceSessionId);
      finalizeTraceSession('error', options.traceSessionId);
    }
    setIsLoading(false);
  }, [addMessage, appendTraceEvent, finalizeTraceSession, incrementRequests, isAuthenticated, resolveSessionUserId, setIsLoading, threadId]);

  const handleSendMessage = useCallback(async (message, sendOptions = {}) => {
    const skipUserAppend = !!sendOptions.skipUserAppend;
    const anchorMessageId = sendOptions.anchorMessageId || (!skipUserAppend ? `user_${Date.now()}_${Math.random()}` : null);
    const trimmed = typeof message === 'string' ? message.trim() : '';
    if (!trimmed) {
      return;
    }

    if (trimmed.length > 10000) {
      sideEffects.notify({
        title: 'Сообщение слишком длинное',
        description: 'Максимум 10000 символов.',
        status: 'warning',
        duration: 2500,
      });
      return;
    }

    composerRef.current?.clearInput();
    setSidebarSearch('');

    // Reset WS dedupe state for each new user request.
    activeWsJobIdRef.current = '';
    lastWsReplyFingerprintRef.current = '';

    const modelForRequest = selectedModelOverride || initialManualModel || null;
    const attachedInputType = attachedFile?.file_type === 'audio'
      ? 'audio'
      : attachedFile?.file_type === 'image'
        ? 'image'
        : null;
    const inputTypeForRequest = attachedInputType || initialInputType || 'text';
    const routeOverrideForRequest = attachedFile?.file_type === 'audio' ? 'audio_transcribe' : null;

    if (!ensureGuestLimit()) {
      return;
    }

    setIsLoading(true);
    clearError();
    upsertRecentThread(threadId, trimmed);
    const traceSessionId = startTraceSession(trimmed, anchorMessageId);
    appendTraceEvent({
      kind: 'info',
      title: 'Запрос принят',
      detail: clampTraceDetail(trimmed, 140),
    }, traceSessionId);

    if (webSearchEnabled) {
      appendTraceEvent({
        kind: 'info',
        title: 'Включен веб-поиск',
        detail: 'При необходимости будут вызваны внешние источники',
      }, traceSessionId);
    }

    if (deepResearchEnabled) {
      appendTraceEvent({
        kind: 'info',
        title: 'Включен режим Deep Research',
        detail: 'Маршрутизатор может выбрать исследовательский пайплайн',
      }, traceSessionId);
    }

    // Auto-parse URLs found in the message text
    let urlContext = attachedFile?.extracted_text || initialFileContext || '';
    try {
      const foundUrls = extractUrlCandidates(trimmed, 2);
      if (foundUrls.length > 0) {
        sideEffects.notify({ title: foundUrls.length > 1 ? 'Читаю ссылки…' : 'Читаю ссылку…', status: 'info', duration: 2000, isClosable: true });
        const { parseUrl: apiParseUrl } = await import('@api/chat');
        const results = await Promise.allSettled(foundUrls.map((u) => apiParseUrl(u)));
        const parsedBlocks = [];
        results.forEach((r, i) => {
          const url = foundUrls[i];
          if (r.status === 'fulfilled' && r.value?.content) {
            const title = r.value.title || url;
            parsedBlocks.push(`## Страница: ${title}\nURL: ${url}\n\n${String(r.value.content).slice(0, 8000)}`);
          } else {
            const err = r.status === 'rejected' ? (r.reason?.message || 'недоступно') : (r.value?.error || 'пустой ответ');
            parsedBlocks.push(`## Страница: ${url}\n[не удалось прочитать: ${err}]`);
          }
        });
        const parsed = parsedBlocks.length ? `# __URL_CONTEXT__\n${parsedBlocks.join('\n\n---\n\n')}` : '';
        const okCount = results.filter((r) => r.status === 'fulfilled' && r.value?.content).length;
        if (parsed) {
          urlContext = urlContext ? `${urlContext}\n\n${parsed}` : parsed;
          appendTraceEvent({
            kind: okCount > 0 ? 'done' : 'error',
            title: okCount > 0 ? 'Ссылки проанализированы' : 'Ссылки недоступны',
            detail: `Обработано URL: ${okCount}/${foundUrls.length} (${foundUrls.join(', ')})`,
          }, traceSessionId);
          if (okCount > 0) {
            sideEffects.notify({ title: okCount > 1 ? 'Ссылки прочитаны' : 'Ссылка прочитана', status: 'success', duration: 2000 });
          } else {
            sideEffects.notify({ title: 'Не удалось прочитать ссылку', status: 'warning', duration: 2500 });
          }
        }
      }
    } catch (err) {
      appendTraceEvent({
        kind: 'error',
        title: 'Ошибка парсинга ссылки',
        detail: err?.message || String(err),
      }, traceSessionId);
    }

    try {
      if (useWebSocket || connectionState === 'connecting' || connectionState === 'connected') {
        if (!skipUserAppend) {
          const userMessage = {
            id: anchorMessageId,
            type: 'user',
            content: trimmed,
            timestamp: new Date().toISOString(),
          };
          addMessage(userMessage);
        }
        const wsOptions = {
          ...(webSearchEnabled && { webSearch: true }),
          ...(deepResearchEnabled && { deepResearch: true }),
          ...(urlContext && { fileContext: urlContext.substring(0, 6000) }),
          ...(routeOverrideForRequest && { routeOverride: routeOverrideForRequest }),
        };
        wsSendMessage(trimmed, modelForRequest, inputTypeForRequest, wsOptions);
        setAttachedFile(null);
      } else {
        await sendViaRest(trimmed, modelForRequest, inputTypeForRequest, {
          webSearch: webSearchEnabled,
          deepResearch: deepResearchEnabled,
          fileContext: urlContext ? urlContext.substring(0, 6000) : '',
          routeOverride: routeOverrideForRequest,
          skipUserAppend,
          userMessageId: anchorMessageId,
          traceSessionId,
        });
      }
    } catch (sendError) {
      if (sendError?.status === 429) {
        showAuthModal(
          'Превышен лимит запросов',
          'Бесплатные запросы закончились. Войдите, чтобы продолжить.',
          'request_limit'
        );
      } else {
        setError('Не удалось отправить сообщение. Попробуйте еще раз.');
      }
      appendTraceEvent({
        kind: 'error',
        title: 'Отправка не удалась',
        detail: sendError?.message || 'Неизвестная ошибка отправки',
      }, traceSessionId);
      finalizeTraceSession('error', traceSessionId);
      setIsLoading(false);
    }
  }, [addMessage, appendTraceEvent, attachedFile, clearError, connectionState, deepResearchEnabled, ensureGuestLimit, finalizeTraceSession, initialFileContext, initialInputType, initialManualModel, selectedModelOverride, sendViaRest, setAttachedFile, setError, setIsLoading, setSidebarSearch, showAuthModal, startTraceSession, threadId, sideEffects, upsertRecentThread, useWebSocket, webSearchEnabled, wsSendMessage]);

  useEffect(() => {
    handleSendMessageRef.current = handleSendMessage;
  }, [handleSendMessage]);

  useEffect(() => {
    if (!initialMessage || !threadId || hasInitialized || connectionState === 'connecting') {
      return;
    }

    handleSendMessage(initialMessage);
    sideEffects.goToThread(threadId, { replace: true });
    setHasInitialized(true);
  }, [
    connectionState,
    handleSendMessage,
    hasInitialized,
    initialManualModel,
    initialMessage,
    navigate,
    sideEffects,
    threadId,
  ]);

  const startNewChat = useCallback(() => {
    clearMessages();
    composerRef.current?.clearInput();
    setSidebarSearch('');
    setAttachedFile(null);
    clearError();
    resetTraceSessions();
    setTracePanelsExpanded({});
    navigate('/');
  }, [clearError, clearMessages, navigate, resetTraceSessions, setAttachedFile, setSidebarSearch, setTracePanelsExpanded]);

  const openMemoryPanel = useCallback(async () => {
    if (!isAuthenticated) {
      showAuthModal(
        'Память доступна после входа',
        'Войдите в аккаунт, чтобы увидеть и управлять долговременной памятью.',
        'memory_requires_auth'
      );
      return;
    }
    memoryDisclosure.onOpen();
    try {
      const { getUserMemory } = await import('@api/chat');
      let effectiveUserId = resolveSessionUserId();
      if (!effectiveUserId) {
        const { fetchProfile } = await import('@api/profile');
        const profile = await fetchProfile();
        effectiveUserId = profile?.id ? String(profile.id) : '';
        if (effectiveUserId && typeof window !== 'undefined') {
          window.sessionStorage.setItem('user_id', effectiveUserId);
        }
      }
      if (!effectiveUserId) {
        throw new Error('user_id is missing in session');
      }
      const data = await getUserMemory(effectiveUserId);
      const facts = data.facts || [];
      setMemoryFacts(facts);
      setProfileMemoryCount(Array.isArray(facts) ? facts.length : 0);
    } catch (e) {
      console.warn('Failed to load memory:', e);
      sideEffects.notify({
        title: 'Не удалось загрузить факты памяти',
        description: 'Проверьте, что сессия активна, и повторите попытку.',
        status: 'warning',
        duration: 2500,
      });
    }
  }, [isAuthenticated, memoryDisclosure, resolveSessionUserId, setMemoryFacts, setProfileMemoryCount, showAuthModal, sideEffects]);

  const resetUiSettings = useCallback(() => {
    resetPersistedUiSettings();
    sideEffects.notify({
      title: 'Настройки сброшены',
      status: 'success',
      duration: 1600,
    });
  }, [resetPersistedUiSettings, sideEffects]);

  const handleFileUpload = useCallback(async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const { uploadFileForChat } = await import('@api/chat');
      const result = await uploadFileForChat(file);
      setAttachedFile(result);
      if (result.file_type === 'image' && result.vlm_description) {
        appendTraceEvent({ kind: 'done', title: 'Проанализировано фото (MWS Vision)', detail: clampTraceDetail(result.vlm_description) });
      } else if (result.file_type === 'audio') {
        appendTraceEvent({ kind: 'done', title: 'Аудио прикреплено', detail: 'Файл будет отправлен модели как вложение' });
      } else {
        appendTraceEvent({ kind: 'done', title: `Файл подготовлен: ${result.filename}`, detail: `Тип: ${result.file_type || 'unknown'}` });
      }
      sideEffects.notify({
        title: `Файл: ${result.filename}`,
        description: result.file_type === 'image' ? 'Изображение готово для анализа' : result.file_type === 'audio' ? 'Аудио прикреплено к сообщению' : `Извлечено ${(result.extracted_text || '').length} символов`,
        status: 'success', duration: 3000,
      });
    } catch (err) {
      sideEffects.notify({ title: 'Ошибка загрузки', description: String(err), status: 'error', duration: 4000 });
    }
    e.target.value = '';
  }, [appendTraceEvent, setAttachedFile, sideEffects]);

  const handleVoiceToggle = useCallback(async () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
      return;
    }
    try {
      const isSecure = window.isSecureContext || window.location.protocol === 'https:' || window.location.hostname === 'localhost';
      if (!isSecure || !navigator.mediaDevices) {
        sideEffects.notify({ title: 'Микрофон недоступен', description: 'Требуется HTTPS-соединение.', status: 'warning', duration: 4000 });
        return;
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      const chunks = [];
      mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunks, { type: 'audio/webm' });
        const file = new File([blob], 'voice.webm', { type: 'audio/webm' });
        try {
          const { uploadFileForChat } = await import('@api/chat');
          const result = await uploadFileForChat(file);
          setAttachedFile(result);
          appendTraceEvent({ kind: 'done', title: 'Аудио прикреплено', detail: 'Файл будет отправлен модели как вложение' });
          sideEffects.notify({ title: 'Аудио прикреплено', description: 'Нажмите отправить', status: 'success', duration: 2000 });
        } catch {
          sideEffects.notify({ title: 'Ошибка распознавания', status: 'error', duration: 3000 });
        }
      };
      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
      sideEffects.notify({ title: 'Запись...', description: 'Нажмите для остановки', status: 'info', duration: 2000 });
    } catch {
      sideEffects.notify({ title: 'Микрофон недоступен', status: 'error', duration: 3000 });
    }
  }, [appendTraceEvent, isRecording, setAttachedFile, sideEffects]);

  const onToggleWebSearch = useCallback(() => setChatUiSettings((p) => ({ ...p, webSearchEnabled: !p.webSearchEnabled })), [setChatUiSettings]);
  const onToggleDeepResearch = useCallback(() => setChatUiSettings((p) => ({ ...p, deepResearchEnabled: !p.deepResearchEnabled })), [setChatUiSettings]);

  const composerModelLabel = lastUsedModel || selectedModelOverride || '';

  return (
    <ChatPageLayout>
      {/* Animated aurora background */}
      <Box position="absolute" inset={0} pointerEvents="none" zIndex={0} overflow="hidden">
        <Box
          position="absolute"
          top="-25%"
          right="-18%"
          w="60%"
          h="60%"
          background="radial-gradient(circle, rgba(239,68,68,0.09) 0%, rgba(239,68,68,0.025) 45%, transparent 72%)"
          filter="blur(90px)"
          sx={{ animation: `${bgAuroraA} 22s ease-in-out infinite` }}
        />
        <Box
          position="absolute"
          bottom="-22%"
          left="-12%"
          w="55%"
          h="55%"
          background="radial-gradient(circle, rgba(220,38,38,0.07) 0%, rgba(220,38,38,0.02) 45%, transparent 72%)"
          filter="blur(100px)"
          sx={{ animation: `${bgAuroraB} 26s ease-in-out infinite` }}
        />
        <Box
          position="absolute"
          top="30%"
          left="35%"
          w="40%"
          h="40%"
          background="radial-gradient(circle, rgba(248,113,113,0.045) 0%, transparent 70%)"
          filter="blur(110px)"
          sx={{ animation: `${bgAuroraC} 30s ease-in-out infinite` }}
        />
        <Box
          position="absolute"
          inset={0}
          backgroundImage="linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)"
          backgroundSize="48px 48px"
          opacity={0.25}
        />
        <Box
          position="absolute"
          inset={0}
          bg="rgba(0,0,0,0.25)"
        />
      </Box>
      <Flex h="100%" overflow="hidden" position="relative" zIndex={1}>
        <ChatSidebarPanel
          isSidebarCollapsed={isSidebarCollapsed}
          filteredRecentThreads={filteredRecentThreads}
          threadId={threadId}
          sidebarSearch={sidebarSearch}
          setSidebarSearch={setSidebarSearch}
          deletingThreadId={deletingThreadId}
          handleDeleteThread={handleDeleteThread}
          onNavigateThread={sideEffects.goToThread}
          onNewChat={startNewChat}
          onOpenMemory={openMemoryPanel}
          onOpenSettings={settingsDisclosure.onOpen}
        />

        <VStack flex="1" align="stretch" spacing={0} minH="0" overflow="hidden">
          {/* Header */}
          <Flex
            as="header"
            align="center"
            justify="space-between"
            px={{ base: 3, md: 5 }}
            h="56px"
            flexShrink={0}
            borderBottom={`1px solid ${CHAT_THEME.panelBorder}`}
            bg={CHAT_THEME.headerBg}
            backdropFilter="blur(16px)"
          >
            {/* Left: sidebar toggle */}
            <HStack spacing={1} w={{ base: 'auto', md: '160px' }}>
              <IconButton
                aria-label="Меню"
                icon={<FiMenu />}
                display={{ base: 'inline-flex', lg: 'none' }}
                onClick={sidebarDisclosure.onOpen}
                variant="ghost"
                size="sm"
                color={CHAT_THEME.textSecondary}
                _hover={{ bg: CHAT_THEME.panelHover, color: CHAT_THEME.textPrimary }}
                borderRadius="10px"
              />
              <IconButton
                aria-label="Переключить сайдбар"
                icon={<FiMenu />}
                display={{ base: 'none', lg: 'inline-flex' }}
                onClick={() => setIsSidebarCollapsed((prev) => !prev)}
                variant="ghost"
                size="sm"
                color={CHAT_THEME.textSecondary}
                _hover={{ bg: CHAT_THEME.panelHover, color: CHAT_THEME.textPrimary }}
                borderRadius="10px"
              />
            </HStack>

            {/* Center: auto + manual model select */}
            <HStack spacing={2} flex="1" justify="center">
              <ModelSelector
                selectedModel={selectedModelOverride}
                availableModels={availableModels}
                onChange={setSelectedModelOverride}
              />
            </HStack>

            {/* Right: settings */}
            <HStack w={{ base: 'auto', md: '160px' }} justify="flex-end" spacing={2}>
              <IconButton
                aria-label="Настройки чата"
                icon={<FiSettings />}
                variant="ghost"
                size="sm"
                color={CHAT_THEME.textSecondary}
                _hover={{ bg: CHAT_THEME.panelHover, color: CHAT_THEME.textPrimary }}
                borderRadius="10px"
                onClick={settingsDisclosure.onOpen}
              />
            </HStack>
          </Flex>

          <Box ref={messagesScrollRef} flex="1" minH="0" overflowY="auto" px={{ base: 3, md: 6, lg: 8 }} pt={{ base: 5, md: 8 }} pb={{ base: 6, md: 8 }} sx={CHAT_SCROLLBAR_SX}>
            {error && (
              <Box display="flex" alignItems="center" gap={2.5} px={4} py={3} mb={4} borderRadius="12px"
                bg="rgba(239,68,68,0.08)" border="1px solid rgba(239,68,68,0.3)"
                backdropFilter="blur(8px)">
                <Icon as={FiAlertCircle} color="#f87171" boxSize="15px" flexShrink={0} />
                <Text fontSize="13px" color="rgba(255,255,255,0.85)" fontWeight="500" lineHeight="1.45">{error}</Text>
              </Box>
            )}

            {providerStatus.unavailable && (
              <Box display="flex" alignItems="center" gap={2.5} px={4} py={3} mb={4} borderRadius="12px"
                bg="rgba(251,191,36,0.07)" border="1px solid rgba(251,191,36,0.28)"
                backdropFilter="blur(8px)">
                <Icon as={FiAlertTriangle} color="#fbbf24" boxSize="15px" flexShrink={0} />
                <Text fontSize="13px" color="rgba(255,255,255,0.85)" fontWeight="500" lineHeight="1.45">
                  Сервис моделей сейчас недоступен. Проверьте API-ключ и доступ к провайдеру.
                  {providerStatus.error ? ` Детали: ${providerStatus.error}` : ''}
                </Text>
              </Box>
            )}

            {connectionState === 'connecting' && (
              <Box display="flex" alignItems="center" gap={2.5} px={4} py={3} mb={4} borderRadius="12px"
                bg="rgba(96,165,250,0.07)" border="1px solid rgba(96,165,250,0.25)"
                backdropFilter="blur(8px)">
                <Icon as={FiInfo} color="#60a5fa" boxSize="15px" flexShrink={0} />
                <Text fontSize="13px" color="rgba(255,255,255,0.85)" fontWeight="500" lineHeight="1.45">Подключаемся к каналу сообщений...</Text>
              </Box>
            )}

            {visibleMessages.length === 0 ? (
              <Center minH="60vh">
                <VStack spacing={3} align="center" maxW="420px" textAlign="center">
                  <Box mb={1}>
                    <Text fontWeight="700" color="white">AI Assistant</Text>
                  </Box>
                  <Text color={CHAT_THEME.textSecondary} fontSize="14px" lineHeight="1.6">
                    Задайте вопрос, прикрепите файл или включите веб-поиск — и начнём.
                  </Text>
                </VStack>
              </Center>
            ) : (
              <VStack spacing={6} align="stretch" w="100%" maxW="860px" mx="auto">
                {visibleMessages.map((message, idx) => (
                  <React.Fragment key={`msg_block_${message.id}`}>
                    {renderedMessages[idx]}
                    {showTracePanel && message.type === 'user' && traceSessionByAnchor.get(message.id)
                      ? (
                        <Suspense fallback={<Box h="24px" />}>
                          <TracePanel
                            sessions={[traceSessionByAnchor.get(message.id)]}
                            expandedMap={tracePanelsExpanded}
                            isCompactTrace={isCompactTrace}
                            onToggleExpanded={(id, expanded) => setTracePanelsExpanded((prev) => ({ ...prev, [id]: expanded }))}
                          />
                        </Suspense>
                      )
                      : null}
                  </React.Fragment>
                ))}

                {currentJob?.status === 'processing' && (
                  <HStack spacing={3} color={colors.text.tertiary}>
                    <Spinner size="sm" />
                    <Text fontSize="sm">Агент обрабатывает задачу...</Text>
                    <Button size="xs" variant="ghost" onClick={() => handleCancelJob(currentJob?.id)}>
                      Отменить
                    </Button>
                  </HStack>
                )}
                <Box ref={messagesEndRef} />
              </VStack>
            )}
          </Box>

          <ChatComposerPanel
            ref={composerRef}
            onSubmit={handleSendMessageStable}
            disabled={isLoading}
            webSearchEnabled={webSearchEnabled}
            deepResearchEnabled={deepResearchEnabled}
            onToggleWebSearch={onToggleWebSearch}
            onToggleDeepResearch={onToggleDeepResearch}
            modelLabel={composerModelLabel}
            isAuthenticated={isAuthenticated}
            remainingRequests={remainingRequests}
            attachedFile={attachedFile}
            onClearAttachment={() => setAttachedFile(null)}
            onFileUpload={handleFileUpload}
            onVoiceToggle={handleVoiceToggle}
            isRecording={isRecording}
            fileInputRef={fileInputRef}
          />
        </VStack>
      </Flex>

      <Drawer isOpen={sidebarDisclosure.isOpen} placement="left" onClose={sidebarDisclosure.onClose}>
        <DrawerOverlay />
        <DrawerContent bg={CHAT_THEME.sidebarBg} borderRight={`1px solid ${CHAT_THEME.panelBorder}`} p={0}>
          <DrawerCloseButton mt={2} zIndex={2} />
          <DrawerBody p={0} h="full">
            <ChatSidebarPanel
              isSidebarCollapsed={false}
              filteredRecentThreads={filteredRecentThreads}
              threadId={threadId}
              sidebarSearch={sidebarSearch}
              setSidebarSearch={setSidebarSearch}
              deletingThreadId={deletingThreadId}
              handleDeleteThread={handleDeleteThread}
              onNavigateThread={(tid) => { sideEffects.goToThread(tid); sidebarDisclosure.onClose(); }}
              onNewChat={() => { startNewChat(); sidebarDisclosure.onClose(); }}
              onOpenMemory={openMemoryPanel}
              onOpenSettings={settingsDisclosure.onOpen}
            />
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      <AuthModal isOpen={isAuthModalOpen} onClose={onAuthModalClose} {...modalData} />

      {/* Memory Drawer */}
      <Drawer isOpen={memoryDisclosure.isOpen} placement="right" onClose={memoryDisclosure.onClose} size="md">
        <DrawerOverlay />
        <DrawerContent bg={CHAT_THEME.sidebarBg} borderLeft={`1px solid ${CHAT_THEME.panelBorder}`}>
          <DrawerCloseButton mt={2} />
          <DrawerHeader borderBottomWidth="1px" borderColor="rgba(255,255,255,0.08)">
            🧠 Долговременная память
          </DrawerHeader>
          <DrawerBody pt={4} sx={CHAT_SCROLLBAR_SX}>
            <Text fontSize="xs" color={colors.text.tertiary} mb={3}>
              Здесь сохраняются устойчивые факты: предпочтения, контекст проектов и важные договоренности.
            </Text>
            {memoryFacts.length === 0 ? (
              <VStack spacing={3} py={8}>
                <Text color={colors.text.tertiary} textAlign="center">
                  Память пуста. Факты будут автоматически извлекаться из ваших разговоров.
                </Text>
              </VStack>
            ) : (
              <VStack spacing={3} align="stretch">
                <Text fontSize="xs" color={colors.text.tertiary}>
                  {memoryFacts.length} фактов сохранено
                </Text>
                {memoryFacts.map((fact) => (
                  <Box
                    key={fact.id}
                    p={3}
                    borderRadius="lg"
                    bg="rgba(255,255,255,0.06)"
                    border="1px solid rgba(255,255,255,0.1)"
                  >
                    <HStack justify="space-between" mb={1}>
                      <Text fontSize="xs" color="red.300" fontWeight="600" textTransform="uppercase">
                        {fact.fact_type}
                      </Text>
                      <Text fontSize="xs" color={colors.text.tertiary}>
                        {fact.confidence ? `${Math.round(fact.confidence * 100)}%` : ''}
                      </Text>
                    </HStack>
                    <Text fontSize="sm" fontWeight="500" color={colors.text.primary}>
                      {fact.fact_key}
                    </Text>
                    <Text fontSize="sm" color={colors.text.secondary} mt={1}>
                      {fact.fact_value}
                    </Text>
                    <Text fontSize="xs" color={colors.text.tertiary} mt={1}>
                      {fact.updated_at ? new Date(fact.updated_at).toLocaleDateString('ru') : ''}
                    </Text>
                  </Box>
                ))}
              </VStack>
            )}
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      <Drawer
        isOpen={settingsDisclosure.isOpen}
        placement="right"
        onClose={settingsDisclosure.onClose}
        size="md"
        motionPreset="none"
        blockScrollOnMount={false}
        autoFocus={false}
        trapFocus={false}
        useInert={false}
        returnFocusOnClose={false}
        isLazy
        lazyBehavior="keepMounted"
        preserveScrollBarGap
      >
        <DrawerOverlay bg="rgba(0,0,0,0.6)" backdropFilter="blur(8px)" />
        <DrawerContent
          bg={CHAT_THEME.sidebarBg}
          borderLeft={`1px solid ${CHAT_THEME.panelBorder}`}
          boxShadow="-20px 0 60px rgba(0,0,0,0.55)"
          sx={{
            willChange: 'transform, opacity',
            transform: 'translateZ(0)',
            backgroundImage:
              'radial-gradient(circle at 85% -10%, rgba(239,68,68,0.12), transparent 55%), radial-gradient(circle at 15% 110%, rgba(220,38,38,0.08), transparent 50%)',
          }}
        >
          <DrawerCloseButton
            mt={3}
            mr={2}
            borderRadius="10px"
            color={CHAT_THEME.textSecondary}
            _hover={{ bg: CHAT_THEME.panelHover, color: CHAT_THEME.textPrimary }}
          />
          <DrawerHeader borderBottomWidth="1px" borderColor="rgba(255,255,255,0.08)" py={5}>
            <HStack spacing={3} align="center" pr={10}>
              <Box
                w="38px"
                h="38px"
                borderRadius="12px"
                display="flex"
                alignItems="center"
                justifyContent="center"
                bg={CHAT_THEME.accentSoft}
                border="1px solid rgba(239,68,68,0.3)"
                flexShrink={0}
              >
                <Icon as={FiSettings} boxSize={6} color="#fca5a5" />
              </Box>
              <VStack align="start" spacing={0.5}>
                <Text fontWeight="700" letterSpacing="-0.01em" fontSize="17px" color={CHAT_THEME.textPrimary}>
                  Настройки
                </Text>
                <Text fontSize="11.5px" color={CHAT_THEME.textSecondary} fontWeight="500" lineHeight="1.35">
                  Поведение интерфейса и инструменты по умолчанию
                </Text>
              </VStack>
            </HStack>
          </DrawerHeader>
          <DrawerBody px={5} py={5} sx={CHAT_SCROLLBAR_SX}>
            <VStack align="stretch" spacing={5}>
              {/* Interface section */}
              <VStack align="stretch" spacing={2.5}>
                <HStack spacing={2} px={1}>
                  <Icon as={FiEye} boxSize={3.5} color={CHAT_THEME.textTertiary} />
                  <Text fontSize="10.5px" fontWeight="700" color={CHAT_THEME.textTertiary} textTransform="uppercase" letterSpacing="0.09em">
                    Интерфейс
                  </Text>
                </HStack>
                <Box
                  borderRadius="14px"
                  bg="rgba(255,255,255,0.025)"
                  border={`1px solid ${CHAT_THEME.panelBorder}`}
                  overflow="hidden"
                >
                  {[
                    {
                      key: 'trace',
                      icon: FiLayers,
                      title: 'Пошаговый режим',
                      desc: 'Показывать этапы подготовки ответа',
                      checked: showTracePanel,
                      onChange: () => setChatUiSettings((p) => ({ ...p, showTracePanel: !p.showTracePanel })),
                    },
                  ].map((row, i, arr) => (
                    <HStack
                      key={row.key}
                      justify="space-between"
                      px={4}
                      py={3.5}
                      spacing={3}
                      borderBottom={i < arr.length - 1 ? `1px solid ${CHAT_THEME.panelBorder}` : 'none'}
                      transition="background 0.15s"
                      _hover={{ bg: 'rgba(255,255,255,0.02)' }}
                    >
                      <HStack spacing={3} align="center" flex="1" minW="0">
                        <Box
                          w="32px"
                          h="32px"
                          borderRadius="9px"
                          display="flex"
                          alignItems="center"
                          justifyContent="center"
                          bg={row.checked ? CHAT_THEME.accentSoft : 'rgba(255,255,255,0.04)'}
                          border={`1px solid ${row.checked ? 'rgba(239,68,68,0.28)' : CHAT_THEME.panelBorder}`}
                          flexShrink={0}
                          transition="all 0.2s"
                        >
                          <Icon as={row.icon} boxSize={3.5} color={row.checked ? '#fca5a5' : CHAT_THEME.textTertiary} />
                        </Box>
                        <VStack align="start" spacing={0} minW="0">
                          <Text fontSize="13px" fontWeight="600" color={CHAT_THEME.textPrimary} letterSpacing="-0.005em">
                            {row.title}
                          </Text>
                          <Text fontSize="11.5px" fontWeight="500" color={CHAT_THEME.textSecondary} noOfLines={1}>
                            {row.desc}
                          </Text>
                        </VStack>
                      </HStack>
                      <Switch
                        isChecked={row.checked}
                        onChange={row.onChange}
                        size="md"
                        sx={{
                          '& .chakra-switch__track[data-checked]': {
                            background: '#ef4444',
                          },
                          '& .chakra-switch__track:not([data-checked])': {
                            background: 'rgba(255,255,255,0.12)',
                          },
                          '& .chakra-switch__track:focus, & .chakra-switch__track[data-focus]': {
                            boxShadow: '0 0 0 3px rgba(239,68,68,0.35)',
                          },
                        }}
                      />
                    </HStack>
                  ))}
                </Box>
              </VStack>

              {/* Tools section */}
              <VStack align="stretch" spacing={2.5}>
                <HStack spacing={2} px={1}>
                  <Icon as={FiZap} boxSize={3.5} color={CHAT_THEME.textTertiary} />
                  <Text fontSize="10.5px" fontWeight="700" color={CHAT_THEME.textTertiary} textTransform="uppercase" letterSpacing="0.09em">
                    Инструменты по умолчанию
                  </Text>
                </HStack>
                <Box
                  borderRadius="14px"
                  bg="rgba(255,255,255,0.025)"
                  border={`1px solid ${CHAT_THEME.panelBorder}`}
                  overflow="hidden"
                >
                  {[
                    {
                      key: 'web',
                      icon: FiSearch,
                      title: 'Веб-поиск',
                      desc: 'Подмешивать внешние источники в ответ',
                      checked: webSearchEnabled,
                      onChange: () => setChatUiSettings((p) => ({ ...p, webSearchEnabled: !p.webSearchEnabled })),
                    },
                    {
                      key: 'deep',
                      icon: FiLayers,
                      title: 'Deep Research',
                      desc: 'Углубленный аналитический сценарий',
                      checked: deepResearchEnabled,
                      onChange: () => setChatUiSettings((p) => ({ ...p, deepResearchEnabled: !p.deepResearchEnabled })),
                    },
                  ].map((row, i, arr) => (
                    <HStack
                      key={row.key}
                      justify="space-between"
                      px={4}
                      py={3.5}
                      spacing={3}
                      borderBottom={i < arr.length - 1 ? `1px solid ${CHAT_THEME.panelBorder}` : 'none'}
                      transition="background 0.15s"
                      _hover={{ bg: 'rgba(255,255,255,0.02)' }}
                    >
                      <HStack spacing={3} align="center" flex="1" minW="0">
                        <Box
                          w="32px"
                          h="32px"
                          borderRadius="9px"
                          display="flex"
                          alignItems="center"
                          justifyContent="center"
                          bg={row.checked ? CHAT_THEME.accentSoft : 'rgba(255,255,255,0.04)'}
                          border={`1px solid ${row.checked ? 'rgba(239,68,68,0.28)' : CHAT_THEME.panelBorder}`}
                          flexShrink={0}
                          transition="all 0.2s"
                        >
                          <Icon as={row.icon} boxSize={3.5} color={row.checked ? '#fca5a5' : CHAT_THEME.textTertiary} />
                        </Box>
                        <VStack align="start" spacing={0} minW="0">
                          <Text fontSize="13px" fontWeight="600" color={CHAT_THEME.textPrimary} letterSpacing="-0.005em">
                            {row.title}
                          </Text>
                          <Text fontSize="11.5px" fontWeight="500" color={CHAT_THEME.textSecondary} noOfLines={1}>
                            {row.desc}
                          </Text>
                        </VStack>
                      </HStack>
                      <Switch
                        isChecked={row.checked}
                        onChange={row.onChange}
                        size="md"
                        sx={{
                          '& .chakra-switch__track[data-checked]': {
                            background: '#ef4444',
                          },
                          '& .chakra-switch__track:not([data-checked])': {
                            background: 'rgba(255,255,255,0.12)',
                          },
                          '& .chakra-switch__track:focus, & .chakra-switch__track[data-focus]': {
                            boxShadow: '0 0 0 3px rgba(239,68,68,0.35)',
                          },
                        }}
                      />
                    </HStack>
                  ))}
                </Box>
              </VStack>

              <Divider borderColor="rgba(255,255,255,0.06)" />

              <Button
                leftIcon={<FiRotateCcw />}
                size="md"
                h="42px"
                variant="ghost"
                fontWeight="600"
                fontSize="13px"
                borderRadius="12px"
                color={CHAT_THEME.textSecondary}
                bg="rgba(255,255,255,0.025)"
                border={`1px solid ${CHAT_THEME.panelBorder}`}
                _hover={{
                  bg: CHAT_THEME.panelHover,
                  color: CHAT_THEME.textPrimary,
                  borderColor: CHAT_THEME.panelBorderStrong,
                }}
                onClick={resetUiSettings}
              >
                Сбросить локальные настройки
              </Button>

              <Text fontSize="11px" color={CHAT_THEME.textTertiary} textAlign="center" fontWeight="500" mt={-1}>
                Настройки сохраняются локально в этом браузере
              </Text>
            </VStack>
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      <ProfileDrawer
        isOpen={profileDisclosure.isOpen}
        onClose={profileDisclosure.onClose}
        profileData={profileData}
        profileMemoryCount={profileMemoryCount}
        isLoading={isProfileLoading}
        user={user}
        threadCount={recentThreads.length}
        memoryFallbackCount={memoryFacts.length}
        onLogout={logout}
      />
    </ChatPageLayout>
  );
}

export default ChatPageContainer;
