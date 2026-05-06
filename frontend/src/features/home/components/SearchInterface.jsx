import React, { useState, useRef, useEffect } from 'react';
import {
  Input,
  InputGroup,
  InputLeftElement,
  InputRightElement,
  Select,
  VStack,
  HStack,
  Text,
  Icon,
  Spinner,
  useToast,
  Alert,
  AlertIcon,
  AlertDescription,
  CloseButton
} from '@chakra-ui/react';
import { MotionBox } from '@shared/ui/lib/motionPrimitives';
import { FiSearch, FiSend } from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';
import { useGuestSession } from '@hooks/useGuestSession';
import { useAuth } from '@context/AuthContext';
import { colors, borderRadius } from '@theme/tokens';
import AnimatedSuggestions from './AnimatedSuggestions';
import { AuthModal, useAuthModal } from '@features/auth';
import { getChatModels } from '../../../shared/api/chat';
import { SEARCH_THEME } from '@features/home/theme';

/**
 * SearchInterface - Google-like поисковый интерфейс для общения с AI агентами
 *
 * Особенности:
 * - Автофокус при загрузке
 * - Проверка лимитов гостевых сессий
 * - Анимированные состояния загрузки
 * - Keyboard shortcuts (Enter)
 * - Интеграция с навигацией
 */
