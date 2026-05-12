import React, { useState } from 'react';
import {
  Box,
  Text,
  VStack,
  HStack,
  Icon,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  useToast,
  Tooltip,
  Badge,
  Image,
  Link
} from '@chakra-ui/react';
import { motion } from 'framer-motion';

const MotionBox = motion(Box);
import {
  FiCopy,
  FiMoreVertical,
  FiCheck,
  FiCheckCheck,
  FiClock,
  FiX,
  FiDownload,
  FiExternalLink
} from 'react-icons/fi';
import { formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';
import { colors, borderRadius } from '@theme/tokens';
import MessageRenderer from './MessageRenderer';

/**
 * MessageBubble - Компонент для отображения отдельного сообщения в чате
 *
 * Поддерживает:
 * - Разные типы сообщений (user, agent, system, error)
 * - Статусы отправки
 * - Attachments (изображения, документы)
 * - Markdown форматирование
 * - Контекстное меню
 * - Copy to clipboard
 */
function MessageBubble({
  message,
  isOwn = false,
  showAvatar = true,
  showTimestamp = true,
  onRetry,
  onDelete,
  ...props
}) {
  const [showMenu, setShowMenu] = useState(false);
  const toast = useToast();

  // Определение стиля сообщения по типу
  const getMessageStyle = () => {
    switch (message.type) {
      case 'user':
        return {
          bg: `linear-gradient(135deg, ${colors.brand.primary}20, ${colors.brand.secondary}20)`,
          borderColor: colors.brand.primary,
          alignSelf: 'flex-end',
          textAlign: 'right'
        };

      case 'agent':
        return {
          bg: 'rgba(255,255,255,0.05)',
          borderColor: 'rgba(255,255,255,0.1)',
          alignSelf: 'flex-start',
          textAlign: 'left'
        };

      case 'system':
        return {
          bg: 'rgba(255,255,255,0.02)',
          borderColor: 'rgba(255,255,255,0.05)',
          alignSelf: 'center',
          textAlign: 'center',
          fontSize: 'sm',
          opacity: 0.7
        };

      case 'error':
        return {
          bg: 'rgba(255,0,0,0.1)',
          borderColor: 'rgba(255,0,0,0.3)',
          alignSelf: 'center',
          textAlign: 'center'
        };

      default:
        return {
          bg: 'rgba(255,255,255,0.05)',
          borderColor: 'rgba(255,255,255,0.1)',
          alignSelf: 'flex-start'
        };
    }
  };

  // Получение иконки статуса
  const getStatusIcon = () => {
    if (!message.status) return null;

    switch (message.status) {
      case 'sending':
        return <FiClock size={12} color={colors.text.tertiary} />;
      case 'sent':
        return <FiCheck size={12} color={colors.brand.primary} />;
      case 'delivered':
        return <FiCheckCheck size={12} color={colors.brand.primary} />;
      case 'failed':
        return <FiX size={12} color={colors.error} />;
      default:
        return null;
    }
  };

  // Форматирование времени
  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    try {
      const date = new Date(timestamp);
      return formatDistanceToNow(date, {
        addSuffix: true,
        locale: ru
      });
    } catch {
      return '';
    }
  };

  // Копирование сообщения в буфер обмена
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      toast({
        title: 'Скопировано',
        description: 'Сообщение скопировано в буфер обмена',
        status: 'success',
        duration: 2000,
      });
    } catch (error) {
      toast({
        title: 'Ошибка',
        description: 'Не удалось скопировать сообщение',
        status: 'error',
        duration: 3000,
      });
    }
  };

  // Рендер attachments
  const renderAttachments = () => {
    if (!message.attachments || message.attachments.length === 0) return null;

    return (
      <VStack spacing={2} align="stretch" mt={2}>
        {message.attachments.map((attachment, index) => (
          <AttachmentItem key={attachment.id || index} attachment={attachment} />
        ))}
      </VStack>
    );
  };

  // Рендер содержимого сообщения
  const renderContent = () => {
    if (!message.content && !message.isTyping) return null;

    return (
      <MessageRenderer
        content={message.content}
        isTyping={message.isTyping}
        typingProgress={message.typingProgress}
        messageType={message.type}
      />
    );
  };

  const messageStyle = getMessageStyle();
  const isSystem = message.type === 'system';
  const isError = message.type === 'error';

  return (
    <MotionBox
      initial={{
        opacity: 0,
        y: 20,
        scale: 0.9,
        rotateX: 15
      }}
      animate={{
        opacity: 1,
        y: 0,
        scale: 1,
        rotateX: 0
      }}
      transition={{
        type: "spring",
        stiffness: 300,
        damping: 25,
        duration: 0.4
      }}
      whileHover={{
        scale: 1.02,
        transition: { duration: 0.2 }
      }}
      maxW={{ base: '85%', md: '70%' }}
      minW={{ base: 'auto', md: '200px' }}
      {...messageStyle}
      {...props}
    >
      <Box
        p={3}
        borderRadius={borderRadius.lg}
        border="1px solid"
        position="relative"
        onMouseEnter={() => setShowMenu(true)}
        onMouseLeave={() => setShowMenu(false)}
      >
        {/* Основное содержимое */}
        <VStack align={messageStyle.textAlign} spacing={2}>
          {renderContent()}
          {renderAttachments()}
        </VStack>

        {/* Footer с временем и статусом */}
        {(showTimestamp || message.status) && (
          <HStack
            justify={messageStyle.alignSelf === 'flex-end' ? 'flex-end' : 'flex-start'}
            mt={2}
            spacing={2}
            opacity={0.7}
          >
            {showTimestamp && (
              <Text fontSize="xs" color={colors.text.tertiary}>
                {formatTime(message.timestamp)}
              </Text>
            )}

            {message.status && (
              <Box display="flex" alignItems="center">
                {getStatusIcon()}
              </Box>
            )}
          </HStack>
        )}

        {/* Контекстное меню */}
        {showMenu && message.type !== 'system' && (
          <Box position="absolute" top={2} right={2}>
            <Menu>
              <MenuButton
                as={Box}
                cursor="pointer"
                p={1}
                borderRadius="full"
                _hover={{ bg: 'rgba(255,255,255,0.1)' }}
              >
                <Icon as={FiMoreVertical} size={14} color={colors.text.tertiary} />
              </MenuButton>
              <MenuList bg="rgba(0,0,0,0.9)" border="1px solid rgba(255,255,255,0.1)">
                <MenuItem
                  onClick={handleCopy}
                  icon={<FiCopy size={16} />}
                  _hover={{ bg: 'rgba(255,255,255,0.1)' }}
                >
                  Копировать
                </MenuItem>
                {message.status === 'failed' && onRetry && (
                  <MenuItem
                    onClick={() => onRetry(message)}
                    icon={<FiClock size={16} />}
                    _hover={{ bg: 'rgba(255,255,255,0.1)' }}
                  >
                    Повторить отправку
                  </MenuItem>
                )}
                {onDelete && (
                  <MenuItem
                    onClick={() => onDelete(message.id)}
                    icon={<FiX size={16} />}
                    color={colors.error}
                    _hover={{ bg: 'rgba(255,0,0,0.1)' }}
                  >
                    Удалить
                  </MenuItem>
                )}
              </MenuList>
            </Menu>
          </Box>
        )}

        {/* Error badge */}
        {isError && (
          <Badge
            position="absolute"
            top={-2}
            right={-2}
            colorScheme="red"
            fontSize="xs"
            borderRadius="full"
          >
            !
          </Badge>
        )}
      </Box>
    </MotionBox>
  );
}

