import React, { useState } from 'react';
import {
  Box,
  HStack,
  VStack,
  Text,
  Icon,
  Button,
  Tooltip,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverBody,
  useDisclosure,
  Badge
} from '@chakra-ui/react';
import { FiPlus, FiSmile } from 'react-icons/fi';
import { MotionBox } from '@ui/motionPrimitives';
import { colors, borderRadius } from '@theme/tokens';

/**
 * MessageReactions - Система реакций на сообщения
 *
 * Функциональность:
 * - Отображение существующих реакций с счетчиками
 * - Добавление новых реакций
 * - Просмотр пользователей поставивших реакцию
 * - Quick reactions (👍, 👎, ❤️, 😂, 😮, 😢)
 */

// Популярные реакции для быстрого доступа
const QUICK_REACTIONS = ['👍', '👎', '❤️', '😂', '😮', '😢'];

function MessageReactions({ messageId, reactions = [], onAddReaction, onRemoveReaction, currentUserId }) {
  const [selectedReaction, setSelectedReaction] = useState(null);
  const { isOpen, onOpen, onClose } = useDisclosure();

  // Группировка реакций по emoji
  const groupedReactions = React.useMemo(() => {
    const groups = {};
    reactions.forEach(reaction => {
      if (!groups[reaction.emoji]) {
        groups[reaction.emoji] = {
          emoji: reaction.emoji,
          count: 0,
          users: []
        };
      }
      groups[reaction.emoji].count++;
      groups[reaction.emoji].users.push(reaction.userId);
    });
    return Object.values(groups);
  }, [reactions]);

  // Проверка, поставил ли текущий пользователь эту реакцию
  const hasUserReacted = (emoji) => {
    return reactions.some(r => r.emoji === emoji && r.userId === currentUserId);
  };

  // Обработка клика по реакции
  const handleReactionClick = (emoji) => {
    if (hasUserReacted(emoji)) {
      onRemoveReaction(messageId, emoji);
    } else {
      onAddReaction(messageId, emoji);
    }
    onClose();
  };

  // Обработка добавления реакции
  const handleAddReaction = (emoji) => {
    onAddReaction(messageId, emoji);
    onClose();
  };

  if (groupedReactions.length === 0) {
    return (
      <Popover isOpen={isOpen} onClose={onClose}>
        <PopoverTrigger>
          <Button
            size="xs"
            variant="ghost"
            p={1}
            minW="auto"
            h="auto"
            color={colors.text.tertiary}
            _hover={{ color: colors.brand.primary, bg: 'rgba(255,255,255,0.05)' }}
            onClick={onOpen}
          >
            <Icon as={FiSmile} boxSize={3} />
          </Button>
        </PopoverTrigger>
        <PopoverContent
          bg="rgba(0,0,0,0.9)"
          border="1px solid rgba(255,255,255,0.1)"
          borderRadius={borderRadius.lg}
          w="auto"
          p={2}
        >
          <ReactionPicker onSelectReaction={handleAddReaction} />
        </PopoverContent>
      </Popover>
    );
  }

  return (
    <HStack spacing={1} flexWrap="wrap">
      {/* Существующие реакции */}
      {groupedReactions.map((reaction) => (
        <ReactionButton
          key={reaction.emoji}
          reaction={reaction}
          isActive={hasUserReacted(reaction.emoji)}
          onClick={() => handleReactionClick(reaction.emoji)}
          currentUserId={currentUserId}
        />
      ))}

      {/* Кнопка добавления новой реакции */}
      <Popover isOpen={isOpen} onClose={onClose}>
        <PopoverTrigger>
          <MotionBox
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
          >
            <Button
              size="xs"
              variant="ghost"
              p={1}
              minW="24px"
              h="24px"
              borderRadius="full"
              color={colors.text.tertiary}
              _hover={{
                color: colors.brand.primary,
                bg: 'rgba(47, 116, 255, 0.1)',
                border: '1px solid rgba(47, 116, 255, 0.3)'
              }}
              onClick={onOpen}
              border="1px solid transparent"
              transition="all 0.2s"
            >
              <Icon as={FiPlus} boxSize={3} />
            </Button>
          </MotionBox>
        </PopoverTrigger>
        <PopoverContent
          bg="rgba(0,0,0,0.9)"
          border="1px solid rgba(255,255,255,0.1)"
          borderRadius={borderRadius.lg}
          w="auto"
          p={2}
        >
          <ReactionPicker onSelectReaction={handleAddReaction} />
        </PopoverContent>
      </Popover>
    </HStack>
  );
}

