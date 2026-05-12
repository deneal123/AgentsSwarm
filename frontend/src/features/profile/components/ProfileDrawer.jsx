import {
  Avatar,
  Badge,
  Box,
  Button,
  Drawer,
  DrawerBody,
  DrawerCloseButton,
  DrawerContent,
  DrawerHeader,
  DrawerOverlay,
  HStack,
  Icon,
  SimpleGrid,
  Spinner,
  Text,
  VStack,
} from '@chakra-ui/react';
import { FiLogOut, FiMessageSquare, FiSliders } from 'react-icons/fi';
import { CHAT_SCROLLBAR_SX, CHAT_THEME } from '@features/chat/constants/theme';

export function ProfileDrawer({
  isOpen,
  onClose,
  profileData,
  profileMemoryCount,
  isLoading,
  user,
  threadCount = 0,
  memoryFallbackCount = 0,
  onLogout,
}) {
  return (
    <Drawer isOpen={isOpen} placement="right" onClose={onClose} size="md">
      <DrawerOverlay bg="rgba(0,0,0,0.6)" backdropFilter="blur(8px)" />
      <DrawerContent
        bg={CHAT_THEME.sidebarBg}
        borderLeft={`1px solid ${CHAT_THEME.panelBorder}`}
        sx={{
          backgroundImage:
            'radial-gradient(circle at 85% -10%, rgba(239,68,68,0.12), transparent 55%), radial-gradient(circle at 15% 110%, rgba(220,38,38,0.08), transparent 50%)',
        }}
      >
        <DrawerCloseButton mt={2} color={CHAT_THEME.textSecondary} _hover={{ color: CHAT_THEME.textPrimary }} />
        <DrawerHeader borderBottomWidth="1px" borderColor="rgba(255,255,255,0.08)" fontWeight="700" letterSpacing="-0.01em">
          Профиль
        </DrawerHeader>
        <DrawerBody pt={5} sx={CHAT_SCROLLBAR_SX}>
          <VStack spacing={5} align="stretch">
            {/* Identity card */}
            <Box
              p={5}
              borderRadius="16px"
              bg="rgba(255,255,255,0.04)"
              border={`1px solid ${CHAT_THEME.panelBorder}`}
              position="relative"
              overflow="hidden"
            >
              <Box
                position="absolute"
                top="-30%"
                right="-10%"
                w="50%"
                h="120%"
                background="radial-gradient(circle, rgba(239,68,68,0.16) 0%, transparent 65%)"
                filter="blur(30px)"
                pointerEvents="none"
              />
              <HStack spacing={4} align="center" position="relative">
                <Box p="2px" borderRadius="full" bg="linear-gradient(135deg, rgba(239,68,68,0.95), rgba(255,255,255,0.35))">
                  <Avatar
                    size="lg"
                    name={profileData?.first_name || user?.first_name || profileData?.email || user?.email}
                    bg="rgba(14,14,14,1)"
                    color={CHAT_THEME.textPrimary}
                    fontWeight="700"
                  />
                </Box>
                <VStack align="flex-start" spacing={0.5} flex="1" minW="0">
                  <Text fontSize="18px" fontWeight="700" color={CHAT_THEME.textPrimary} letterSpacing="-0.01em" noOfLines={1}>
                    {profileData?.first_name || user?.first_name || 'Пользователь'}
                  </Text>
                  <Text fontSize="12.5px" fontWeight="500" color={CHAT_THEME.textSecondary} noOfLines={1}>
                    {profileData?.email || user?.email || '—'}
                  </Text>
                  <HStack spacing={1.5} mt={1.5}>
                    <Badge
                      px={2} py={0.5} borderRadius="full" fontSize="10px" fontWeight="600" textTransform="none"
                      bg="rgba(34,197,94,0.14)" color="rgba(134,239,172,0.95)" border="1px solid rgba(34,197,94,0.25)"
                    >
                      ● Активен
                    </Badge>
                  </HStack>
                </VStack>
              </HStack>
            </Box>

            {/* Stats grid */}
            <SimpleGrid columns={2} spacing={3}>
              {[
                { label: 'Чатов', value: threadCount, icon: FiMessageSquare },
                { label: 'Память', value: profileMemoryCount ?? memoryFallbackCount, icon: FiSliders },
              ].map(({ label, value, icon: StatIcon }) => (
                <Box
                  key={label}
                  p={4}
                  borderRadius="14px"
                  bg="rgba(255,255,255,0.03)"
                  border={`1px solid ${CHAT_THEME.panelBorder}`}
                  transition="all 0.2s"
                  _hover={{ bg: 'rgba(255,255,255,0.05)', borderColor: CHAT_THEME.panelBorderStrong }}
                >
                  <HStack spacing={2} mb={1.5}>
                    <Icon as={StatIcon} boxSize={3.5} color="rgba(239,68,68,0.75)" />
                    <Text fontSize="10.5px" fontWeight="600" color={CHAT_THEME.textTertiary} letterSpacing="0.04em" textTransform="uppercase">
                      {label}
                    </Text>
                  </HStack>
                  <Text fontSize="22px" fontWeight="700" color={CHAT_THEME.textPrimary} letterSpacing="-0.02em" lineHeight="1.1">
                    {value}
                  </Text>
                </Box>
              ))}
            </SimpleGrid>

            <Button
              leftIcon={<FiLogOut />}
              onClick={() => { onClose(); onLogout?.(); }}
              h="42px"
              borderRadius="12px"
              fontSize="13px"
              fontWeight="600"
              bg={CHAT_THEME.accentSoft}
              color="#fca5a5"
              border="1px solid rgba(239,68,68,0.3)"
              _hover={{ bg: 'rgba(239,68,68,0.22)', borderColor: 'rgba(239,68,68,0.45)' }}
            >
              Выйти
            </Button>

            {isLoading && (
              <HStack spacing={2} justify="center" color={CHAT_THEME.textTertiary}>
                <Spinner size="xs" />
                <Text fontSize="11px">Загружаем данные…</Text>
              </HStack>
            )}
          </VStack>
        </DrawerBody>
      </DrawerContent>
    </Drawer>
  );
}
