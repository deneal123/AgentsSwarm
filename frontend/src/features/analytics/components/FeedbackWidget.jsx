import React, { useState, useCallback } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Textarea,
  Button,
  Icon,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  useToast,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  Radio,
  RadioGroup,
  Checkbox,
  FormControl,
  FormLabel,
  Input
} from '@chakra-ui/react';
import {
  FiMessageSquare,
  FiThumbsUp,
  FiThumbsDown,
  FiStar,
  FiSend,
  FiSmile,
  FiMeh,
  FiFrown
} from 'react-icons/fi';
import { useAnalytics } from '../context/AnalyticsContext';

/**
 * FeedbackWidget - Виджет для сбора обратной связи от пользователей
 *
 * Поддерживает:
 * - Рейтинги и оценки
 * - Текстовые отзывы
 * - Категории фидбека
 * - Анонимные отзывы
 * - Follow-up вопросы
 */
function FeedbackWidget({
  trigger = 'button',
  context = 'general',
  title = 'Обратная связь',
  placeholder = 'Расскажите, что вы думаете...'
}) {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { trackEvent } = useAnalytics();
  const toast = useToast();

  const [feedback, setFeedback] = useState({
    rating: 5,
    category: 'general',
    message: '',
    email: '',
    allowFollowUp: true,
    submitted: false
  });

  // Категории фидбека
  const categories = [
    { value: 'general', label: 'Общее впечатление', icon: FiMessageSquare },
    { value: 'bug', label: 'Ошибка', icon: FiFrown },
    { value: 'feature', label: 'Предложение функции', icon: FiStar },
    { value: 'performance', label: 'Производительность', icon: FiMeh },
    { value: 'design', label: 'Дизайн', icon: FiSmile },
  ];

  // Обработка отправки фидбека
  const handleSubmit = useCallback(async () => {
    if (!feedback.message.trim()) {
      toast({
        title: 'Введите сообщение',
        description: 'Пожалуйста, напишите ваш отзыв',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    try {
      // Отправка аналитики
      trackEvent('feedback_submitted', {
        context,
        rating: feedback.rating,
        category: feedback.category,
        messageLength: feedback.message.length,
        allowFollowUp: feedback.allowFollowUp,
        hasEmail: !!feedback.email.trim(),
      });

      // Имитация отправки на сервер
      await new Promise(resolve => setTimeout(resolve, 1000));

      setFeedback(prev => ({ ...prev, submitted: true }));

      toast({
        title: 'Спасибо за отзыв!',
        description: 'Ваша обратная связь очень важна для нас',
        status: 'success',
        duration: 5000,
      });

      // Закрыть через 2 секунды
      setTimeout(() => {
        onClose();
        // Сброс состояния
        setFeedback({
          rating: 5,
          category: 'general',
          message: '',
          email: '',
          allowFollowUp: true,
          submitted: false
        });
      }, 2000);

    } catch (error) {
      console.error('Failed to submit feedback:', error);
      toast({
        title: 'Ошибка отправки',
        description: 'Не удалось отправить отзыв. Попробуйте еще раз.',
        status: 'error',
        duration: 5000,
      });
    }
  }, [feedback, context, trackEvent, toast, onClose]);

  // Trigger компоненты
  const renderTrigger = () => {
    switch (trigger) {
      case 'floating':
        return (
          <Box
            position="fixed"
            bottom={6}
            right={6}
            zIndex={1000}
          >
            <Button
              onClick={onOpen}
              colorScheme="brand"
              borderRadius="full"
              size="lg"
              shadow="lg"
              leftIcon={<FiMessageSquare />}
              _hover={{ transform: 'scale(1.05)' }}
              transition="all 0.2s"
            >
              Обратная связь
            </Button>
          </Box>
        );

      case 'thumbs':
        return (
          <HStack spacing={2}>
            <Button
              size="sm"
              variant="ghost"
              color="green.400"
              onClick={() => {
                setFeedback(prev => ({ ...prev, rating: 5, category: 'positive' }));
                onOpen();
              }}
              leftIcon={<FiThumbsUp />}
            >
              Полезно
            </Button>
            <Button
              size="sm"
              variant="ghost"
              color="red.400"
              onClick={() => {
                setFeedback(prev => ({ ...prev, rating: 2, category: 'negative' }));
                onOpen();
              }}
              leftIcon={<FiThumbsDown />}
            >
              Не очень
            </Button>
          </HStack>
        );

      default:
        return (
          <Button
            onClick={onOpen}
            variant="outline"
            size="sm"
            leftIcon={<FiMessageSquare />}
          >
            Обратная связь
          </Button>
        );
    }
  };

  return (
    <>
      {renderTrigger()}

      <Modal isOpen={isOpen} onClose={onClose} isCentered size="lg">
        <ModalOverlay backdropFilter="blur(8px)" />
        <ModalContent
          bg="rgba(5,5,5,0.95)"
          backdropFilter="blur(20px)"
          border="1px solid rgba(255,255,255,0.1)"
          borderRadius="xl"
        >
          <ModalHeader color="white">
            <HStack spacing={3}>
              <Icon as={FiMessageSquare} color="brand.primary" />
              <Text>{title}</Text>
            </HStack>
          </ModalHeader>

          <ModalCloseButton color="gray.400" />

          <ModalBody pb={6}>
            {!feedback.submitted ? (
              <VStack spacing={6} align="stretch">
                {/* Рейтинг */}
                <VStack spacing={3} align="center">
                  <Text fontSize="sm" color="gray.300">
                    Как бы вы оценили этот опыт?
                  </Text>
                  <HStack spacing={4}>
                    {[1, 2, 3, 4, 5].map((star) => (
                      <Icon
                        key={star}
                        as={FiStar}
                        size={24}
                        color={star <= feedback.rating ? "yellow.400" : "gray.500"}
                        cursor="pointer"
                        onClick={() => setFeedback(prev => ({ ...prev, rating: star }))}
                        _hover={{ color: "yellow.300" }}
                        transition="color 0.2s"
                      />
                    ))}
                  </HStack>
                  <Text fontSize="xs" color="gray.400">
                    {feedback.rating === 1 && "Очень плохо"}
                    {feedback.rating === 2 && "Плохо"}
                    {feedback.rating === 3 && "Нормально"}
                    {feedback.rating === 4 && "Хорошо"}
                    {feedback.rating === 5 && "Отлично"}
                  </Text>
                </VStack>

                {/* Категория */}
                <FormControl>
                  <FormLabel fontSize="sm" color="gray.300">
                    Категория отзыва
                  </FormLabel>
                  <RadioGroup
                    value={feedback.category}
                    onChange={(value) => setFeedback(prev => ({ ...prev, category: value }))}
                  >
                    <VStack spacing={2} align="start">
                      {categories.map((category) => {
                        const IconComponent = category.icon;
                        return (
                          <Radio
                            key={category.value}
                            value={category.value}
                            colorScheme="brand"
                            size="sm"
                          >
                            <HStack spacing={2}>
                              <IconComponent size={16} />
                              <Text fontSize="sm">{category.label}</Text>
                            </HStack>
                          </Radio>
                        );
                      })}
                    </VStack>
                  </RadioGroup>
                </FormControl>

                {/* Сообщение */}
                <FormControl>
                  <FormLabel fontSize="sm" color="gray.300">
                    Ваш отзыв
                  </FormLabel>
                  <Textarea
                    value={feedback.message}
                    onChange={(e) => setFeedback(prev => ({ ...prev, message: e.target.value }))}
                    placeholder={placeholder}
                    rows={4}
                    bg="rgba(255,255,255,0.05)"
                    border="1px solid rgba(255,255,255,0.1)"
                    _focus={{
                      borderColor: 'brand.primary',
                      bg: "rgba(255,255,255,0.08)"
                    }}
                    resize="vertical"
                  />
                  <Text fontSize="xs" color="gray.400" mt={1}>
                    {feedback.message.length}/1000 символов
                  </Text>
                </FormControl>

                {/* Email для follow-up */}
                <FormControl>
                  <FormLabel fontSize="sm" color="gray.300">
                    Email (опционально, для связи)
                  </FormLabel>
                  <Input
                    type="email"
                    value={feedback.email}
                    onChange={(e) => setFeedback(prev => ({ ...prev, email: e.target.value }))}
                    placeholder="your.email@example.com"
                    bg="rgba(255,255,255,0.05)"
                    border="1px solid rgba(255,255,255,0.1)"
                    _focus={{
                      borderColor: 'brand.primary',
                      bg: "rgba(255,255,255,0.08)"
                    }}
                  />
                </FormControl>

                {/* Follow-up согласие */}
                <Checkbox
                  isChecked={feedback.allowFollowUp}
                  onChange={(e) => setFeedback(prev => ({ ...prev, allowFollowUp: e.target.checked }))}
                  colorScheme="brand"
                  size="sm"
                >
                  <Text fontSize="xs" color="gray.300">
                    Я согласен на получение follow-up вопросов по этому отзыву
                  </Text>
                </Checkbox>

                {/* Кнопки */}
                <HStack spacing={3} justify="flex-end" pt={2}>
                  <Button variant="ghost" onClick={onClose} size="sm">
                    Отмена
                  </Button>
                  <Button
                    colorScheme="brand"
                    onClick={handleSubmit}
                    isDisabled={!feedback.message.trim()}
                    leftIcon={<FiSend />}
                    size="sm"
                  >
                    Отправить
                  </Button>
                </HStack>
              </VStack>
            ) : (
              // Success state
              <VStack spacing={4} align="center" py={8}>
                <Icon as={FiThumbsUp} size={48} color="green.400" />
                <Text fontSize="lg" color="white" textAlign="center">
                  Спасибо за ваш отзыв!
                </Text>
                <Text fontSize="sm" color="gray.300" textAlign="center">
                  Ваша обратная связь помогает нам становиться лучше
                </Text>
              </VStack>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
}

// Preset компоненты для разных контекстов
export function InlineFeedback({ context, ...props }) {
  return (
    <FeedbackWidget
      trigger="thumbs"
      context={context}
      title="Быстрая оценка"
      placeholder="Что можно улучшить?"
      {...props}
    />
  );
}

export function FloatingFeedback({ context, ...props }) {
  return (
    <FeedbackWidget
      trigger="floating"
      context={context}
      {...props}
    />
  );
}

export default FeedbackWidget;
