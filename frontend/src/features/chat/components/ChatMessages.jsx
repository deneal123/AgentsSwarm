import React, { memo, useRef, useEffect, useMemo, useCallback } from 'react';
import { Box, VStack, Text, Spinner, Center } from '@chakra-ui/react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { format } from 'date-fns';
import { colors } from '@theme/tokens';
import { useChat } from '../context/ChatContext';
import MessageGroup from './MessageGroup';
import TypingIndicator from './TypingIndicator';
import JobProgress from './JobProgress';
import { getDateLabel, groupMessagesBySender } from '../utils/messageGrouping';

/**
 * ChatMessages - Компонент для отображения списка сообщений в чате
 *
 * Особенности:
 * - Виртуализация для производительности с большим количеством сообщений
 * - Группировка сообщений по времени (Сегодня, Вчера, Дата)
 * - Auto-scroll к новым сообщениям
 * - Loading состояния
 * - Пустое состояние
 */
function ChatMessagesComponent({ onRetryMessage, onDeleteMessage, onCancelJob }) {
  const { messages, loading, error, currentJob, isTyping } = useChat();
  const scrollRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Группировка сообщений по датам
  const groupedMessages = useMemo(() => {
    const groups = [];
    let currentGroup = null;

    messages.forEach((message) => {
      const messageDate = new Date(message.timestamp);
      const dateKey = format(messageDate, 'yyyy-MM-dd');

      if (!currentGroup || currentGroup.date !== dateKey) {
        currentGroup = {
          date: dateKey,
          label: getDateLabel(messageDate),
          messages: []
        };
        groups.push(currentGroup);
      }

      currentGroup.messages.push(message);
    });
    return groups;
  }, [messages]);



  // Виртуализация для производительности
  const virtualizer = useVirtualizer({
    count: groupedMessages.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 220,
    overscan: 8,
  });

  // Auto-scroll к новым сообщениям
  useEffect(() => {
    if (messagesEndRef.current && messages.length > 0) {
      const timer = setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'end'
        });
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [messages.length]);

  // Рендер группы сообщений
  const renderMessageGroup = useCallback((group) => {
    const senderGroups = groupMessagesBySender(group.messages);

    return (
      <Box mb={6}>
        <MessageDateSeparator date={group.label} />
        <VStack spacing={4} align="stretch">
          {senderGroups.map((senderGroup, senderIndex) => (
            <MessageGroup
              key={`sender-${senderIndex}`}
              messages={senderGroup.messages}
              onRetryMessage={onRetryMessage}
              onDeleteMessage={onDeleteMessage}
            />
          ))}
        </VStack>
      </Box>
    );
  }, [onDeleteMessage, onRetryMessage]);

  // Loading состояние
  if (loading && messages.length === 0) {
    return (
      <Center h="full">
        <VStack spacing={4}>
          <Spinner size="lg" color={colors.brand.primary} />
          <Text color={colors.text.secondary}>Загрузка сообщений...</Text>
        </VStack>
      </Center>
    );
  }

  // Пустое состояние
  if (!loading && messages.length === 0) {
    return (
      <Center h="full">
        <VStack spacing={4} textAlign="center">
          <Box
            w={16}
            h={16}
            borderRadius="full"
            bg="rgba(255,255,255,0.05)"
            display="flex"
            alignItems="center"
            justifyContent="center"
          >
            <Text fontSize="2xl">💬</Text>
          </Box>
          <Text color={colors.text.secondary} fontSize="lg">
            Начните разговор с AI
          </Text>
          <Text color={colors.text.tertiary} fontSize="sm">
            Задайте вопрос о питании, тренировках или здоровье
          </Text>
        </VStack>
      </Center>
    );
  }

  return (
    <Box
      ref={scrollRef}
      h="full"
      overflowY="auto"
      p={4}
      css={{
        '&::-webkit-scrollbar': {
          width: '6px',
        },
        '&::-webkit-scrollbar-track': {
          background: 'rgba(255,255,255,0.05)',
          borderRadius: '3px',
        },
        '&::-webkit-scrollbar-thumb': {
          background: 'rgba(255,255,255,0.2)',
          borderRadius: '3px',
        },
        '&::-webkit-scrollbar-thumb:hover': {
          background: 'rgba(255,255,255,0.3)',
        },
      }}
    >
      <Box
        h={`${virtualizer.getTotalSize()}px`}
        position="relative"
      >
        {virtualizer.getVirtualItems().map((virtualItem) => {
          const group = groupedMessages[virtualItem.index];
          return (
            <Box
              key={virtualItem.key}
              position="absolute"
              top={0}
              left={0}
              w="full"
              transform={`translateY(${virtualItem.start}px)`}
            >
              {renderMessageGroup(group)}
            </Box>
          );
        })}
      </Box>

          {/* Job Progress */}
          {currentJob && (
            <Box px={4} py={2}>
              <JobProgress
                job={currentJob}
                onCancel={onCancelJob}
                onDownload={(url) => window.open(url, '_blank')}
              />
            </Box>
          )}

          {/* Typing Indicator */}
          <TypingIndicator
            isVisible={isTyping || loading}
            message="думает"
          />

          {/* Error indicator */}
          {error && (
            <Center py={4}>
              <Text fontSize="sm" color={colors.error}>
                {error}
              </Text>
            </Center>
          )}
    </Box>
  );
}

// Компонент разделителя дат
const MessageDateSeparator = memo(function MessageDateSeparator({ date }) {
  return (
    <Center my={4}>
      <Box
        px={3}
        py={1}
        bg="rgba(255,255,255,0.05)"
        borderRadius="full"
        border="1px solid rgba(255,255,255,0.1)"
      >
        <Text
          fontSize="xs"
          color={colors.text.tertiary}
          fontWeight={500}
          textTransform="uppercase"
          letterSpacing="0.5px"
        >
          {date}
        </Text>
      </Box>
    </Center>
  );
});

const ChatMessages = memo(ChatMessagesComponent);

export default ChatMessages;
