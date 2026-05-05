import React from 'react';
import { VStack, Box, Text, HStack } from '@chakra-ui/react';
import { colors } from '@theme/tokens';
import MessageBubble from './MessageBubble';

/**
 * MessageGroup - Группировка сообщений по отправителю и времени
 *
 * Группирует последовательные сообщения от одного отправителя
 * в компактные блоки с оптимизацией пространства
 */
function MessageGroup({ messages, showAvatar = true, onRetryMessage, onDeleteMessage }) {
  if (!messages || messages.length === 0) return null;

  const sender = messages[0].type;
  const isUser = sender === 'user';
  const isSystem = sender === 'system';

  // Группировка сообщений: объединяем близкие по времени
  const groupedMessages = groupMessagesByTime(messages);

  return (
    <VStack spacing={1} align={isUser ? 'flex-end' : 'flex-start'} maxW="80%">
      {groupedMessages.map((group, groupIndex) => (
        <MessageGroupBlock
          key={`group-${groupIndex}`}
          messages={group.messages}
          timestamp={group.timestamp}
          isUser={isUser}
          isSystem={isSystem}
          showAvatar={showAvatar && groupIndex === 0} // Avatar только у первой группы
          onRetryMessage={onRetryMessage}
          onDeleteMessage={onDeleteMessage}
        />
      ))}
    </VStack>
  );
}

// Компонент для блока сгруппированных сообщений
function MessageGroupBlock({
  messages,
  timestamp,
  isUser,
  isSystem,
  showAvatar,
  onRetryMessage,
  onDeleteMessage
}) {
  return (
    <Box
      display="flex"
      flexDirection={isUser ? 'row-reverse' : 'row'}
      alignItems="flex-end"
      gap={2}
      maxW="100%"
    >
      {/* Avatar (только для первой группы) */}
      {showAvatar && !isSystem && (
        <Box
          flexShrink={0}
          w={8}
          h={8}
          borderRadius="full"
          bg={isUser ? colors.brand.primary : colors.brand.secondary}
          display="flex"
          alignItems="center"
          justifyContent="center"
        >
          <Text fontSize="xs" fontWeight="bold" color="white">
            {isUser ? 'Вы' : 'AI'}
          </Text>
        </Box>
      )}

      {/* Сообщения */}
      <VStack spacing={1} align={isUser ? 'flex-end' : 'flex-start'} maxW="calc(100% - 40px)">
        {messages.map((message, index) => (
          <MessageBubble
            key={message.id}
            message={message}
            isOwn={isUser}
            showAvatar={false} // Avatar уже показан на уровне группы
            showTimestamp={index === messages.length - 1} // Время только у последнего сообщения
            onRetry={onRetryMessage}
            onDelete={onDeleteMessage}
          />
        ))}

        {/* Timestamp для группы */}
        {timestamp && (
          <Text
            fontSize="xs"
            color={colors.text.tertiary}
            alignSelf={isUser ? 'flex-end' : 'flex-start'}
            mt={1}
          >
            {formatTimestamp(timestamp)}
          </Text>
        )}
      </VStack>
    </Box>
  );
}

/**
 * Группирует сообщения по времени (сообщения в течение 5 минут считаются одной группой)
 */
function groupMessagesByTime(messages) {
  if (!messages || messages.length === 0) return [];

  const groups = [];
  let currentGroup = {
    messages: [messages[0]],
    timestamp: messages[0].timestamp
  };

  for (let i = 1; i < messages.length; i++) {
    const currentMessage = messages[i];
    const lastMessageInGroup = currentGroup.messages[currentGroup.messages.length - 1];

    // Проверяем, можно ли добавить сообщение в текущую группу
    const timeDiff = new Date(currentMessage.timestamp) - new Date(lastMessageInGroup.timestamp);
    const isWithinTimeWindow = timeDiff < 5 * 60 * 1000; // 5 минут

    if (isWithinTimeWindow) {
      // Добавляем в текущую группу
      currentGroup.messages.push(currentMessage);
    } else {
      // Создаем новую группу
      groups.push(currentGroup);
      currentGroup = {
        messages: [currentMessage],
        timestamp: currentMessage.timestamp
      };
    }
  }

  // Добавляем последнюю группу
  groups.push(currentGroup);

  return groups;
}

/**
 * Форматирует timestamp для отображения
 */
function formatTimestamp(timestamp) {
  if (!timestamp) return '';

  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMinutes < 1) {
      return 'только что';
    } else if (diffMinutes < 60) {
      return `${diffMinutes} мин назад`;
    } else if (diffHours < 24) {
      return `${diffHours} ч назад`;
    } else if (diffDays < 7) {
      return `${diffDays} д назад`;
    } else {
      return date.toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
      });
    }
  } catch {
    return '';
  }
}

export default MessageGroup;