// Компонент кнопки реакции
function ReactionButton({ reaction, isActive, onClick, currentUserId }) {
  const [showUsers, setShowUsers] = useState(false);

  // Mock данные пользователей (в реальном приложении приходят с API)
  const getUserName = (userId) => {
    return userId === currentUserId ? 'Вы' : `Пользователь ${userId}`;
  };

  const userNames = reaction.users.map(getUserName);
  const tooltipText = userNames.join(', ');

  return (
    <Tooltip
      label={tooltipText}
      isOpen={showUsers}
      placement="top"
      hasArrow
    >
      <MotionBox
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        <Button
          size="xs"
          variant="ghost"
          p={2}
          minW="auto"
          h="auto"
          borderRadius="full"
          bg={isActive ? 'rgba(47, 116, 255, 0.2)' : 'rgba(255,255,255,0.05)'}
          border={isActive ? '1px solid rgba(47, 116, 255, 0.5)' : '1px solid rgba(255,255,255,0.1)'}
          color={colors.text.primary}
          _hover={{
            bg: 'rgba(47, 116, 255, 0.1)',
            border: '1px solid rgba(47, 116, 255, 0.3)',
            transform: 'translateY(-1px)'
          }}
          onClick={onClick}
          onMouseEnter={() => setShowUsers(true)}
          onMouseLeave={() => setShowUsers(false)}
          transition="all 0.2s"
          position="relative"
        >
          <HStack spacing={1}>
            <Text fontSize="sm">{reaction.emoji}</Text>
            {reaction.count > 1 && (
              <Text fontSize="xs" color={colors.text.secondary}>
                {reaction.count}
              </Text>
            )}
          </HStack>
        </Button>
      </MotionBox>
    </Tooltip>
  );
}

// Компонент выбора реакции
function ReactionPicker({ onSelectReaction }) {
  const [customEmoji, setCustomEmoji] = useState('');

  return (
    <VStack spacing={3}>
      {/* Quick reactions */}
      <HStack spacing={1} flexWrap="wrap" maxW="200px">
        {QUICK_REACTIONS.map((emoji) => (
          <MotionBox
            key={emoji}
            whileHover={{ scale: 1.2 }}
            whileTap={{ scale: 0.9 }}
          >
            <Button
              size="sm"
              variant="ghost"
              p={2}
              minW="40px"
              h="40px"
              borderRadius="full"
              onClick={() => onSelectReaction(emoji)}
              _hover={{
                bg: 'rgba(255,255,255,0.1)',
                transform: 'translateY(-2px)'
              }}
              transition="all 0.2s"
            >
              <Text fontSize="lg">{emoji}</Text>
            </Button>
          </MotionBox>
        ))}
      </HStack>

      {/* Custom emoji input */}
      <HStack spacing={2} w="full">
        <input
          type="text"
          placeholder="Или введите emoji..."
          value={customEmoji}
          onChange={(e) => setCustomEmoji(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter' && customEmoji.trim()) {
              onSelectReaction(customEmoji.trim());
              setCustomEmoji('');
            }
          }}
          style={{
            flex: 1,
            padding: '8px 12px',
            borderRadius: '8px',
            border: '1px solid rgba(255,255,255,0.2)',
            background: 'rgba(255,255,255,0.05)',
            color: colors.text.primary,
            fontSize: '14px',
            outline: 'none'
          }}
        />
        <Button
          size="sm"
          colorScheme="brand"
          onClick={() => {
            if (customEmoji.trim()) {
              onSelectReaction(customEmoji.trim());
              setCustomEmoji('');
            }
          }}
          isDisabled={!customEmoji.trim()}
        >
          OK
        </Button>
      </HStack>
    </VStack>
  );
}

// Hook для управления реакциями
export function useMessageReactions() {
  const [reactions, setReactions] = React.useState([]);

  const addReaction = React.useCallback((messageId, emoji, userId) => {
    setReactions(prev => [
      ...prev,
      {
        id: `${messageId}_${emoji}_${userId}_${Date.now()}`,
        messageId,
        emoji,
        userId,
        timestamp: new Date().toISOString()
      }
    ]);
  }, []);

  const removeReaction = React.useCallback((messageId, emoji, userId) => {
    setReactions(prev =>
      prev.filter(r => !(r.messageId === messageId && r.emoji === emoji && r.userId === userId))
    );
  }, []);

  const getReactionsForMessage = React.useCallback((messageId) => {
    return reactions.filter(r => r.messageId === messageId);
  }, [reactions]);

  return {
    reactions,
    addReaction,
    removeReaction,
    getReactionsForMessage
  };
}

export default MessageReactions;
