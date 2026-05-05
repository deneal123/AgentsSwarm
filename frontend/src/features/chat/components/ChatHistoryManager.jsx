import React, { useState, useMemo } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Input,
  InputGroup,
  InputLeftElement,
  Icon,
  Button,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  Badge,
  Avatar,
  Divider,
  useToast
} from '@chakra-ui/react';
import {
  FiSearch,
  FiMessageSquare,
  FiPin,
  FiArchive,
  FiTrash2,
  FiEdit,
  FiDownload,
  FiMoreVertical,
  FiPlus,
  FiClock
} from 'react-icons/fi';
import { formatDistanceToNow, isToday, isYesterday, isThisWeek } from 'date-fns';
import { ru } from 'date-fns/locale';
import { colors, borderRadius } from '@theme/tokens';

/**
 * ChatHistoryManager - Компонент для управления историей чатов
 *
 * Функциональность:
 * - Просмотр всех чатов пользователя
 * - Поиск по названиям чатов
 * - Группировка по времени (сегодня, вчера, неделя)
 * - Закрепленные чаты
 * - Действия с чатами (переименование, удаление, экспорт)
 */
function ChatHistoryManager({ isOpen, onClose, currentChatId, onChatSelect }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [chats, setChats] = useState([
    // Mock data - в реальном приложении будет приходить с API
    {
      id: 'chat_1',
      title: 'Обсуждение питания',
      lastMessage: 'Расскажи о здоровом питании',
      lastMessageTime: new Date(Date.now() - 1000 * 60 * 30), // 30 минут назад
      isPinned: true,
      messageCount: 15,
      hasUnread: false
    },
    {
      id: 'chat_2',
      title: 'План тренировок',
      lastMessage: 'Создай план на неделю',
      lastMessageTime: new Date(Date.now() - 1000 * 60 * 60 * 2), // 2 часа назад
      isPinned: false,
      messageCount: 8,
      hasUnread: true
    },
    {
      id: 'chat_3',
      title: 'Калорийность продуктов',
      lastMessage: 'Сколько калорий в банане?',
      lastMessageTime: new Date(Date.now() - 1000 * 60 * 60 * 24), // вчера
      isPinned: false,
      messageCount: 3,
      hasUnread: false
    }
  ]);

  const toast = useToast();

  // Группировка чатов по времени
  const groupedChats = useMemo(() => {
    const groups = {
      pinned: [],
      today: [],
      yesterday: [],
      week: [],
      older: []
    };

    // Фильтрация по поиску
    const filteredChats = chats.filter(chat =>
      chat.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      chat.lastMessage.toLowerCase().includes(searchQuery.toLowerCase())
    );

    filteredChats.forEach(chat => {
      if (chat.isPinned) {
        groups.pinned.push(chat);
      } else {
        const daysDiff = Math.floor((Date.now() - chat.lastMessageTime) / (1000 * 60 * 60 * 24));

        if (isToday(chat.lastMessageTime)) {
          groups.today.push(chat);
        } else if (isYesterday(chat.lastMessageTime)) {
          groups.yesterday.push(chat);
        } else if (isThisWeek(chat.lastMessageTime)) {
          groups.week.push(chat);
        } else {
          groups.older.push(chat);
        }
      }
    });

    return groups;
  }, [chats, searchQuery]);

  // Действия с чатом
  const handleChatAction = (action, chatId) => {
    switch (action) {
      case 'pin':
        setChats(prev => prev.map(chat =>
          chat.id === chatId ? { ...chat, isPinned: !chat.isPinned } : chat
        ));
        break;

      case 'archive':
        setChats(prev => prev.filter(chat => chat.id !== chatId));
        toast({
          title: 'Чат архивирован',
          description: 'Чат перемещен в архив',
          status: 'info',
          duration: 2000,
        });
        break;

      case 'delete':
        setChats(prev => prev.filter(chat => chat.id !== chatId));
        break;

      case 'rename':
        // В реальном приложении открываем модал для переименования
        toast({
          title: 'Переименование',
          description: 'Функция переименования будет реализована',
          status: 'info',
          duration: 2000,
        });
        break;

      case 'export':
        // В реальном приложении скачиваем историю
        toast({
          title: 'Экспорт',
          description: 'История чата экспортирована',
          status: 'success',
          duration: 2000,
        });
        break;
    }
  };

  // Создание нового чата
  const handleNewChat = () => {
    const newChat = {
      id: `chat_${Date.now()}`,
      title: 'Новый чат',
      lastMessage: 'Начните разговор...',
      lastMessageTime: new Date(),
      isPinned: false,
      messageCount: 0,
      hasUnread: false
    };

    setChats(prev => [newChat, ...prev]);
    onChatSelect(newChat.id);
    onClose();

    toast({
      title: 'Новый чат создан',
      description: 'Начните общение с AI',
      status: 'success',
      duration: 2000,
    });
  };

  const renderChatGroup = (title, chats, icon) => {
    if (chats.length === 0) return null;

    return (
      <Box>
        <HStack spacing={2} mb={3}>
          <Icon as={icon} boxSize={4} color={colors.text.tertiary} />
          <Text fontSize="sm" fontWeight="medium" color={colors.text.secondary}>
            {title}
          </Text>
        </HStack>

        <VStack spacing={1} align="stretch">
          {chats.map(chat => (
            <ChatItem
              key={chat.id}
              chat={chat}
              isActive={chat.id === currentChatId}
              onSelect={() => {
                onChatSelect(chat.id);
                onClose();
              }}
              onAction={handleChatAction}
            />
          ))}
        </VStack>
      </Box>
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md">
      <ModalOverlay backdropFilter="blur(8px)" />
      <ModalContent
        bg="rgba(5,5,5,0.95)"
        backdropFilter="blur(20px)"
        border="1px solid rgba(255,255,255,0.1)"
        borderRadius="xl"
        maxH="80vh"
        overflow="hidden"
      >
        <ModalHeader color={colors.text.primary}>
          <HStack spacing={3} justify="space-between">
            <HStack spacing={3}>
              <Icon as={FiMessageSquare} color={colors.brand.primary} />
              <Text>История чатов</Text>
            </HStack>
            <Button
              size="sm"
              colorScheme="brand"
              leftIcon={<FiPlus />}
              onClick={handleNewChat}
            >
              Новый чат
            </Button>
          </HStack>
        </ModalHeader>

        <ModalCloseButton color={colors.text.secondary} />

        <ModalBody>
          <VStack spacing={4} align="stretch">
            {/* Search */}
            <InputGroup>
              <InputLeftElement>
                <Icon as={FiSearch} color={colors.text.tertiary} />
              </InputLeftElement>
              <Input
                placeholder="Поиск по чатам..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                bg="rgba(255,255,255,0.05)"
                border="1px solid rgba(255,255,255,0.1)"
                _focus={{
                  borderColor: colors.brand.primary,
                  bg: "rgba(255,255,255,0.08)"
                }}
              />
            </InputGroup>

            {/* Chat groups */}
            <Box maxH="400px" overflowY="auto">
              <VStack spacing={6} align="stretch">
                {renderChatGroup('Закрепленные', groupedChats.pinned, FiPin)}
                {renderChatGroup('Сегодня', groupedChats.today, FiClock)}
                {renderChatGroup('Вчера', groupedChats.yesterday, FiClock)}
                {renderChatGroup('На этой неделе', groupedChats.week, FiClock)}
                {renderChatGroup('Ранее', groupedChats.older, FiClock)}
              </VStack>
            </Box>

            {chats.length === 0 && (
              <Box textAlign="center" py={8}>
                <Icon as={FiMessageSquare} boxSize={8} color={colors.text.tertiary} mb={3} />
                <Text color={colors.text.secondary}>У вас пока нет чатов</Text>
                <Button
                  mt={3}
                  colorScheme="brand"
                  leftIcon={<FiPlus />}
                  onClick={handleNewChat}
                >
                  Начать первый чат
                </Button>
              </Box>
            )}
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}

// Компонент для отдельного чата
function ChatItem({ chat, isActive, onSelect, onAction }) {
  return (
    <Box
      p={3}
      borderRadius={borderRadius.lg}
      bg={isActive ? 'rgba(47, 116, 255, 0.1)' : 'rgba(255,255,255,0.02)'}
      border={isActive ? '1px solid rgba(47, 116, 255, 0.3)' : '1px solid rgba(255,255,255,0.05)'}
      cursor="pointer"
      onClick={onSelect}
      _hover={{ bg: 'rgba(255,255,255,0.05)' }}
      transition="all 0.2s"
      position="relative"
    >
      <HStack spacing={3} align="start">
        {/* Avatar */}
        <Avatar
          size="sm"
          bg={chat.isPinned ? colors.brand.primary : colors.brand.secondary}
          icon={<FiMessageSquare size={12} />}
        />

        {/* Content */}
        <VStack align="start" spacing={1} flex="1" minW={0}>
          <HStack spacing={2} w="full">
            <Text
              fontSize="sm"
              fontWeight="medium"
              color={colors.text.primary}
              noOfLines={1}
              flex="1"
            >
              {chat.title}
            </Text>

            {chat.hasUnread && (
              <Box
                w={2}
                h={2}
                borderRadius="full"
                bg={colors.brand.primary}
                flexShrink={0}
              />
            )}

            {chat.isPinned && (
              <Icon as={FiPin} boxSize={3} color={colors.brand.primary} />
            )}
          </HStack>

          <Text
            fontSize="xs"
            color={colors.text.tertiary}
            noOfLines={1}
          >
            {chat.lastMessage}
          </Text>

          <HStack spacing={2}>
            <Text fontSize="xs" color={colors.text.tertiary}>
              {formatDistanceToNow(chat.lastMessageTime, {
                addSuffix: true,
                locale: ru
              })}
            </Text>
            <Text fontSize="xs" color={colors.text.tertiary}>
              •
            </Text>
            <Text fontSize="xs" color={colors.text.tertiary}>
              {chat.messageCount} сообщений
            </Text>
          </HStack>
        </VStack>

        {/* Actions menu */}
        <Menu>
          <MenuButton
            as={Box}
            p={1}
            borderRadius="full"
            _hover={{ bg: 'rgba(255,255,255,0.1)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <Icon as={FiMoreVertical} boxSize={3} color={colors.text.tertiary} />
          </MenuButton>
          <MenuList bg="rgba(0,0,0,0.9)" border="1px solid rgba(255,255,255,0.1)">
            <MenuItem
              onClick={() => onAction('rename', chat.id)}
              icon={<FiEdit size={16} />}
              _hover={{ bg: 'rgba(255,255,255,0.1)' }}
            >
              Переименовать
            </MenuItem>
            <MenuItem
              onClick={() => onAction('pin', chat.id)}
              icon={<FiPin size={16} />}
              _hover={{ bg: 'rgba(255,255,255,0.1)' }}
            >
              {chat.isPinned ? 'Открепить' : 'Закрепить'}
            </MenuItem>
            <MenuItem
              onClick={() => onAction('export', chat.id)}
              icon={<FiDownload size={16} />}
              _hover={{ bg: 'rgba(255,255,255,0.1)' }}
            >
              Экспорт истории
            </MenuItem>
            <MenuItem
              onClick={() => onAction('archive', chat.id)}
              icon={<FiArchive size={16} />}
              _hover={{ bg: 'rgba(255,255,255,0.1)' }}
            >
              В архив
            </MenuItem>
            <MenuItem
              onClick={() => onAction('delete', chat.id)}
              icon={<FiTrash2 size={16} />}
              color={colors.error}
              _hover={{ bg: 'rgba(255,0,0,0.1)' }}
            >
              Удалить
            </MenuItem>
          </MenuList>
        </Menu>
      </HStack>
    </Box>
  );
}

export default ChatHistoryManager;