function SearchInterface() {
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [showLimitWarning, setShowLimitWarning] = useState(false);
  const [rippleEffect, setRippleEffect] = useState(false);
  const [modelMode, setModelMode] = useState('auto');
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [customModelId, setCustomModelId] = useState('');
  const [isModelsLoading, setIsModelsLoading] = useState(false);

  const inputRef = useRef(null);
  const navigate = useNavigate();
  const toast = useToast();

  const {
    session,
    checkLimits,
    incrementRequests,
    shouldShowLimitWarning,
    remainingRequests
  } = useGuestSession();

  const { isAuthenticated } = useAuth();
  const { isOpen: isAuthModalOpen, onClose: onAuthModalClose, showAuthModal, modalData } = useAuthModal();

  // Автофокус на input при загрузке
  useEffect(() => {
    if (inputRef.current && !isLoading) {
      // Небольшая задержка для плавной анимации
      setTimeout(() => {
        inputRef.current.focus();
      }, 1000);
    }
  }, [isLoading]);

  // Показ предупреждения о лимите (только для гостей)
  useEffect(() => {
    if (!isAuthenticated && shouldShowLimitWarning(2)) {
      setShowLimitWarning(true);
    } else {
      setShowLimitWarning(false);
    }
  }, [shouldShowLimitWarning, isAuthenticated]);

  // Загружаем модели MWS, чтобы ручной выбор был доступен уже на главной.
  useEffect(() => {
    let cancelled = false;

    const loadModels = async () => {
      setIsModelsLoading(true);
      try {
        const models = await getChatModels();
        if (!cancelled) {
          setAvailableModels(models);
          if (models.length > 0) {
            setSelectedModel(models[0]);
          }
        }
      } catch (error) {
        if (!cancelled) {
          console.error('Failed to load models on home page:', error);
          setAvailableModels([]);
        }
      } finally {
        if (!cancelled) {
          setIsModelsLoading(false);
        }
      }
    };

    loadModels();
    return () => {
      cancelled = true;
    };
  }, []);

  // Обработка отправки запроса
  const handleSubmit = async (text = query.trim()) => {
    if (!text || isLoading) return;

    const manualModel = selectedModel === '__custom__' ? customModelId.trim() : selectedModel.trim();
    if (modelMode === 'manual' && !manualModel) {
      toast({
        title: 'Выберите модель',
        description: 'В ручном режиме нужно выбрать или ввести model id.',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    setIsLoading(true);
    setShowSuggestions(false);

    try {
      // Для авторизованных пользователей не проверяем лимиты гостевой сессии
      // (у них должны быть свои лимиты на backend)
      if (!isAuthenticated) {
        // Проверка лимитов гостевых сессий
        const limitsCheck = checkLimits();

        if (!limitsCheck.allowed) {
          if (limitsCheck.reason === 'request_limit_exceeded') {
            // Для гостей показываем модальное окно авторизации
            handleShowAuthModal('request_limit');
            setIsLoading(false);
            return;
          }
        }

        // Инкремент счетчика запросов для гостей
        incrementRequests();
      }

      // Создание thread ID как UUID для совместимости с базой данных
      const generateUUID = () => {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
          const r = Math.random() * 16 | 0;
          const v = c === 'x' ? r : ((r & 0x3) | 0x8);
          return v.toString(16);
        });
      };
      const threadId = generateUUID();

      console.log('SearchInterface: Creating chat thread', { threadId, isAuthenticated, text });

      // Переход к чату с предзаполненным сообщением
      const params = new URLSearchParams();
      params.set('initial', text);
      params.set('model_mode', modelMode);
      if (modelMode === 'manual') {
        params.set('model', manualModel);
      }
      navigate(`/chat/${threadId}?${params.toString()}`);

    } catch (error) {
      console.error('Error starting chat:', error);
      toast({
        title: 'Ошибка',
        description: 'Не удалось начать разговор. Попробуйте еще раз.',
        status: 'error',
        duration: 5000,
      });
      setIsLoading(false);
      setShowSuggestions(true);
    }
  };

  // Обработка нажатий клавиш
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Показ модального окна авторизации (только для гостей)
  const handleShowAuthModal = (type = 'request_limit', customTitle, customDescription) => {
    if (!isAuthenticated) {
      showAuthModal(
        customTitle,
        customDescription,
        type,
        () => {
          // Callback после успешной авторизации
          console.log('User authenticated successfully');
        }
      );
    } else {
      // Для авторизованных пользователей показываем сообщение о необходимости пополнения квоты
      toast({
        title: 'Недостаточно квоты',
        description: 'Ваша квота исчерпана. Пожалуйста, пополните баланс для продолжения использования.',
        status: 'warning',
        duration: 10000,
        action: {
          label: 'Пополнить',
          onClick: () => navigate('/billing') // Предполагаемая страница биллинга
        }
      });
    }
  };

  // Обработка клика по подсказке (будет реализовано в AnimatedSuggestions)
  const handleSuggestionClick = (suggestion) => {
    setQuery(suggestion);
    setTimeout(() => handleSubmit(suggestion), 100);
  };

  // Обработка клика по кнопке отправки с ripple эффектом
  const handleSendClick = () => {
    if (canSubmit) {
      setRippleEffect(true);
      setTimeout(() => setRippleEffect(false), 600);
      handleSubmit();
    }
  };

  const canSubmit = query.trim() && !isLoading;
  const showWarning = showLimitWarning && !isLoading;

  return (
    <VStack spacing={6} w="full" maxW="600px" position="relative">
      {/* Предупреждение о лимите */}
      {showWarning && (
        <MotionBox
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          w="full"
        >
          <Alert status="warning" borderRadius={borderRadius.lg} bg="orange.900" border="1px solid orange.600">
            <AlertIcon color="orange.300" />
            <AlertDescription color="orange.100" flex="1">
              Осталось {remainingRequests} бесплатных запросов.{' '}
              <Text
                as="button"
                color="orange.200"
                fontWeight="bold"
                textDecoration="underline"
                onClick={() => navigate('/register')}
                _hover={{ color: "orange.100" }}
              >
                Зарегистрируйтесь
              </Text>{' '}
              для неограниченного доступа.
            </AlertDescription>
            <CloseButton
              color="orange.300"
              onClick={() => setShowLimitWarning(false)}
              _hover={{ color: "orange.200" }}
            />
          </Alert>
        </MotionBox>
      )}

      {/* Поисковый интерфейс */}
      <MotionBox
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        w="full"
        p={3}
        borderRadius={borderRadius.lg}
        bg={SEARCH_THEME.cardBg}
        border={`1px solid ${SEARCH_THEME.cardBorder}`}
      >
        <VStack spacing={2} align="stretch">
          <HStack spacing={3}>
            <Text minW="88px" fontSize="sm" color={colors.text.secondary}>Режим</Text>
            <Select
              size="sm"
              value={modelMode}
              onChange={(e) => setModelMode(e.target.value)}
              bg={SEARCH_THEME.controlBg}
              borderColor={SEARCH_THEME.controlBorder}
              sx={{ option: SEARCH_THEME.nativeOption }}
            >
              <option value="auto">Auto (рекомендуется)</option>
              <option value="manual">Manual (выбрать модель)</option>
            </Select>
          </HStack>

          {modelMode === 'manual' && (
            <HStack spacing={3}>
              <Text minW="88px" fontSize="sm" color={colors.text.secondary}>Модель</Text>
              {availableModels.length > 0 ? (
                <Select
                  size="sm"
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  isDisabled={isModelsLoading}
                  bg={SEARCH_THEME.controlBg}
                  borderColor={SEARCH_THEME.controlBorder}
                  sx={{ option: SEARCH_THEME.nativeOption }}
                >
                  {availableModels.map((modelId) => (
                    <option key={modelId} value={modelId}>{modelId}</option>
                  ))}
                  <option value="__custom__">Ввести вручную...</option>
                </Select>
              ) : (
                <Input
                  size="sm"
                  value={customModelId}
                  onChange={(e) => setCustomModelId(e.target.value)}
                  placeholder="Например: mws-gpt-alpha"
                  bg={SEARCH_THEME.controlBg}
                  borderColor={SEARCH_THEME.controlBorder}
                />
              )}
            </HStack>
          )}

          {modelMode === 'manual' && selectedModel === '__custom__' && availableModels.length > 0 && (
            <Input
              size="sm"
              value={customModelId}
              onChange={(e) => setCustomModelId(e.target.value)}
              placeholder="Введите model id вручную"
              bg={SEARCH_THEME.controlBg}
              borderColor={SEARCH_THEME.controlBorder}
            />
          )}

          <Text fontSize="xs" color={colors.text.tertiary}>
            Доступно моделей: {availableModels.length}
          </Text>

          {modelMode === 'manual' && (selectedModel || customModelId) && (
            <Text fontSize="xs" color={colors.text.tertiary}>
              Выбрано: {selectedModel === '__custom__' ? customModelId : selectedModel}
            </Text>
          )}
        </VStack>
      </MotionBox>

      <MotionBox
        initial={{ opacity: 0, y: 30, scale: 0.9 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.8, ease: [0.25, 0.46, 0.45, 0.94] }}
        w="full"
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        <MotionBox
          position="relative"
          borderRadius="full"
          p="1px"
          bg={`linear-gradient(135deg, ${colors.brand.primary}20, ${colors.brand.secondary}20, transparent, transparent)`}
          animate={query ? {
            background: `linear-gradient(135deg, ${colors.brand.primary}40, ${colors.brand.secondary}40, ${colors.brand.tertiary}40, ${colors.brand.primary}40)`
          } : {}}
          transition={{ duration: 0.3 }}
          whileFocus={{
            background: `linear-gradient(135deg, ${colors.brand.primary}, ${colors.brand.secondary}, ${colors.brand.tertiary}, ${colors.brand.primary})`,
            boxShadow: `0 0 20px ${colors.brand.primary}40`
          }}
          whileHover={{
            background: `linear-gradient(135deg, ${colors.brand.primary}30, ${colors.brand.secondary}30, ${colors.brand.tertiary}30, ${colors.brand.primary}30)`
          }}
        >
          <InputGroup size="lg" position="relative" bg="transparent">
            <InputLeftElement h="full" display="flex" alignItems="center" justifyContent="center">
              {isLoading ? (
                <Spinner size="sm" color={colors.brand.primary} />
              ) : (
                <Icon
                  as={FiSearch}
                  boxSize={5}
                  color={colors.text.secondary}
                  transition="color 0.2s ease"
                  _hover={{ color: colors.brand.primary }}
                />
              )}
            </InputLeftElement>

            <Input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Спросите что-нибудь..."
              bg={SEARCH_THEME.inputBg}
              border="none"
              borderRadius="full"
              backdropFilter="blur(15px)"
              color={colors.text.primary}
              position="relative"
              zIndex={1}
              _placeholder={{
                color: colors.text.tertiary,
                transition: "color 0.3s ease"
              }}
              _focus={{
                bg: SEARCH_THEME.inputBgFocus,
                boxShadow: "none"
              }}
              _hover={{
                bg: SEARCH_THEME.inputBgHover,
                _placeholder: { color: colors.text.secondary }
              }}
              disabled={isLoading}
              pl={12}
              pr={14}
              fontSize="16px"
              transition="all 0.3s ease"
            />

            <InputRightElement h="full" display="flex" alignItems="center" justifyContent="center">
              <MotionBox
                position="relative"
                display="flex"
                alignItems="center"
                justifyContent="center"
                w={8}
                h={8}
                borderRadius="full"
                bg={canSubmit ? SEARCH_THEME.actionGradientMuted : 'transparent'}
                backdropFilter="blur(10px)"
                animate={canSubmit ? {
                  scale: [1, 1.1, 1],
                  rotate: [0, 5, -5, 0]
                } : {}}
                transition={canSubmit ? {
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut"
                } : { duration: 0.3 }}
                whileHover={canSubmit ? {
                  scale: 1.2,
                  rotate: 15,
                  bg: SEARCH_THEME.actionGradientSoft,
                  boxShadow: `0 0 15px ${colors.brand.primary}50`,
                  transition: { duration: 0.2 }
                } : {}}
                whileTap={canSubmit ? {
                  scale: 0.9,
                  transition: { duration: 0.1 }
                } : {}}
                onClick={handleSendClick}
                style={{ overflow: 'hidden' }}
              >
                <Icon
                  as={FiSend}
                  color={canSubmit ? colors.brand.primary : colors.text.tertiary}
                  cursor={canSubmit ? 'pointer' : 'not-allowed'}
                  boxSize={4}
                  transition="all 0.3s ease"
                />

                {/* Ripple эффект */}
                {rippleEffect && (
                  <MotionBox
                    position="absolute"
                    top="50%"
                    left="50%"
                    w={2}
                    h={2}
                    bg={`${colors.brand.primary}60`}
                    borderRadius="full"
                    initial={{ scale: 0, opacity: 1 }}
                    animate={{ scale: 8, opacity: 0 }}
                    transition={{ duration: 0.6, ease: "easeOut" }}
                    transform="translate(-50%, -50%)"
                  />
                )}
              </MotionBox>
            </InputRightElement>
          </InputGroup>

          {/* Анимированная рамка при фокусе */}
          <MotionBox
            position="absolute"
            top={0}
            left={0}
            right={0}
            bottom={0}
            borderRadius="full"
            border="2px solid transparent"
            bg={SEARCH_THEME.actionGradient}
            opacity={0}
            transform="scale(0.98)"
            transition={{ duration: 0.3 }}
            pointerEvents="none"
            sx={{
              backgroundClip: 'padding-box',
              mask: SEARCH_THEME.focusMask,
              maskComposite: 'exclude',
            }}
          />
        </MotionBox>
      </MotionBox>

      {/* Анимированные подсказки */}
      {showSuggestions && !isLoading && (
        <AnimatedSuggestions
          suggestions={[
            "Что мне сегодня покушать?",
            "Создай календарь питания на неделю",
            "Расскажи о здоровом питании",
            "Как похудеть без диет?",
            "План тренировок для новичка",
            "Рецепты низкокалорийных блюд"
          ]}
          onSuggestionClick={handleSuggestionClick}
        />
      )}

      {/* Индикатор лимитов для гостей */}
      {session && !isLoading && (
        <MotionBox
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 0.5 }}
        >
          <Text
            fontSize="xs"
            color={colors.text.tertiary}
            textAlign="center"
          >
            Осталось {remainingRequests} бесплатных запросов
          </Text>
        </MotionBox>
      )}

      {/* Модальное окно авторизации */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={onAuthModalClose}
        {...modalData}
      />
    </VStack>
  );
}

export default SearchInterface;
