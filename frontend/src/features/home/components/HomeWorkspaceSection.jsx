import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Box,
  Button,
  Center,
  Drawer,
  DrawerBody,
  DrawerCloseButton,
  DrawerContent,
  DrawerHeader,
  DrawerOverlay,
  Flex,
  HStack,
  Icon,
  IconButton,
  Select,
  SimpleGrid,
  Spinner,
  Text,
  Textarea,
  VStack,
  useDisclosure,
  useToast,
} from '@chakra-ui/react';
import {
  FiX,
  FiFileText,
  FiFolder,
  FiGlobe,
  FiImage,
  FiMenu,
  FiMessageSquare,
  FiMic,
  FiPaperclip,
  FiPlus,
  FiSend,
  FiSettings,
  FiSliders,
} from 'react-icons/fi';
import { NavLink } from 'react-router-dom';
import { useGuestSession } from '@hooks/useGuestSession';
import { useAuth } from '@context/AuthContext';
import AuthModal, { useAuthModal } from '@features/auth/components/AuthModal';
import BrandMark from '@ui/layout/BrandMark';
import {
  createChatThread,
  deleteChatThread,
  getChatHistory,
  getChatModels,
  getUserChats,
  sendChatMessage,
  uploadFileForChat,
} from '../../../API/chat';
import { colors } from '@theme/tokens';
import { extractUrlCandidates } from '@utils/urlParser';

const ASSISTANT_OPTIONS = [
  { value: 'auto', label: 'Универсальный ассистент (Auto)' },
  { value: 'text', label: 'Текст и чат' },
  { value: 'code', label: 'Написание кода' },
  { value: 'image', label: 'Генерация изображений' },
];

const CONTEXT_OPTIONS = [
  { value: 'alpha', label: 'Проект "Альфа"' },
  { value: 'personal', label: 'Личный контекст' },
];

const QUICK_ACTIONS = [
  {
    key: 'pdf-summary',
    title: 'Сделать саммари PDF',
    icon: FiFileText,
    prompt: 'Сделай краткое саммари PDF и выдели ключевые выводы.',
  },
  {
    key: 'deep-research',
    title: 'Глубокий ресерч темы (Deep Research)',
    icon: FiGlobe,
    prompt: 'Проведи глубокий ресерч темы с источниками и выводами.',
  },
  {
    key: 'pptx',
    title: 'Сгенерировать .PPTX',
    icon: FiSliders,
    prompt: 'Сгенерируй структуру презентации .PPTX по теме проекта.',
  },
  {
    key: 'illustration',
    title: 'Создать иллюстрацию',
    icon: FiImage,
    prompt: 'Создай концепт иллюстрации для текущего проекта.',
  },
];

const AUTH_ACCENT = '#ef4444';
const AUTH_ACCENT_HOVER = '#dc2626';
const HOME_SIDEBAR_COLLAPSE_STORAGE_KEY = 'gpthub.home.sidebar.collapsed';

const AUTH_OUTLINE_BUTTON_SX = {
  variant: 'outline',
  borderColor: 'rgba(255, 255, 255, 0.22)',
  color: colors.text.secondary,
  bg: 'rgba(255, 255, 255, 0.03)',
  _hover: {
    color: colors.text.primary,
    bg: 'rgba(255, 255, 255, 0.08)',
    borderColor: 'rgba(239, 68, 68, 0.32)',
  },
};

const TRACE_PREPARATION_STEPS = [
  'Анализирую запрос',
  'Подбираю модель и инструменты',
  'Проверяю контекст и вложения',
  'Формирую ответ',
];

const GUEST_MAX_REQUESTS = 10;

const createThreadId = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (symbol) => {
    const rnd = Math.random() * 16 | 0;
    const value = symbol === 'x' ? rnd : ((rnd & 0x3) | 0x8);
    return value.toString(16);
  });
};

const normalizeThreadTitle = (thread, fallback) => {
  return thread?.title || thread?.last_message || fallback;
};

const findModelByProfile = (profile, models) => {
  const blockedMarkers = ['bge', 'e5', 'gte', 'embed', 'embedding', 'rerank', 'ranker'];
  const normalized = [...new Set(
    (models || [])
      .map((model) => String(model).trim())
      .filter(Boolean)
      .filter((id) => !blockedMarkers.some((marker) => id.toLowerCase().includes(marker)))
  )];
  if (!normalized.length) {
    return '';
  }

  const preferredTextModel =
    normalized.find((id) => /(gpt|qwen|llama|mistral|gemma|deepseek|yi|phi|glm|kimi|instruct|chat|alpha)/i.test(id))
    || normalized[0];

  if (profile === 'code') {
    return normalized.find((id) => /(kodify|code|coder|codestral|cotype|starcoder|deepseek.*coder|qwen.*coder)/i.test(id)) || normalized[0];
  }

  if (profile === 'image') {
    return normalized.find((id) => /(image|vision|vl|multimodal)/i.test(id)) || normalized[0];
  }

  if (profile === 'text') {
    return preferredTextModel;
  }

  return preferredTextModel;
};

