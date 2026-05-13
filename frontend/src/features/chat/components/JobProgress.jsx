import React, { useState } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Progress,
  Icon,
  Button,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  Badge,
  Spinner
} from '@chakra-ui/react';
import {
  FiPlay,
  FiPause,
  FiX,
  FiDownload,
  FiCheckCircle,
  FiXCircle,
  FiAlertCircle,
  FiInfo
} from 'react-icons/fi';
import { motion } from 'framer-motion';
import { colors, borderRadius } from '@theme/tokens';

const MotionBox = motion(Box);

/**
 * JobProgress - Компонент для отображения прогресса выполнения задач
 *
 * Отображает:
 * - Progress bar с процентами
 * - Статус выполнения (processing, completed, failed)
 * - Возможность отмены выполнения
 * - Детали задачи
 * - Результаты выполнения
 */
function JobProgress({ job, onCancel, onDownload, ...props }) {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [isExpanded, setIsExpanded] = useState(false);

  if (!job) return null;

  const getStatusInfo = () => {
    switch (job.status) {
      case 'processing':
        return {
          icon: FiPlay,
          color: colors.brand.primary,
          bgColor: 'rgba(47, 116, 255, 0.1)',
          text: 'Выполняется',
          description: 'Задача обрабатывается...'
        };
      case 'completed':
        return {
          icon: FiCheckCircle,
          color: colors.success,
          bgColor: 'rgba(34, 197, 94, 0.1)',
          text: 'Завершено',
          description: 'Задача выполнена успешно'
        };
      case 'failed':
        return {
          icon: FiXCircle,
          color: colors.error,
          bgColor: 'rgba(239, 68, 68, 0.1)',
          text: 'Ошибка',
          description: 'Произошла ошибка при выполнении'
        };
      case 'cancelled':
        return {
          icon: FiX,
          color: colors.warning,
          bgColor: 'rgba(245, 158, 11, 0.1)',
          text: 'Отменено',
          description: 'Задача была отменена'
        };
      default:
        return {
          icon: FiInfo,
          color: colors.text.tertiary,
          bgColor: 'rgba(255,255,255,0.05)',
          text: 'Неизвестно',
          description: 'Статус неизвестен'
        };
    }
  };

  const statusInfo = getStatusInfo();
  const StatusIcon = statusInfo.icon;
  const progressPercent = Math.min(job.progress || 0, 100);

  // Определяем тип задачи
  const getJobTypeLabel = () => {
    switch (job.type) {
      case 'calendar':
        return 'Генерация календаря питания';
      case 'analysis':
        return 'Анализ данных';
      case 'training':
        return 'Обучение модели';
      case 'processing':
        return 'Обработка данных';
      default:
        return 'Задача';
    }
  };

  return (
    <>
      <MotionBox
        p={3}
        borderRadius={borderRadius.lg}
        bg={statusInfo.bgColor}
        border={`1px solid ${statusInfo.color}30`}
        cursor="pointer"
        onClick={() => setIsExpanded(!isExpanded)}
        _hover={{ bg: `${statusInfo.color}15` }}
        transition="all 0.2s"
        {...props}
      >
        <HStack spacing={3} align="center">
          {/* Status icon */}
          <Box
            p={2}
            borderRadius="full"
            bg={`${statusInfo.color}20`}
            display="flex"
            alignItems="center"
            justifyContent="center"
          >
            {job.status === 'processing' ? (
              <Spinner size="sm" color={statusInfo.color} />
            ) : (
              <Icon as={StatusIcon} color={statusInfo.color} boxSize={4} />
            )}
          </Box>

          {/* Content */}
          <VStack align="start" spacing={1} flex="1">
            <HStack spacing={2}>
              <Text fontSize="sm" fontWeight="medium" color={colors.text.primary}>
                {getJobTypeLabel()}
              </Text>
              <Badge
                size="sm"
                colorScheme={
                  job.status === 'completed' ? 'green' :
                  job.status === 'failed' ? 'red' :
                  job.status === 'processing' ? 'blue' : 'gray'
                }
                fontSize="xs"
              >
                {statusInfo.text}
              </Badge>
            </HStack>

            {/* Progress bar */}
            <Box w="full">
              <HStack justify="space-between" mb={1}>
                <Text fontSize="xs" color={colors.text.tertiary}>
                  {statusInfo.description}
                </Text>
                <Text fontSize="xs" color={colors.text.secondary}>
                  {progressPercent}%
                </Text>
              </HStack>
              <Progress
                value={progressPercent}
                size="sm"
                colorScheme={
                  job.status === 'completed' ? 'green' :
                  job.status === 'failed' ? 'red' : 'blue'
                }
                borderRadius="full"
                bg="rgba(255,255,255,0.1)"
              />
            </Box>
          </VStack>

          {/* Actions */}
          <HStack spacing={1}>
            {job.status === 'processing' && onCancel && (
              <Button
                size="xs"
                variant="ghost"
                color={colors.error}
                _hover={{ bg: 'rgba(239, 68, 68, 0.1)' }}
                onClick={(e) => {
                  e.stopPropagation();
                  onCancel(job.id);
                }}
              >
                <Icon as={FiX} boxSize={3} />
              </Button>
            )}

            {job.status === 'completed' && job.fileUrl && onDownload && (
              <Button
                size="xs"
                variant="ghost"
                color={colors.success}
                _hover={{ bg: 'rgba(34, 197, 94, 0.1)' }}
                onClick={(e) => {
                  e.stopPropagation();
                  onDownload(job.fileUrl);
                }}
              >
                <Icon as={FiDownload} boxSize={3} />
              </Button>
            )}

            <Button
              size="xs"
              variant="ghost"
              color={colors.text.tertiary}
              _hover={{ color: colors.text.primary }}
              onClick={(e) => {
                e.stopPropagation();
                onOpen();
              }}
            >
              <Icon as={FiInfo} boxSize={3} />
            </Button>
          </HStack>
        </HStack>

        {/* Expanded details */}
        {isExpanded && (
          <MotionBox
            mt={3}
            p={3}
            borderRadius={borderRadius.md}
            bg="rgba(0,0,0,0.2)"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            <VStack align="start" spacing={2}>
              <Text fontSize="xs" color={colors.text.secondary}>
                ID задачи: {job.id}
              </Text>
              {job.celeryTaskId && (
                <Text fontSize="xs" color={colors.text.secondary}>
                  Celery ID: {job.celeryTaskId}
                </Text>
              )}
              {job.startedAt && (
                <Text fontSize="xs" color={colors.text.secondary}>
                  Начало: {new Date(job.startedAt).toLocaleString()}
                </Text>
              )}
              {job.completedAt && (
                <Text fontSize="xs" color={colors.text.secondary}>
                  Завершение: {new Date(job.completedAt).toLocaleString()}
                </Text>
              )}
            </VStack>
          </MotionBox>
        )}
      </MotionBox>

      {/* Modal with job details */}
      <JobDetailsModal
        isOpen={isOpen}
        onClose={onClose}
        job={job}
        onCancel={onCancel}
        onDownload={onDownload}
      />
    </>
  );
}

