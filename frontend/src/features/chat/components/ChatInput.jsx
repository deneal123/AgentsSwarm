import React, { useState, useRef, useCallback } from 'react';
import {
  Box,
  VStack,
  HStack,
  Textarea,
  Icon,
  Button,
  Text,
  useToast,
  Progress,
  Image,
  IconButton,
  Tooltip
} from '@chakra-ui/react';
import { MotionBox } from '@ui/motionPrimitives';
import {
  FiSend,
  FiPaperclip,
  FiX,
  FiImage,
  FiFile,
  FiUpload
} from 'react-icons/fi';
import { useChat } from '../context/ChatContext';
import { colors, borderRadius } from '@theme/tokens';

/**
 * ChatInput - Компонент для ввода сообщений в чате
 *
 * Функциональность:
 * - Многострочный ввод с auto-resize
 * - Отправка по Enter (Shift+Enter для новой строки)
 * - Drag & drop для файлов
 * - Preview attachments
 * - Максимальная длина сообщения
 * - Loading состояния
 */
function ChatInput({ placeholder = "Введите сообщение...", maxLength = 2000 }) {
  const [message, setMessage] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  const { sendMessage, uploadFile, attachments, loading, hasAttachments } = useChat();
  const toast = useToast();

  // Auto-resize textarea
  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, []);

  // Обработка изменения текста
  const handleTextChange = (e) => {
    const value = e.target.value;
    if (value.length <= maxLength) {
      setMessage(value);
      adjustTextareaHeight();
    }
  };

  // Обработка клавиш
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Отправка сообщения
  const handleSend = async () => {
    const trimmedMessage = message.trim();

    if (!trimmedMessage && !hasAttachments) return;

    try {
      await sendMessage(trimmedMessage, attachments);
      setMessage('');
      adjustTextareaHeight();

      // Фокус обратно на textarea
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 100);
    } catch (error) {
      console.error('Failed to send message:', error);
      toast({
        title: 'Ошибка отправки',
        description: 'Не удалось отправить сообщение. Попробуйте еще раз.',
        status: 'error',
        duration: 3000,
      });
    }
  };

  // Обработка выбора файлов
  const handleFileSelect = (files) => {
    Array.from(files).forEach(file => {
      if (validateFile(file)) {
        uploadFile(file);
      }
    });
  };

  // Drag & drop обработчики
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files);
    }
  };

  // Валидация файла
  const validateFile = (file) => {
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = [
      'image/jpeg', 'image/png', 'image/gif', 'image/webp',
      'application/pdf', 'text/plain', 'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ];

    if (file.size > maxSize) {
      toast({
        title: 'Файл слишком большой',
        description: 'Максимальный размер файла 10MB',
        status: 'error',
        duration: 3000,
      });
      return false;
    }

    if (!allowedTypes.includes(file.type)) {
      toast({
        title: 'Неподдерживаемый тип файла',
        description: 'Поддерживаются изображения, PDF и текстовые файлы',
        status: 'error',
        duration: 3000,
      });
      return false;
    }

    return true;
  };

  // Открытие выбора файла
  const handleFileButtonClick = () => {
    fileInputRef.current?.click();
  };

  const canSend = (message.trim() || hasAttachments) && !loading;
  const remainingChars = maxLength - message.length;

  return (
    <Box
      p={4}
      borderTop="1px solid rgba(255,255,255,0.1)"
      bg="rgba(0,0,0,0.2)"
      backdropFilter="blur(10px)"
    >
      <VStack spacing={3}>
        {/* Preview attachments */}
        {attachments.length > 0 && (
          <AttachmentPreview attachments={attachments} />
        )}

        {/* Drag & drop overlay */}
        {isDragOver && (
          <MotionBox
            position="absolute"
            inset={0}
            bg={`${colors.brand.primary}20`}
            border={`2px dashed ${colors.brand.primary}`}
            borderRadius={borderRadius.lg}
            display="flex"
            alignItems="center"
            justifyContent="center"
            zIndex={10}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <VStack spacing={2}>
              <Icon as={FiUpload} size={24} color={colors.brand.primary} />
              <Text color={colors.brand.primary} fontWeight={500}>
                Перетащите файлы сюда
              </Text>
            </VStack>
          </MotionBox>
        )}

        {/* Input area */}
        <Box
          w="full"
          position="relative"
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <HStack spacing={3} align="flex-end">
            {/* File button */}
            <Tooltip label="Прикрепить файл">
              <IconButton
                icon={<FiPaperclip />}
                size="sm"
                variant="ghost"
                color={colors.text.secondary}
                _hover={{ color: colors.brand.primary, bg: 'rgba(255,255,255,0.1)' }}
                onClick={handleFileButtonClick}
                isDisabled={loading}
                aria-label="Прикрепить файл"
              />
            </Tooltip>

            {/* Text input */}
            <Box flex="1" position="relative">
              <Textarea
                ref={textareaRef}
                value={message}
                onChange={handleTextChange}
                onKeyPress={handleKeyPress}
                placeholder={placeholder}
                minH="44px"
                maxH="120px"
                resize="none"
                border="1px solid rgba(255,255,255,0.2)"
                borderRadius={borderRadius.lg}
                bg="rgba(255,255,255,0.05)"
                color={colors.text.primary}
                _placeholder={{ color: colors.text.tertiary }}
                _focus={{
                  borderColor: colors.brand.primary,
                  bg: "rgba(255,255,255,0.08)",
                  boxShadow: `0 0 0 1px ${colors.brand.primary}40`
                }}
                _hover={{
                  borderColor: "rgba(255,255,255,0.3)"
                }}
                disabled={loading}
                fontSize="14px"
                lineHeight="1.4"
                pr={12}
              />

              {/* Character counter */}
              {message.length > maxLength * 0.8 && (
                <Text
                  position="absolute"
                  bottom={2}
                  right={3}
                  fontSize="xs"
                  color={remainingChars < 0 ? colors.error : colors.text.tertiary}
                >
                  {remainingChars}
                </Text>
              )}
            </Box>

            {/* Send button */}
            <Tooltip label="Отправить (Enter)">
              <IconButton
                icon={<FiSend />}
                colorScheme="brand"
                size="sm"
                isDisabled={!canSend}
                onClick={handleSend}
                aria-label="Отправить сообщение"
                _hover={{
                  transform: 'scale(1.05)',
                  bg: colors.brand.primary
                }}
                transition="all 0.2s"
              />
            </Tooltip>
          </HStack>
        </Box>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*,.pdf,.txt,.doc,.docx"
          style={{ display: 'none' }}
          onChange={(e) => handleFileSelect(e.target.files)}
        />
      </VStack>
    </Box>
  );
}

