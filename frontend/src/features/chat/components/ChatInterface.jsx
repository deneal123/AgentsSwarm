import React from 'react';
import { Box, VStack, HStack, Text, Icon, Button, useToast } from '@chakra-ui/react';
import { FiX, FiMinimize2, FiMaximize2 } from 'react-icons/fi';
import { ChatProvider } from '../context/ChatContext';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import { colors, borderRadius } from '@theme/tokens';

/**
 * ChatInterface - Полноценный интерфейс чата с AI агентом
 *
 * Архитектура:
 * - ChatProvider для управления состоянием
 * - ChatMessages для отображения сообщений с виртуализацией
 * - ChatInput для ввода сообщений и attachments
 * - Header с управлением окном
 */
function ChatInterface({ threadId, onClose, isMinimized = false, onToggleMinimize }) {
  return (
    <ChatProvider threadId={threadId}>
      <ChatInterfaceContent
        threadId={threadId}
        onClose={onClose}
        isMinimized={isMinimized}
        onToggleMinimize={onToggleMinimize}
      />
    </ChatProvider>
  );
}

// Внутренний компонент с доступом к контексту
function ChatInterfaceContent({ threadId, onClose, isMinimized, onToggleMinimize }) {
  const { connectionState, error, clearMessages } = useChat();
  const toast = useToast();

  // Обработка повторной отправки сообщения
  const handleRetryMessage = async (message) => {
    // Реализация будет добавлена позже
    console.log('Retry message:', message);
  };

  // Обработка удаления сообщения
  const handleDeleteMessage = async (messageId) => {
    // Реализация будет добавлена позже
    console.log('Delete message:', messageId);
  };

  // Очистка чата
  const handleClearChat = () => {
    clearMessages();
    toast({
      title: 'Чат очищен',
      description: 'Все сообщения удалены',
      status: 'success',
      duration: 2000,
    });
  };

  if (isMinimized) {
    return (
      <MinimizedChatHeader
        threadId={threadId}
        connectionState={connectionState}
        onToggleMinimize={onToggleMinimize}
        onClose={onClose}
      />
    );
  }

  return (
    <Box
      h="600px"
      w="full"
      maxW="800px"
      borderRadius="xl"
      bg="rgba(5,5,5,0.95)"
      backdropFilter="blur(20px)"
      border="1px solid rgba(255,255,255,0.1)"
      overflow="hidden"
      display="flex"
      flexDirection="column"
      boxShadow={`0 25px 50px rgba(0,0,0,0.5), 0 0 0 1px ${colors.brand.primary}20`}
    >
      {/* Header */}
      <ChatHeader
        threadId={threadId}
        connectionState={connectionState}
        onToggleMinimize={onToggleMinimize}
        onClearChat={handleClearChat}
        onClose={onClose}
      />

      {/* Error banner */}
      {error && (
        <Box p={3} bg="rgba(255,0,0,0.1)" borderBottom="1px solid rgba(255,0,0,0.2)">
          <Text fontSize="sm" color={colors.error}>
            {error}
          </Text>
        </Box>
      )}

      {/* Messages area */}
      <Box flex="1" overflow="hidden">
        <ChatMessages
          onRetryMessage={handleRetryMessage}
          onDeleteMessage={handleDeleteMessage}
        />
      </Box>

      {/* Input area */}
      <ChatInput />
    </Box>
  );
}

// Компонент header'а чата
function ChatHeader({ threadId, connectionState, onToggleMinimize, onClearChat, onClose }) {
  const getConnectionStatus = () => {
    switch (connectionState) {
      case 'connected':
        return { text: 'Подключено', color: colors.success };
      case 'connecting':
        return { text: 'Подключение...', color: colors.warning };
      case 'disconnected':
        return { text: 'Отключено', color: colors.error };
      default:
        return { text: 'Неизвестно', color: colors.text.tertiary };
    }
  };

  const status = getConnectionStatus();

  return (
    <HStack
      p={4}
      borderBottom="1px solid rgba(255,255,255,0.1)"
      bg="rgba(255,255,255,0.02)"
      justify="space-between"
    >
      <VStack align="start" spacing={0}>
        <Text fontSize="lg" fontWeight="bold" color={colors.text.primary}>
          AI Агент
        </Text>
        <HStack spacing={2}>
          <Box
            w={2}
            h={2}
            borderRadius="full"
            bg={status.color}
          />
          <Text fontSize="xs" color={colors.text.tertiary}>
            {status.text}
          </Text>
        </HStack>
      </VStack>

      <HStack spacing={1}>
        <Button
          size="sm"
          variant="ghost"
          color={colors.text.secondary}
          _hover={{ color: colors.text.primary, bg: 'rgba(255,255,255,0.1)' }}
          onClick={onClearChat}
          leftIcon={<Icon as={FiX} />}
        >
          Очистить
        </Button>

        <Button
          size="sm"
          variant="ghost"
          color={colors.text.secondary}
          _hover={{ color: colors.text.primary, bg: 'rgba(255,255,255,0.1)' }}
          onClick={onToggleMinimize}
          leftIcon={<Icon as={FiMinimize2} />}
        >
          Свернуть
        </Button>

        <Button
          size="sm"
          variant="ghost"
          color={colors.text.secondary}
          _hover={{ color: colors.error, bg: 'rgba(255,0,0,0.1)' }}
          onClick={onClose}
          leftIcon={<Icon as={FiX} />}
        >
          Закрыть
        </Button>
      </HStack>
    </HStack>
  );
}

// Компонент свернутого чата
function MinimizedChatHeader({ threadId, connectionState, onToggleMinimize, onClose }) {
  return (
    <HStack
      p={3}
      borderRadius={borderRadius.lg}
      bg="rgba(5,5,5,0.9)"
      backdropFilter="blur(10px)"
      border="1px solid rgba(255,255,255,0.1)"
      justify="space-between"
      w="full"
      maxW="400px"
      cursor="pointer"
      onClick={onToggleMinimize}
      _hover={{ bg: 'rgba(5,5,5,0.95)' }}
      transition="all 0.2s"
    >
      <HStack spacing={3}>
        <Box
          w={8}
          h={8}
          borderRadius="full"
          bg={`linear-gradient(135deg, ${colors.brand.primary}, ${colors.brand.secondary})`}
          display="flex"
          alignItems="center"
          justifyContent="center"
        >
          <Text fontSize="sm" fontWeight="bold" color="white">
            AI
          </Text>
        </Box>

        <VStack align="start" spacing={0}>
          <Text fontSize="sm" fontWeight="medium" color={colors.text.primary}>
            AI Агент
          </Text>
          <Text fontSize="xs" color={colors.text.tertiary}>
            Нажмите для развертывания
          </Text>
        </VStack>
      </HStack>

      <Button
        size="xs"
        variant="ghost"
        color={colors.text.secondary}
        _hover={{ color: colors.error }}
        onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}
      >
        <Icon as={FiX} />
      </Button>
    </HStack>
  );
}

export default ChatInterface;