// Модальное окно с деталями задачи
function JobDetailsModal({ isOpen, onClose, job, onCancel, onDownload }) {
  if (!job) return null;

  const getJobDetails = () => {
    switch (job.type) {
      case 'calendar':
        return {
          title: 'Генерация календаря питания',
          description: 'AI анализирует ваши предпочтения и создает персональный план питания',
          steps: [
            'Анализ предпочтений',
            'Расчет калорийности',
            'Генерация рецептов',
            'Создание календаря'
          ]
        };
      case 'analysis':
        return {
          title: 'Анализ данных',
          description: 'AI выполняет статистический анализ предоставленных данных',
          steps: [
            'Валидация данных',
            'Статистический анализ',
            'Генерация отчетов',
            'Визуализация результатов'
          ]
        };
      default:
        return {
          title: 'Обработка данных',
          description: 'AI выполняет обработку данных согласно заданным параметрам',
          steps: ['Подготовка', 'Обработка', 'Анализ', 'Завершение']
        };
    }
  };

  const details = getJobDetails();
  const currentStepIndex = Math.floor((job.progress || 0) / 25); // Предполагаем 4 шага

  return (
    <Modal isOpen={isOpen} onClose={onClose} isCentered size="md">
      <ModalOverlay backdropFilter="blur(8px)" />
      <ModalContent
        bg="rgba(5,5,5,0.95)"
        backdropFilter="blur(20px)"
        border="1px solid rgba(255,255,255,0.1)"
        borderRadius="xl"
      >
        <ModalHeader color={colors.text.primary}>
          {details.title}
        </ModalHeader>
        <ModalCloseButton color={colors.text.secondary} />

        <ModalBody pb={6}>
          <VStack spacing={4} align="stretch">
            <Text color={colors.text.secondary} fontSize="sm">
              {details.description}
            </Text>

            {/* Progress */}
            <Box>
              <HStack justify="space-between" mb={2}>
                <Text fontSize="sm" color={colors.text.primary}>
                  Прогресс выполнения
                </Text>
                <Text fontSize="sm" color={colors.text.secondary}>
                  {job.progress || 0}%
                </Text>
              </HStack>
              <Progress
                value={job.progress || 0}
                size="md"
                colorScheme={
                  job.status === 'completed' ? 'green' :
                  job.status === 'failed' ? 'red' : 'blue'
                }
                borderRadius="full"
                bg="rgba(255,255,255,0.1)"
              />
            </Box>

            {/* Steps */}
            <VStack align="start" spacing={2}>
              <Text fontSize="sm" fontWeight="medium" color={colors.text.primary}>
                Этапы выполнения:
              </Text>
              {details.steps.map((step, index) => (
                <HStack key={index} spacing={3}>
                  <Box
                    w={2}
                    h={2}
                    borderRadius="full"
                    bg={
                      index < currentStepIndex ? colors.success :
                      index === currentStepIndex && job.status === 'processing' ? colors.brand.primary :
                      colors.text.tertiary
                    }
                  />
                  <Text
                    fontSize="sm"
                    color={
                      index <= currentStepIndex ? colors.text.primary : colors.text.tertiary
                    }
                  >
                    {step}
                  </Text>
                </HStack>
              ))}
            </VStack>

            {/* Actions */}
            <HStack spacing={3} justify="flex-end">
              {job.status === 'processing' && onCancel && (
                <Button
                  size="sm"
                  variant="outline"
                  colorScheme="red"
                  onClick={() => onCancel(job.id)}
                >
                  Отменить
                </Button>
              )}

              {job.status === 'completed' && job.fileUrl && onDownload && (
                <Button
                  size="sm"
                  colorScheme="green"
                  onClick={() => onDownload(job.fileUrl)}
                  leftIcon={<Icon as={FiDownload} />}
                >
                  Скачать
                </Button>
              )}

              <Button size="sm" onClick={onClose}>
                Закрыть
              </Button>
            </HStack>
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}

export default JobProgress;