// Компонент для preview attachments
function AttachmentPreview({ attachments }) {
  return (
    <HStack spacing={3} overflowX="auto" pb={2}>
      {attachments.map((attachment) => (
        <AttachmentItem key={attachment.id} attachment={attachment} />
      ))}
    </HStack>
  );
}

// Компонент для отдельного attachment
function AttachmentItem({ attachment }) {
  const { removeAttachment } = useChat();
  const isImage = attachment.type?.startsWith('image/');

  return (
    <MotionBox
      position="relative"
      minW="80px"
      maxW="120px"
      borderRadius={borderRadius.md}
      overflow="hidden"
      border="1px solid rgba(255,255,255,0.2)"
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
    >
      {isImage && attachment.url ? (
        <Image
          src={attachment.url}
          alt={attachment.name}
          w="full"
          h="60px"
          objectFit="cover"
        />
      ) : (
        <Box
          w="full"
          h="60px"
          bg="rgba(255,255,255,0.05)"
          display="flex"
          alignItems="center"
          justifyContent="center"
        >
          <Icon
            as={attachment.type?.includes('pdf') ? FiFile : FiImage}
            size={20}
            color={colors.text.secondary}
          />
        </Box>
      )}

      {/* Remove button */}
      <IconButton
        icon={<FiX />}
        size="xs"
        position="absolute"
        top={1}
        right={1}
        bg="rgba(0,0,0,0.7)"
        color={colors.text.primary}
        borderRadius="full"
        _hover={{ bg: "rgba(0,0,0,0.9)" }}
        onClick={() => removeAttachment(attachment.id)}
        aria-label="Удалить файл"
      />

      {/* File name */}
      <Box p={2} bg="rgba(0,0,0,0.8)">
        <Text
          fontSize="xs"
          color={colors.text.secondary}
          noOfLines={1}
          title={attachment.name}
        >
          {attachment.name}
        </Text>
      </Box>
    </MotionBox>
  );
}

export default ChatInput;