// Компонент для отображения attachment
function AttachmentItem({ attachment }) {
  const isImage = attachment.type?.startsWith('image/');
  const fileName = attachment.name || 'Файл';
  const fileSize = attachment.size ? formatFileSize(attachment.size) : '';

  if (isImage && attachment.url) {
    return (
      <Box
        borderRadius={borderRadius.md}
        overflow="hidden"
        border="1px solid rgba(255,255,255,0.1)"
        maxW="300px"
      >
        <Image
          src={attachment.url}
          alt={fileName}
          w="full"
          h="auto"
          objectFit="cover"
          loading="lazy"
        />
        <HStack p={2} bg="rgba(0,0,0,0.5)" justify="space-between">
          <Text fontSize="xs" color={colors.text.secondary} noOfLines={1}>
            {fileName}
          </Text>
          {fileSize && (
            <Text fontSize="xs" color={colors.text.tertiary}>
              {fileSize}
            </Text>
          )}
        </HStack>
      </Box>
    );
  }

  return (
    <HStack
      p={3}
      bg="rgba(255,255,255,0.05)"
      borderRadius={borderRadius.md}
      border="1px solid rgba(255,255,255,0.1)"
      justify="space-between"
      w="full"
    >
      <VStack align="start" spacing={0} flex="1">
        <Text fontSize="sm" color={colors.text.primary} noOfLines={1}>
          {fileName}
        </Text>
        {fileSize && (
          <Text fontSize="xs" color={colors.text.tertiary}>
            {fileSize}
          </Text>
        )}
      </VStack>

      {attachment.url && (
        <Link href={attachment.url} isExternal>
          <Icon
            as={attachment.downloaded ? FiCheck : FiDownload}
            size={16}
            color={colors.brand.primary}
            cursor="pointer"
            _hover={{ color: colors.brand.secondary }}
          />
        </Link>
      )}
    </HStack>
  );
}

// Вспомогательная функция для форматирования размера файла
function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export default MessageBubble;