function HomeWorkspaceSection() {
  const toast = useToast();
  const sidebarDisclosure = useDisclosure();
  const memoryDisclosure = useDisclosure();
  const settingsDisclosure = useDisclosure();
  const inputRef = useRef(null);

  const { isAuthenticated, user } = useAuth();
  const resolveSessionUserId = useCallback(() => {
    const fromAuth = user?.id ? String(user.id) : '';
    if (fromAuth) {
      if (typeof window !== 'undefined') {
        window.sessionStorage.setItem('user_id', fromAuth);
      }
      return fromAuth;
    }
    const fromStorage = typeof window !== 'undefined' ? window.sessionStorage.getItem('user_id') : '';
    if (fromStorage) {
      return fromStorage;
    }
    if (typeof document !== 'undefined') {
      return document.cookie.split('; ').find((r) => r.startsWith('user_id='))?.split('=')[1] || '';
    }
    return '';
  }, [user?.id]);

  const { checkLimits, incrementRequests, remainingRequests } = useGuestSession();
  const { isOpen: isAuthModalOpen, onClose: onAuthModalClose, showAuthModal, modalData } = useAuthModal();

  const [assistantProfile, setAssistantProfile] = useState('auto');
  const [workspaceContext, setWorkspaceContext] = useState('alpha');
  const [availableModels, setAvailableModels] = useState([]);
  const [manualModelOverride, setManualModelOverride] = useState('');
  const [inputValue, setInputValue] = useState('');
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [deepResearchEnabled, setDeepResearchEnabled] = useState(false);
  const [showTracePanel, setShowTracePanel] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recentThreads, setRecentThreads] = useState([]);
  const [activeThreadId, setActiveThreadId] = useState(null);
  const [activeDraftThreadId, setActiveDraftThreadId] = useState(null);
  const [conversationMessages, setConversationMessages] = useState([]);
  const [traceStepIndex, setTraceStepIndex] = useState(-1);
  const [isTraceVisible, setIsTraceVisible] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.localStorage.getItem(HOME_SIDEBAR_COLLAPSE_STORAGE_KEY) === '1';
  });
  const [deletingThreadId, setDeletingThreadId] = useState(null);
  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const traceTimerRef = useRef(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(HOME_SIDEBAR_COLLAPSE_STORAGE_KEY, isSidebarCollapsed ? '1' : '0');
  }, [isSidebarCollapsed]);

  useEffect(() => {
    return () => {
      if (traceTimerRef.current) {
        clearInterval(traceTimerRef.current);
        traceTimerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadModels = async () => {
      try {
        const models = await getChatModels();
        if (!cancelled) {
          setAvailableModels(models);
        }
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

  useEffect(() => {
    let cancelled = false;

    const loadThreads = async () => {
      try {
  const data = await getUserChats(resolveSessionUserId() || null, 15);
        if (cancelled) {
          return;
        }

        const list = Array.isArray(data) ? data : (data?.chats || data?.threads || []);
        const mapped = list
          .map((thread) => {
            const id = thread?.thread_id || thread?.id || (typeof thread === 'string' ? thread : null);
            if (!id) return null;
            return {
              id,
              title: normalizeThreadTitle(thread, `Чат ${String(id).slice(0, 8)}`),
              isDraft: false,
            };
          })
          .filter(Boolean);

        setRecentThreads((prev) => {
          const drafts = prev.filter((thread) => thread.isDraft);
          return [...drafts, ...mapped].slice(0, 18);
        });
      } catch {
        // Non-critical for home screen
      }
    };

    if (isAuthenticated) {
      loadThreads();
    }

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, resolveSessionUserId]);

  const loadThreadHistory = useCallback(async (threadId) => {
    try {
      const data = await getChatHistory(threadId, 100);
      const rows = data?.messages || [];
      const mapped = rows.map((row, idx) => ({
        id: `hist_${threadId}_${idx}_${row.created_at || Date.now()}`,
        type: row.sender === 'user' ? 'user' : 'agent',
        content: row.content || '',
        timestamp: row.created_at || new Date().toISOString(),
      }));
      setConversationMessages(mapped);
    } catch {
      setConversationMessages([]);
    }
  }, []);

  const selectedProfileModel = useMemo(() => {
    return findModelByProfile(assistantProfile, availableModels);
  }, [assistantProfile, availableModels]);

  const startChat = useCallback(async (text) => {
    const trimmed = String(text || '').trim();
    if (!trimmed) {
      return;
    }

    if (!isAuthenticated) {
      const limitsCheck = checkLimits();
      if (!limitsCheck.allowed) {
        showAuthModal(
          'Превышен лимит запросов',
          'Бесплатные запросы закончились. Войдите, чтобы продолжить.',
          'request_limit'
        );
        return;
      }
    }

    if (assistantProfile !== 'auto' && !selectedProfileModel) {
      toast({
        title: 'Модель пока недоступна',
        description: 'Для выбранного режима не найдено подходящей модели.',
        status: 'warning',
        duration: 2500,
      });
      return;
    }

    setIsSubmitting(true);

    if (showTracePanel) {
      if (traceTimerRef.current) {
        clearInterval(traceTimerRef.current);
      }
      setIsTraceVisible(true);
      setTraceStepIndex(0);
      traceTimerRef.current = setInterval(() => {
        setTraceStepIndex((prev) => Math.min(prev + 1, TRACE_PREPARATION_STEPS.length - 1));
      }, 700);
    }

    try {
      if (!isAuthenticated) {
        incrementRequests();
      }

      // Auto-parse URLs in the message
      let fileContext = attachedFile?.extracted_text || '';
      try {
        const foundUrls = extractUrlCandidates(trimmed, 2);
        if (foundUrls.length > 0) {
          toast({ title: 'Читаю ссылку…', status: 'info', duration: 2000 });
          const { parseUrl: apiParseUrl } = await import('../../../API/chat');
          const results = await Promise.allSettled(foundUrls.map((u) => apiParseUrl(u)));
          const parsed = results
            .filter((r) => r.status === 'fulfilled' && r.value?.content)
            .map((r) => `### Содержимое: ${r.value.title || r.value.url}\n${r.value.content.slice(0, 3000)}`)
            .join('\n\n');
          if (parsed) {
            fileContext = fileContext ? `${fileContext}\n\n${parsed}` : parsed;
          }
        }
      } catch {
        // silent
      }

      let threadId = activeThreadId;
      const hasDraft = !!activeDraftThreadId;
      const effectiveUserId = resolveSessionUserId() || null;
      if (!threadId || hasDraft) {
        const created = await createChatThread(effectiveUserId);
        threadId = created?.thread_id || created?.id || createThreadId();
      }

      const inputType = assistantProfile === 'image' ? 'image' : 'text';
      const selectedModel = manualModelOverride
        || (assistantProfile === 'auto' ? null : selectedProfileModel);

      const userMessage = {
        id: `local_user_${Date.now()}_${Math.random()}`,
        type: 'user',
        content: trimmed,
        timestamp: new Date().toISOString(),
      };
      setConversationMessages((prev) => [...prev, userMessage]);

      const response = await sendChatMessage(
        threadId,
        trimmed,
        effectiveUserId,
        selectedModel || null,
        inputType,
        {
          webSearch: webSearchEnabled,
          deepResearch: deepResearchEnabled,
          fileContext: fileContext ? fileContext.substring(0, 4000) : '',
        }
      );

      const replyText = String(response?.reply || '').trim();
      if (replyText) {
        setConversationMessages((prev) => [
          ...prev,
          {
            id: `local_agent_${Date.now()}_${Math.random()}`,
            type: 'agent',
            content: replyText,
            timestamp: new Date().toISOString(),
          },
        ]);
      }

      setRecentThreads((prev) => {
        const nextTitle = trimmed.slice(0, 72);
        const withoutDraft = prev.filter((thread) => !thread.isDraft);
        const exists = withoutDraft.some((thread) => thread.id === threadId);
        if (exists) {
          const updated = withoutDraft.map((thread) => (
            thread.id === threadId
              ? { ...thread, title: nextTitle, isDraft: false }
              : thread
          ));
          const selected = updated.find((thread) => thread.id === threadId);
          const rest = updated.filter((thread) => thread.id !== threadId);
          return selected ? [selected, ...rest].slice(0, 18) : updated.slice(0, 18);
        }
        return [{ id: threadId, title: nextTitle, isDraft: false }, ...withoutDraft].slice(0, 18);
      });

      setActiveThreadId(threadId);
      setActiveDraftThreadId(null);
      setAttachedFile(null);
      setInputValue('');
    } catch (err) {
      const errText = String(err?.response?.data?.detail || err?.message || '').trim();
      setConversationMessages((prev) => [
        ...prev,
        {
          id: `local_agent_error_${Date.now()}_${Math.random()}`,
          type: 'agent',
          content: errText
            ? `Не удалось получить ответ: ${errText}`
            : 'Не удалось получить ответ. Проверьте соединение и попробуйте снова.',
          timestamp: new Date().toISOString(),
        },
      ]);
      toast({
        title: 'Ошибка отправки сообщения',
        description: errText || 'Сервис временно недоступен',
        status: 'error',
        duration: 2600,
      });
    } finally {
      if (traceTimerRef.current) {
        clearInterval(traceTimerRef.current);
        traceTimerRef.current = null;
      }
      if (showTracePanel) {
        setTraceStepIndex(TRACE_PREPARATION_STEPS.length - 1);
        setTimeout(() => {
          setIsTraceVisible(false);
          setTraceStepIndex(-1);
        }, 550);
      }
      setIsSubmitting(false);
    }
  }, [activeDraftThreadId, activeThreadId, assistantProfile, attachedFile, checkLimits, incrementRequests, isAuthenticated, manualModelOverride, resolveSessionUserId, selectedProfileModel, showAuthModal, showTracePanel, toast, webSearchEnabled, deepResearchEnabled]);

  const handleQuickAction = useCallback((prompt) => {
    setInputValue(prompt);
    setTimeout(() => {
      inputRef.current?.focus();
    }, 0);
  }, []);

  const handleNewChat = useCallback(() => {
    const existingDraft = recentThreads.find((thread) => thread.isDraft);
    if (existingDraft) {
      setActiveDraftThreadId(existingDraft.id);
      setActiveThreadId(null);
      setConversationMessages([]);
      setInputValue('');
      setAttachedFile(null);
      setTimeout(() => {
        inputRef.current?.focus();
      }, 0);
      return;
    }

    const draftId = createThreadId();
    setActiveDraftThreadId(draftId);
    setActiveThreadId(null);
    setConversationMessages([]);
    const draftTitle = `Новый чат ${draftId.slice(0, 8)}`;
    setRecentThreads((prev) => [
      { id: draftId, title: draftTitle, isDraft: true },
      ...prev.filter((thread) => thread.id !== draftId),
    ].slice(0, 18));
    setInputValue('');
    setAttachedFile(null);
    setTimeout(() => {
      inputRef.current?.focus();
    }, 0);
  }, [recentThreads]);

  const handleDeleteThread = useCallback(async (item, event) => {
    event.preventDefault();
    event.stopPropagation();

    if (!item?.id || deletingThreadId === item.id) {
      return;
    }

    if (item.isDraft) {
      setRecentThreads((prev) => prev.filter((thread) => thread.id !== item.id));
      if (activeDraftThreadId === item.id) {
        setActiveDraftThreadId(null);
        setConversationMessages([]);
      }
      return;
    }

    setDeletingThreadId(item.id);
    try {
      await deleteChatThread(item.id, resolveSessionUserId() || null);
      setRecentThreads((prev) => prev.filter((thread) => thread.id !== item.id));

      if (activeThreadId === item.id) {
        setActiveThreadId(null);
        setConversationMessages([]);
        setInputValue('');
      }
    } catch {
      toast({
        title: 'Не удалось удалить чат',
        status: 'error',
        duration: 2200,
      });
    } finally {
      setDeletingThreadId(null);
    }
  }, [activeDraftThreadId, activeThreadId, deletingThreadId, resolveSessionUserId, toast]);

  const sidebar = (
    <VStack h="full" align="stretch" spacing={5}>
      <BrandMark size="sm" />

      <Button
        leftIcon={<FiPlus />}
        borderRadius="xl"
        onClick={handleNewChat}
        {...AUTH_OUTLINE_BUTTON_SX}
      >
        Новый чат
      </Button>

      <Box>
        <Text color={colors.text.tertiary} fontSize="xs" textTransform="uppercase" letterSpacing="0.12em" mb={3}>
          Недавние чаты
        </Text>
        <VStack spacing={2} align="stretch">
          {recentThreads.length === 0 && (
            <Text color={colors.text.tertiary} fontSize="xs" px={1}>Нет чатов</Text>
          )}
          {recentThreads.map((item) => (
            <Box key={item.id} position="relative" role="group">
              <Button
                onClick={async () => {
                  if (item.isDraft) {
                    setActiveDraftThreadId(item.id);
                    setActiveThreadId(null);
                    setConversationMessages([]);
                    setInputValue('');
                    setTimeout(() => {
                      inputRef.current?.focus();
                    }, 0);
                    return;
                  }
                  setActiveDraftThreadId(null);
                  setActiveThreadId(item.id);
                  await loadThreadHistory(item.id);
                }}
                justifyContent="flex-start"
                leftIcon={<Icon as={FiMessageSquare} color={item.isDraft || item.id === activeThreadId ? 'red.300' : colors.text.tertiary} boxSize={4} />}
                px={3}
                py={2}
                pr={10}
                h="auto"
                borderRadius="lg"
                bg={item.isDraft || item.id === activeThreadId ? 'rgba(239,68,68,0.14)' : 'rgba(255,255,255,0.04)'}
                border={`1px solid ${(item.isDraft || item.id === activeThreadId) ? 'rgba(239,68,68,0.4)' : 'rgba(255,255,255,0.08)'}`}
                fontSize="xs"
                fontWeight="400"
                color={item.isDraft || item.id === activeThreadId ? 'red.200' : colors.text.secondary}
                _hover={{ bg: (item.isDraft || item.id === activeThreadId) ? 'rgba(239,68,68,0.2)' : 'rgba(255,255,255,0.1)' }}
              >
                <Text color={item.isDraft || item.id === activeThreadId ? 'red.200' : colors.text.secondary} fontSize="xs" noOfLines={1}>
                  {item.title}
                </Text>
              </Button>

              <IconButton
                aria-label="Удалить чат"
                icon={deletingThreadId === item.id ? <Spinner size="xs" /> : <FiX />}
                size="xs"
                position="absolute"
                right="6px"
                top="50%"
                transform="translateY(-50%) translateX(3px)"
                opacity={item.id === activeThreadId ? 0.92 : 0}
                pointerEvents={item.id === activeThreadId ? 'auto' : 'none'}
                _groupHover={{ opacity: 1, transform: 'translateY(-50%) translateX(0px)', pointerEvents: 'auto' }}
                variant="ghost"
                color="rgba(248,113,113,0.95)"
                _hover={{ bg: 'rgba(239,68,68,0.2)', color: '#fca5a5' }}
                _active={{ bg: 'rgba(239,68,68,0.28)' }}
                borderRadius="8px"
                onClick={(event) => handleDeleteThread(item, event)}
                isDisabled={deletingThreadId === item.id}
                transition="all 0.18s"
              />
            </Box>
          ))}
        </VStack>
      </Box>

      <Box mt="auto">
        <Text color={colors.text.tertiary} fontSize="xs" textTransform="uppercase" letterSpacing="0.12em" mb={3}>
          КОНФИГУРАЦИЯ
        </Text>
        <VStack spacing={2} align="stretch">
          <Button
            size="sm"
            fontSize="xs"
            justifyContent="flex-start"
            leftIcon={<Text fontSize="sm">🧠</Text>}
            variant="outline"
            borderColor="rgba(255,255,255,0.18)"
            color={colors.text.secondary}
            bg="rgba(255,255,255,0.04)"
            _hover={{ bg: 'rgba(255,255,255,0.09)', borderColor: 'rgba(239,68,68,0.45)', color: colors.text.primary }}
            onClick={memoryDisclosure.onOpen}
          >
            Память и контекст
          </Button>
          <Button
            size="sm"
            fontSize="xs"
            justifyContent="flex-start"
            leftIcon={<FiSettings />}
            variant="outline"
            borderColor="rgba(255,255,255,0.18)"
            color={colors.text.secondary}
            bg="rgba(255,255,255,0.04)"
            _hover={{ bg: 'rgba(255,255,255,0.09)', borderColor: 'rgba(239,68,68,0.45)', color: colors.text.primary }}
            onClick={settingsDisclosure.onOpen}
          >
            Настройки системы
          </Button>
        </VStack>
      </Box>
    </VStack>
  );

  return (
    <Box minH="100vh" bg="#060606" color={colors.text.primary} position="relative" overflow="hidden">
      <Box
        position="absolute"
        top="-20%"
        right="-10%"
        w="52%"
        h="52%"
        bg="radial-gradient(circle, rgba(239, 68, 68, 0.16) 0%, transparent 70%)"
        filter="blur(60px)"
        pointerEvents="none"
      />
      <Box
        position="absolute"
        bottom="-24%"
        left="-10%"
        w="46%"
        h="46%"
        bg="radial-gradient(circle, rgba(255, 255, 255, 0.08) 0%, transparent 70%)"
        filter="blur(70px)"
        pointerEvents="none"
      />
      <Flex h="100vh" overflow="hidden">
        <Box
          as="aside"
          display={{ base: 'none', lg: 'block' }}
          w={isSidebarCollapsed ? '0' : '290px'}
          p={isSidebarCollapsed ? 0 : 5}
          borderRight={isSidebarCollapsed ? 'none' : '1px solid rgba(255,255,255,0.08)'}
          bg="rgba(12,12,12,0.78)"
          backdropFilter="blur(14px)"
          overflow="hidden"
          transition="width 0.22s ease, padding 0.22s ease, border-color 0.22s ease"
        >
          {!isSidebarCollapsed && sidebar}
        </Box>

        <VStack flex="1" align="stretch" spacing={0}>
          <Flex
            as="header"
            align="center"
            justify="space-between"
            px={{ base: 3, md: 6 }}
            py={3}
            borderBottom="1px solid rgba(255,255,255,0.08)"
            bg="rgba(12,12,12,0.74)"
            backdropFilter="blur(12px)"
          >
            <Box w={{ base: '40px', md: '180px' }}>
              <HStack spacing={2}>
                <IconButton
                  aria-label="Открыть меню"
                  icon={<FiMenu />}
                  display={{ base: 'inline-flex', lg: 'none' }}
                  onClick={sidebarDisclosure.onOpen}
                  variant="ghost"
                />
                <Button
                  size="sm"
                  variant="ghost"
                  leftIcon={<FiMenu />}
                  display={{ base: 'none', lg: 'inline-flex' }}
                  onClick={() => setIsSidebarCollapsed((prev) => !prev)}
                  color={colors.text.secondary}
                  _hover={{ bg: 'rgba(255,255,255,0.08)', color: colors.text.primary }}
                >
                  {isSidebarCollapsed ? 'Показать чаты' : 'Скрыть чаты'}
                </Button>
              </HStack>
            </Box>

            <HStack spacing={2} flex="1" justify="center">
              <Select
                value={assistantProfile}
                onChange={(e) => { setAssistantProfile(e.target.value); setManualModelOverride(''); }}
                maxW="280px"
                borderRadius="full"
                bg="rgba(255,255,255,0.08)"
                borderColor="rgba(255,255,255,0.15)"
                fontSize="xs"
                fontWeight="600"
                sx={{ option: { color: '#111', background: '#fff' } }}
              >
                {ASSISTANT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </Select>

              <Select
                value={manualModelOverride}
                onChange={(e) => setManualModelOverride(e.target.value)}
                maxW="280px"
                borderRadius="full"
                bg={manualModelOverride ? 'rgba(239,68,68,0.18)' : 'rgba(255,255,255,0.08)'}
                borderColor={manualModelOverride ? 'rgba(239,68,68,0.5)' : 'rgba(255,255,255,0.15)'}
                fontSize="xs"
                fontWeight="600"
                sx={{ option: { color: '#111', background: '#fff' } }}
                isDisabled={availableModels.length === 0}
                title={availableModels.length === 0 ? 'Модели недоступны — проверьте API ключ' : 'Выбрать модель вручную'}
              >
                <option value="">{availableModels.length === 0 ? '⚠️ Модели недоступны' : '🤖 Модель: авто'}</option>
                {availableModels.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </Select>
            </HStack>

            <HStack w={{ base: 'auto', md: '260px' }} justify="flex-end" spacing={2}>
              {!isAuthenticated ? (
                <>
                  <Button
                    as={NavLink}
                    to="/login"
                    size="sm"
                    display={{ base: 'none', md: 'flex' }}
                    {...AUTH_OUTLINE_BUTTON_SX}
                  >
                    Войти
                  </Button>
                  <Button
                    as={NavLink}
                    to="/register"
                    size="sm"
                    display={{ base: 'none', md: 'flex' }}
                    borderRadius="10px"
                    fontSize="13px"
                    bg={AUTH_ACCENT}
                    color="white"
                    _hover={{ bg: AUTH_ACCENT_HOVER }}
                    _active={{ bg: AUTH_ACCENT_HOVER }}
                  >
                    Регистрация
                  </Button>
                </>
              ) : (
                <>
                  <Icon as={FiFolder} color={colors.text.tertiary} boxSize={4} display={{ base: 'none', md: 'block' }} />
                  <Select
                    value={workspaceContext}
                    onChange={(e) => setWorkspaceContext(e.target.value)}
                    maxW="180px"
                    size="sm"
                    bg="rgba(255,255,255,0.08)"
                    borderColor="rgba(255,255,255,0.15)"
                    sx={{ option: { color: '#111', background: '#fff' } }}
                    display={{ base: 'none', md: 'block' }}
                  >
                    {CONTEXT_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </Select>
                </>
              )}
            </HStack>
          </Flex>

          <Center flex="1" px={{ base: 4, md: 8 }} pt={{ base: 8, md: 12 }} pb={{ base: 36, md: 40 }}>
            {conversationMessages.length === 0 ? (
              <VStack spacing={7} maxW="860px" w="full" align="stretch">
                <VStack spacing={2}>
                  <Text fontSize={{ base: 'xl', md: '2xl' }} fontWeight="700" textAlign="center">
                    Доброе утро! Готовы продолжить работу над проектом "Альфа"?
                  </Text>
                  <Text color={colors.text.tertiary} textAlign="center" fontSize="xs">
                    ИИ помнит ваш рабочий контекст и готов продолжить с текущего состояния.
                  </Text>
                </VStack>

                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                  {QUICK_ACTIONS.map((item) => (
                    <Button
                      key={item.key}
                      onClick={() => handleQuickAction(item.prompt)}
                      h="92px"
                      justifyContent="flex-start"
                      leftIcon={<Icon as={item.icon} boxSize={5} />}
                      bg="rgba(255,255,255,0.06)"
                      border="1px solid rgba(255,255,255,0.12)"
                      borderRadius="2xl"
                      color={colors.text.primary}
                      fontWeight="500"
                      fontSize="sm"
                      whiteSpace="normal"
                      px={5}
                      _hover={{ bg: 'rgba(255,255,255,0.1)', transform: 'translateY(-1px)' }}
                    >
                      {item.title}
                    </Button>
                  ))}
                </SimpleGrid>
              </VStack>
            ) : (
              <VStack spacing={4} align="stretch" w="100%" maxW="980px" mx="auto">
                {showTracePanel && isTraceVisible && (
                  <Box
                    p={4}
                    borderRadius="xl"
                    bg="rgba(239,68,68,0.08)"
                    border="1px solid rgba(239,68,68,0.26)"
                  >
                    <Text fontSize="11px" textTransform="uppercase" letterSpacing="0.08em" color="red.200" mb={2}>
                      Этапы подготовки ответа
                    </Text>
                    <VStack align="stretch" spacing={1.5}>
                      {TRACE_PREPARATION_STEPS.map((step, index) => {
                        const done = index < traceStepIndex;
                        const current = index === traceStepIndex;
                        return (
                          <HStack key={step} spacing={2}>
                            <Text color={done ? 'red.300' : current ? 'red.200' : colors.text.tertiary} fontSize="xs">
                              {done ? '✓' : current ? '•' : '○'}
                            </Text>
                            <Text color={done || current ? colors.text.primary : colors.text.secondary} fontSize="xs">
                              {step}
                            </Text>
                          </HStack>
                        );
                      })}
                    </VStack>
                  </Box>
                )}
                {conversationMessages.map((message) => (
                  <Box
                    key={message.id}
                    display="flex"
                    justifyContent={message.type === 'user' ? 'flex-end' : 'flex-start'}
                    w="100%"
                  >
                    <Box
                      p={4}
                      borderRadius="xl"
                      bg={message.type === 'user' ? 'rgba(171, 28, 28, 0.22)' : 'rgba(255,255,255,0.05)'}
                      maxW={{ base: '95%', md: '82%' }}
                      border={`1px solid ${message.type === 'user' ? 'rgba(239, 68, 68, 0.45)' : 'rgba(255,255,255,0.1)'}`}
                    >
                      <Text whiteSpace="pre-wrap">{message.content}</Text>
                    </Box>
                  </Box>
                ))}
              </VStack>
            )}
          </Center>

          <Box
            position="sticky"
            bottom={0}
            px={{ base: 3, md: 6 }}
            py={4}
            borderTop="1px solid rgba(255,255,255,0.08)"
            bg="linear-gradient(180deg, rgba(11,11,11,0.72) 0%, rgba(11,11,11,0.96) 45%)"
            backdropFilter="blur(12px)"
          >
            <Box maxW="980px" mx="auto">
              <Box position="relative">
                <input
                  type="file"
                  ref={fileInputRef}
                  style={{ display: 'none' }}
                  accept=".txt,.md,.pdf,.docx,.csv,.json,.png,.jpg,.jpeg,.gif,.webp,.mp3,.wav,.ogg,.m4a,.webm"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    try {
                      const result = await uploadFileForChat(file);
                      setAttachedFile(result);
                      toast({
                        title: `Файл загружен: ${result.filename}`,
                        description: result.file_type === 'image'
                          ? 'Изображение готово для анализа'
                          : `Извлечено ${(result.extracted_text || '').length} символов текста`,
                        status: 'success',
                        duration: 3000,
                      });
                    } catch (err) {
                      toast({ title: 'Ошибка загрузки файла', description: String(err), status: 'error', duration: 4000 });
                    }
                    e.target.value = '';
                  }}
                />
                <IconButton
                  aria-label="Прикрепить файл"
                  icon={<FiPaperclip />}
                  size="sm"
                  variant="ghost"
                  position="absolute"
                  left={3}
                  top={3}
                  zIndex={2}
                  color={attachedFile ? 'red.300' : undefined}
                  onClick={() => fileInputRef.current?.click()}
                />

                <Textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      startChat(inputValue);
                    }
                  }}
                  placeholder="Опишите задачу, прикрепите файл или используйте / для команд..."
                  minH="88px"
                  maxH="220px"
                  resize="vertical"
                  pl={12}
                  pr={28}
                  py={4}
                  fontSize="sm"
                  borderRadius="2xl"
                  bg="rgba(255,255,255,0.08)"
                  border="1px solid rgba(255,255,255,0.14)"
                  color={colors.text.primary}
                  _placeholder={{ color: colors.text.tertiary, fontSize: 'xs' }}
                  _focus={{ borderColor: 'rgba(239,68,68,0.85)', boxShadow: '0 0 0 1px rgba(239,68,68,0.4)' }}
                />

                <HStack position="absolute" right={3} bottom={3} spacing={2} zIndex={2}>
                  <IconButton
                    aria-label="Голосовой ввод"
                    icon={<FiMic />}
                    size="sm"
                    variant="ghost"
                    color={isRecording ? 'red.400' : undefined}
                    onClick={async () => {
                      if (isRecording) {
                        // Stop recording
                        if (mediaRecorderRef.current) {
                          mediaRecorderRef.current.stop();
                          setIsRecording(false);
                        }
                        return;
                      }
                      // Start recording
                      try {
                        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                        const mediaRecorder = new MediaRecorder(stream);
                        const chunks = [];
                        mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
                        mediaRecorder.onstop = async () => {
                          stream.getTracks().forEach(t => t.stop());
                          const blob = new Blob(chunks, { type: 'audio/webm' });
                          const file = new File([blob], 'voice_message.webm', { type: 'audio/webm' });
                          try {
                            const result = await uploadFileForChat(file);
                            if (result.extracted_text && !result.extracted_text.startsWith('[')) {
                              setInputValue(prev => prev ? `${prev} ${result.extracted_text}` : result.extracted_text);
                              toast({ title: 'Голос распознан', status: 'success', duration: 2000 });
                            } else {
                              toast({ title: 'Голос записан', description: 'Транскрипция недоступна', status: 'info', duration: 2000 });
                              setAttachedFile(result);
                            }
                          } catch (err) {
                            toast({ title: 'Ошибка распознавания голоса', status: 'error', duration: 3000 });
                          }
                        };
                        mediaRecorder.start();
                        mediaRecorderRef.current = mediaRecorder;
                        setIsRecording(true);
                        toast({ title: 'Запись...', description: 'Нажмите ещё раз для остановки', status: 'info', duration: 2000 });
                      } catch {
                        toast({ title: 'Микрофон недоступен', status: 'error', duration: 3000 });
                      }
                    }}
                  />
                  <IconButton
                    aria-label="Отправить"
                    icon={<FiSend size={18} />}
                    size="sm"
                    bg="rgba(239,68,68,0.24)"
                    color="red.200"
                    border="1px solid rgba(239,68,68,0.56)"
                    _hover={{ bg: 'rgba(239,68,68,0.32)', color: 'red.100' }}
                    borderRadius="full"
                    isDisabled={!inputValue.trim() || isSubmitting}
                    onClick={() => startChat(inputValue)}
                  />
                </HStack>
              </Box>

              {attachedFile && (
                <HStack mt={2} px={2} py={1} bg="rgba(239,68,68,0.15)" borderRadius="lg" spacing={2}>
                  <Icon as={FiFileText} color="red.300" boxSize={4} />
                  <Text fontSize="xs" color="red.200" noOfLines={1}>
                    {attachedFile.filename} ({attachedFile.file_type})
                  </Text>
                  <IconButton
                    aria-label="Удалить файл"
                    icon={<Text fontSize="xs">✕</Text>}
                    size="xs"
                    variant="ghost"
                    onClick={() => setAttachedFile(null)}
                  />
                </HStack>
              )}

              <HStack mt={3} spacing={2} justify="space-between" flexWrap="wrap">
                <HStack spacing={2}>
                  <Button
                    size="xs"
                    borderRadius="full"
                    variant={webSearchEnabled ? 'solid' : 'outline'}
                    colorScheme={webSearchEnabled ? 'red' : 'gray'}
                    onClick={() => setWebSearchEnabled((prev) => !prev)}
                    fontSize="10px"
                    leftIcon={<Text fontSize="xs">🌐</Text>}
                  >
                    Веб-поиск
                  </Button>
                  <Button
                    size="xs"
                    borderRadius="full"
                    variant={deepResearchEnabled ? 'solid' : 'outline'}
                    colorScheme={deepResearchEnabled ? 'red' : 'gray'}
                    onClick={() => setDeepResearchEnabled((prev) => !prev)}
                    fontSize="10px"
                    leftIcon={<Text fontSize="xs">🕵️</Text>}
                  >
                    Deep Research
                  </Button>
                </HStack>

                <Text fontSize="10px" color={colors.text.tertiary}>
                  {assistantProfile === 'auto'
                    ? 'Режим Auto сам подберет модель под запрос'
                    : `Режим профиля: ${selectedProfileModel || 'подходящая модель не найдена'}`}
                </Text>
                {!isAuthenticated && (
                  <Text
                    fontSize="10px"
                    color={remainingRequests > 0 ? colors.text.tertiary : 'red.300'}
                  >
                    {`Гостевые запросы: ${remainingRequests}/${GUEST_MAX_REQUESTS} (сброс раз в сутки)`}
                  </Text>
                )}
              </HStack>
            </Box>
          </Box>
        </VStack>
      </Flex>

      <Drawer isOpen={sidebarDisclosure.isOpen} placement="left" onClose={sidebarDisclosure.onClose}>
        <DrawerOverlay />
        <DrawerContent bg="rgba(10,10,10,0.96)" borderRight="1px solid rgba(255,255,255,0.12)">
          <DrawerCloseButton mt={2} />
          <DrawerHeader borderBottomWidth="1px" borderColor="rgba(255,255,255,0.08)">
            Навигация
          </DrawerHeader>
          <DrawerBody pt={4}>{sidebar}</DrawerBody>
        </DrawerContent>
      </Drawer>

      <Drawer isOpen={memoryDisclosure.isOpen} placement="right" onClose={memoryDisclosure.onClose} size="sm">
        <DrawerOverlay />
        <DrawerContent bg="rgba(10,10,10,0.96)" borderLeft="1px solid rgba(255,255,255,0.12)">
          <DrawerCloseButton mt={2} />
          <DrawerHeader borderBottomWidth="1px" borderColor="rgba(255,255,255,0.08)">
            Память и контекст
          </DrawerHeader>
          <DrawerBody pt={4}>
            <Text color={colors.text.secondary} fontSize="sm">
              Здесь будет управление фактами долговременной памяти и контекстом сессии.
            </Text>
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
        <DrawerOverlay bg="rgba(0,0,0,0.55)" backdropFilter="blur(3px)" />
        <DrawerContent
          bg="linear-gradient(180deg, rgba(14,14,14,0.98) 0%, rgba(9,9,9,0.98) 100%)"
          borderLeft="1px solid rgba(255,255,255,0.14)"
          boxShadow="-16px 0 44px rgba(0,0,0,0.45)"
          sx={{ willChange: 'transform, opacity', transform: 'translateZ(0)' }}
        >
          <DrawerCloseButton
            mt={3}
            mr={2}
            borderRadius="10px"
            color={colors.text.secondary}
            _hover={{ bg: 'rgba(255,255,255,0.08)', color: colors.text.primary }}
          />
          <DrawerHeader borderBottomWidth="1px" borderColor="rgba(255,255,255,0.09)" py={5}>
            <VStack align="start" spacing={1} pr={10}>
              <Text fontWeight="700" letterSpacing="0.01em" fontSize="lg">Настройки системы</Text>
              <Text fontSize="12px" color={colors.text.secondary} fontWeight="500">
                Управляйте поведением интерфейса и инструментов по умолчанию
              </Text>
            </VStack>
          </DrawerHeader>
          <DrawerBody px={5} py={5}>
            <VStack align="stretch" spacing={4}>
              <Box p={4} borderRadius="xl" bg="rgba(255,255,255,0.03)" border="1px solid rgba(255,255,255,0.1)">
                <Text fontSize="11px" fontWeight="700" color={colors.text.secondary} textTransform="uppercase" letterSpacing="0.08em" mb={2}>
                  Интерфейс
                </Text>
                <HStack justify="space-between" p={3} borderRadius="lg" bg="rgba(255,255,255,0.04)" border="1px solid rgba(255,255,255,0.08)">
                  <VStack align="start" spacing={0}>
                    <Text fontSize="13px" fontWeight="600">Пошаговый режим</Text>
                    <Text fontSize="11px" fontWeight="500" color={colors.text.secondary}>Показывать этапы подготовки перед ответом</Text>
                  </VStack>
                  <Button
                    size="xs"
                    borderRadius="full"
                    fontWeight="600"
                    colorScheme={showTracePanel ? 'red' : 'gray'}
                    variant={showTracePanel ? 'solid' : 'outline'}
                    onClick={() => setShowTracePanel((prev) => !prev)}
                  >
                    {showTracePanel ? 'Вкл' : 'Выкл'}
                  </Button>
                </HStack>
              </Box>

              <Box p={4} borderRadius="xl" bg="rgba(255,255,255,0.03)" border="1px solid rgba(255,255,255,0.1)">
                <Text fontSize="11px" fontWeight="700" color={colors.text.secondary} textTransform="uppercase" letterSpacing="0.08em" mb={2}>
                  Инструменты По Умолчанию
                </Text>
                <VStack align="stretch" spacing={2}>
                  <HStack justify="space-between" p={3} borderRadius="lg" bg="rgba(255,255,255,0.04)" border="1px solid rgba(255,255,255,0.08)">
                    <VStack align="start" spacing={0}>
                      <Text fontSize="13px" fontWeight="600">Веб-поиск</Text>
                      <Text fontSize="11px" fontWeight="500" color={colors.text.secondary}>Подмешивать внешние источники в ответ</Text>
                    </VStack>
                    <Button
                      size="xs"
                      borderRadius="full"
                      fontWeight="600"
                      colorScheme={webSearchEnabled ? 'red' : 'gray'}
                      variant={webSearchEnabled ? 'solid' : 'outline'}
                      onClick={() => setWebSearchEnabled((prev) => !prev)}
                    >
                      {webSearchEnabled ? 'Вкл' : 'Выкл'}
                    </Button>
                  </HStack>

                  <HStack justify="space-between" p={3} borderRadius="lg" bg="rgba(255,255,255,0.04)" border="1px solid rgba(255,255,255,0.08)">
                    <VStack align="start" spacing={0}>
                      <Text fontSize="13px" fontWeight="600">Deep Research</Text>
                      <Text fontSize="11px" fontWeight="500" color={colors.text.secondary}>Углубленный аналитический сценарий</Text>
                    </VStack>
                    <Button
                      size="xs"
                      borderRadius="full"
                      fontWeight="600"
                      colorScheme={deepResearchEnabled ? 'red' : 'gray'}
                      variant={deepResearchEnabled ? 'solid' : 'outline'}
                      onClick={() => setDeepResearchEnabled((prev) => !prev)}
                    >
                      {deepResearchEnabled ? 'Вкл' : 'Выкл'}
                    </Button>
                  </HStack>
                </VStack>
              </Box>

              <Button
                size="md"
                variant="outline"
                fontWeight="600"
                borderColor="rgba(255,255,255,0.22)"
                color={colors.text.secondary}
                bg="rgba(255,255,255,0.02)"
                _hover={{ bg: 'rgba(255,255,255,0.08)', color: colors.text.primary, borderColor: 'rgba(239,68,68,0.36)' }}
                onClick={() => {
                  setShowTracePanel(true);
                  setWebSearchEnabled(false);
                  setDeepResearchEnabled(false);
                }}
              >
                Сбросить локальные настройки
              </Button>

              <Text fontSize="11px" color={colors.text.tertiary} textAlign="center" px={2}>
                Настройки сохраняются локально в этом браузере
              </Text>
            </VStack>
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      <AuthModal isOpen={isAuthModalOpen} onClose={onAuthModalClose} {...modalData} />
    </Box>
  );
}

export default HomeWorkspaceSection;
