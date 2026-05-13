import React from 'react';
import { Box, Button, HStack, Icon, IconButton, Spinner, Text, VStack } from '@chakra-ui/react';
import { FiMessageSquare, FiPlus, FiSettings, FiX } from 'react-icons/fi';
import { CHAT_FONT_FAMILY, CHAT_SCROLLBAR_SX, CHAT_THEME } from '../constants/theme';
import { ChatSidebar } from './index';

function ChatSidebarPanel({
  isSidebarCollapsed,
  filteredRecentThreads,
  threadId,
  sidebarSearch,
  setSidebarSearch,
  deletingThreadId,
  handleDeleteThread,
  onNavigateThread,
  onNewChat,
  onOpenMemory,
  onOpenSettings,
}) {
  const sidebar = (
    <VStack h="full" align="stretch" spacing={0} p={4}>
      <Box mb={5}>
        <Text fontWeight="700" color="white">AI Assistant</Text>
      </Box>

      <Button leftIcon={<FiPlus />} onClick={onNewChat} mb={4} h="38px" borderRadius="12px"
        bg={CHAT_THEME.panelHover} border={`1.5px solid ${CHAT_THEME.panelBorderStrong}`}
        color={CHAT_THEME.textSecondary} fontWeight="600" fontSize="13px" fontFamily={CHAT_FONT_FAMILY}
        _hover={{ bg: CHAT_THEME.panelActive, color: CHAT_THEME.textPrimary, borderColor: 'rgba(255,255,255,0.2)' }}
        transition="all 0.18s" justifyContent="flex-start">
        Новый чат
      </Button>

      <Text color={CHAT_THEME.textTertiary} fontSize="11px" fontWeight="600" textTransform="uppercase"
        letterSpacing="0.08em" mb={2} px={1}>
        Последние чаты
      </Text>

      <Box mb={3.5} position="relative">
        <Box as="input" type="text" placeholder="Поиск чатов..." value={sidebarSearch}
          onChange={(e) => setSidebarSearch(e.target.value)}
          w="100%" h="32px" pl={3} pr={3} borderRadius="9px"
          bg={CHAT_THEME.panelHover} border={`1.5px solid ${CHAT_THEME.panelBorder}`}
          color={CHAT_THEME.textPrimary} fontSize="13px" fontFamily={CHAT_FONT_FAMILY} outline="none"
          sx={{
            '&::placeholder': { color: CHAT_THEME.textTertiary },
            '&:focus': { borderColor: 'rgba(239,68,68,0.3)', boxShadow: '0 0 0 3px rgba(239,68,68,0.08)' },
            transition: 'border-color 0.18s, box-shadow 0.18s',
          }} />
      </Box>

      <Box flex="1" overflowY="auto" sx={CHAT_SCROLLBAR_SX} mr={-1} pr={1}>
        <VStack spacing={0.5} align="stretch">
          {filteredRecentThreads.length === 0 && (
            <Text color={CHAT_THEME.textTertiary} fontSize="13px" px={2} py={2}>Нет чатов</Text>
          )}
          {filteredRecentThreads.map((thread) => {
            const tid = thread.thread_id || thread.id || thread;
            const label = thread.title || thread.last_message || `Чат ${String(tid).slice(0, 8)}`;
            const isActive = tid === threadId;
            return (
              <Box key={tid} role="group" position="relative">
                <HStack spacing={2.5} px={3} py={2} pr={9} borderRadius="10px"
                  bg={isActive ? CHAT_THEME.accentSoft : 'transparent'}
                  border={`1.5px solid ${isActive ? 'rgba(239,68,68,0.3)' : 'transparent'}`}
                  cursor="pointer"
                  _hover={{ bg: isActive ? CHAT_THEME.accentSoft : CHAT_THEME.panelHover }}
                  onClick={() => onNavigateThread(tid)} transition="all 0.15s" role="button">
                  <Icon as={FiMessageSquare} color={isActive ? '#f87171' : CHAT_THEME.textTertiary}
                    boxSize="14px" flexShrink={0} />
                  <Text color={isActive ? '#fca5a5' : CHAT_THEME.textSecondary} fontSize="13.5px"
                    fontWeight={isActive ? '600' : '500'} noOfLines={1} flex="1" letterSpacing="-0.01em">
                    {label}
                  </Text>
                </HStack>
                <IconButton aria-label="Удалить чат"
                  icon={deletingThreadId === tid ? <Spinner size="xs" /> : <FiX />}
                  size="xs" position="absolute" right="7px" top="50%"
                  transform="translateY(-50%) translateX(3px)"
                  opacity={isActive ? 0.92 : 0} pointerEvents={isActive ? 'auto' : 'none'}
                  _groupHover={{ opacity: 1, transform: 'translateY(-50%) translateX(0px)', pointerEvents: 'auto' }}
                  variant="ghost" color="rgba(248,113,113,0.95)"
                  _hover={{ bg: 'rgba(239,68,68,0.2)', color: '#fca5a5' }}
                  _active={{ bg: 'rgba(239,68,68,0.28)' }} borderRadius="8px"
                  onClick={(e) => handleDeleteThread(thread, e)}
                  isDisabled={deletingThreadId === tid} transition="all 0.18s" />
              </Box>
            );
          })}
        </VStack>
      </Box>

      <VStack spacing={1} align="stretch" mt={4} pt={4} borderTop={`1px solid ${CHAT_THEME.panelBorder}`}>
        {[
          { icon: '🧠', label: 'Память и контекст', onClick: onOpenMemory },
          { icon: <FiSettings />, label: 'Настройки', onClick: onOpenSettings },
        ].map(({ icon, label, onClick }) => (
          <Button key={label} size="sm" h="34px" justifyContent="flex-start"
            leftIcon={<Box w="16px" h="16px" display="flex" alignItems="center" justifyContent="center" flexShrink={0}>
              {typeof icon === 'string' ? <Text fontSize="13px" lineHeight="1">{icon}</Text> : icon}
            </Box>}
            variant="ghost" color={CHAT_THEME.textSecondary} fontSize="13px" fontWeight="500"
            fontFamily={CHAT_FONT_FAMILY} borderRadius="10px"
            _hover={{ bg: CHAT_THEME.panelHover, color: CHAT_THEME.textPrimary }}
            onClick={onClick} transition="all 0.15s">
            {label}
          </Button>
        ))}
      </VStack>
    </VStack>
  );

  return (
    <ChatSidebar isCollapsed={isSidebarCollapsed}>
      <Box bg={CHAT_THEME.sidebarBg} h="full" borderRight={`1px solid ${CHAT_THEME.panelBorder}`}>
        {sidebar}
      </Box>
    </ChatSidebar>
  );
}

export default React.memo(ChatSidebarPanel);
