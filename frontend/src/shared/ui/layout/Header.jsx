import React, { useEffect, useState } from "react";
import {
  Avatar,
  Box,
  Button,
  Divider,
  Drawer,
  DrawerBody,
  DrawerCloseButton,
  DrawerContent,
  DrawerHeader,
  DrawerOverlay,
  Flex,
  HStack,
  Icon,
  IconButton,
  Link,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  Portal,
  Stack,
  Text,
  VStack,
  useDisclosure,
} from "@chakra-ui/react";
import { ChevronRightIcon, HamburgerIcon, TriangleDownIcon } from "@chakra-ui/icons";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { APP_ROUTES } from "@app/router";
import { isAuthRoute } from "@app/router";
import { FaHome, FaSignOutAlt, FaUser } from "react-icons/fa";
import { MotionBox } from "@shared/ui/lib/motionPrimitives";
import { useAuth } from "@app/providers";
import { borderRadius, colors } from "@theme/tokens";
import { preloadRoute } from "@hooks/useRoutePreload";
import BrandMark from "./BrandMark";

const HEADER_THEME = {
  bg: "rgba(6, 6, 6, 0.88)",
  bgScrolled: "rgba(6, 6, 6, 0.96)",
  border: "rgba(255, 255, 255, 0.12)",
  borderSoft: "rgba(255, 255, 255, 0.08)",
  text: "rgba(255, 255, 255, 0.9)",
  muted: "rgba(255, 255, 255, 0.62)",
  accent: "#ef4444",
  accentSoft: "rgba(239, 68, 68, 0.14)",
};

const navItems = [
  { label: "Чат", to: APP_ROUTES.ROOT, icon: FaHome },
];

const linkBaseStyles = {
  fontWeight: 500,
  fontSize: "13px",
  letterSpacing: "0.02em",
  color: HEADER_THEME.muted,
  transition: "all 0.2s ease",
};

function Header() {
  const { isAuthenticated, logout, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const isAuthPage = isAuthRoute(location.pathname);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [scrolled, setScrolled] = useState(false);
  const userLabel = user?.first_name || user?.email || "Профиль";

  useEffect(() => {
    onClose();
  }, [location.pathname, onClose]);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 18);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const renderNavLink = (item) => {
    const isActive = location.pathname === item.to;

    return (
      <MotionBox
        key={item.to}
        whileHover={{ y: -1 }}
        transition={{ type: "spring", stiffness: 350, damping: 20 }}
      >
        <Link
          as={NavLink}
          to={item.to}
          onMouseEnter={() => preloadRoute(item.to)}
          position="relative"
          px={3}
          py={2}
          borderRadius={borderRadius.md}
          display="flex"
          alignItems="center"
          gap={2}
          bg={isActive ? HEADER_THEME.accentSoft : "transparent"}
          _hover={{
            color: "white",
            bg: "rgba(255, 255, 255, 0.06)",
          }}
          _focusVisible={{
            boxShadow: "0 0 0 2px rgba(239, 68, 68, 0.5)",
            outline: "none",
          }}
          {...linkBaseStyles}
          color={isActive ? HEADER_THEME.accent : HEADER_THEME.muted}
        >
          <Icon as={item.icon} boxSize={3.5} opacity={0.9} />
          {item.label}
          {isActive && (
            <Box
              position="absolute"
              bottom="-2px"
              left={0}
              right={0}
              mx="auto"
              w="70%"
              h="2px"
              borderRadius="full"
              bg="linear-gradient(90deg, transparent, rgba(239,68,68,0.85), transparent)"
            />
          )}
        </Link>
      </MotionBox>
    );
  };

  const renderAuthActions = () => {
    if (!isAuthenticated) {
      return null;
    }

    return (
      <Menu>
        <MenuButton
          as={Button}
          variant="unstyled"
          size="sm"
          px={2}
          py={1}
          borderRadius={borderRadius.full}
          _focusVisible={{
            boxShadow: "0 0 0 2px rgba(239, 68, 68, 0.5)",
            outline: "none",
          }}
        >
          <HStack spacing={3} align="center">
            <Box
              position="relative"
              borderRadius="full"
              p="1.5px"
              bg="linear-gradient(135deg, rgba(239, 68, 68, 0.95), rgba(255, 255, 255, 0.4))"
            >
              <Avatar
                name={userLabel}
                size="xs"
                bg="rgba(12, 12, 12, 1)"
                color={colors.text.primary}
                fontSize="10px"
                fontWeight="bold"
              />
              <Box
                position="absolute"
                bottom={0}
                right={0}
                w="8px"
                h="8px"
                borderRadius="full"
                bg="#ef4444"
                border="2px solid"
                borderColor="rgba(6, 6, 6, 1)"
              />
            </Box>

            <Stack spacing={0} align="flex-start" display={{ base: "none", md: "flex" }}>
              <Text fontSize="sm" fontWeight="500" color={HEADER_THEME.text}>
                {user?.first_name || "Пользователь"}
              </Text>
              <Text fontSize="10px" color={HEADER_THEME.muted} letterSpacing="0.02em">
                {user?.email || "user@local"}
              </Text>
            </Stack>

            <Icon
              as={TriangleDownIcon}
              fontSize="8px"
              color={HEADER_THEME.muted}
              display={{ base: "none", md: "block" }}
            />
          </HStack>
        </MenuButton>

        <Portal>
          <MenuList
            bg="rgba(11, 11, 11, 0.98)"
            backdropFilter="blur(14px)"
            border="1px solid"
            borderColor={HEADER_THEME.border}
            borderRadius={borderRadius.lg}
            boxShadow="0 20px 40px rgba(0, 0, 0, 0.55)"
            py={0}
            px={0}
            minW="240px"
            overflow="hidden"
            zIndex={9999}
          >
            <Box
              position="absolute"
              top={0}
              left={0}
              right={0}
              h="2px"
              bg="linear-gradient(90deg, transparent, rgba(239,68,68,0.85), transparent)"
            />

            <Box px={4} py={4} bg="rgba(255, 255, 255, 0.02)" borderBottom="1px solid rgba(255, 255, 255, 0.06)">
              <HStack spacing={3}>
                <Avatar
                  name={userLabel}
                  size="md"
                  bg="rgba(16, 16, 16, 1)"
                  color={colors.text.primary}
                  fontWeight="bold"
                />
                <VStack align="start" spacing={0}>
                  <Text fontWeight="500" fontSize="sm" color={HEADER_THEME.text}>
                    {user?.first_name || "Пользователь"}
                  </Text>
                  <Text fontSize="xs" color={HEADER_THEME.muted}>
                    {user?.email}
                  </Text>
                </VStack>
              </HStack>
            </Box>

            <Box p={2}>
              <MenuItem
                onClick={() => navigate('/?profile=open')}
                py={3}
                px={3}
                fontSize="sm"
                borderRadius={borderRadius.md}
                bg="transparent"
                color={HEADER_THEME.text}
                icon={<Icon as={FaUser} boxSize={4} color={HEADER_THEME.accent} />}
                _hover={{ bg: "rgba(255, 255, 255, 0.06)" }}
                _focus={{ bg: "rgba(255, 255, 255, 0.06)", boxShadow: "none" }}
              >
                <HStack justify="space-between" w="full">
                  <Text>Профиль</Text>
                  <Icon as={ChevronRightIcon} boxSize={4} color={HEADER_THEME.muted} />
                </HStack>
              </MenuItem>

              <MenuItem
                onClick={logout}
                py={3}
                px={3}
                fontSize="sm"
                borderRadius={borderRadius.md}
                bg="transparent"
                color={HEADER_THEME.accent}
                icon={<Icon as={FaSignOutAlt} boxSize={4} color={HEADER_THEME.accent} />}
                _hover={{ bg: "rgba(239, 68, 68, 0.12)" }}
                _focus={{ bg: "rgba(239, 68, 68, 0.12)", boxShadow: "none" }}
              >
                Выйти
              </MenuItem>
            </Box>
          </MenuList>
        </Portal>
      </Menu>
    );
  };

  return (
    <>
      <Box as="header" position="sticky" top={0} zIndex={100} transition="all 0.25s ease">
        <Box
          position="absolute"
          inset={0}
          bg={scrolled ? HEADER_THEME.bgScrolled : HEADER_THEME.bg}
          backdropFilter={scrolled ? "blur(16px)" : "blur(10px)"}
          borderBottom="1px solid"
          borderColor={scrolled ? HEADER_THEME.border : HEADER_THEME.borderSoft}
          transition="all 0.25s ease"
        />

        <Box
          position="absolute"
          bottom={0}
          left={0}
          right={0}
          h="1px"
          bg="linear-gradient(90deg, transparent, rgba(239,68,68,0.4), transparent)"
          opacity={scrolled ? 0.9 : 0.5}
          transition="opacity 0.25s ease"
        />

        <Box position="relative">
          <Box
            maxW={isAuthPage ? "none" : "1400px"}
            mx="auto"
            px={isAuthPage ? 5 : { base: 4, md: 6, lg: 8 }}
          >
            <Flex align="center" justify="space-between" h="76px" gap={4}>
              <Link
                as={NavLink}
                to="/"
                display="flex"
                alignItems="center"
                _hover={{ textDecoration: "none" }}
                _focusVisible={{
                  boxShadow: "0 0 0 2px rgba(239, 68, 68, 0.5)",
                  outline: "none",
                  borderRadius: borderRadius.md,
                }}
              >
                <BrandMark />
              </Link>

              <Flex align="center" gap={6}>
                <HStack spacing={1} display={{ base: "none", lg: "flex" }}>
                  {navItems.map(renderNavLink)}
                </HStack>

                {renderAuthActions()}

                <MotionBox
                  display={{ base: "block", lg: "none" }}
                  whileHover={{ scale: 1.04 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <IconButton
                    icon={<HamburgerIcon />}
                    variant="ghost"
                    onClick={onOpen}
                    aria-label="Открыть меню"
                    borderRadius={borderRadius.md}
                    border="1px solid rgba(255,255,255,0.14)"
                    color={HEADER_THEME.text}
                    _hover={{
                      bg: "rgba(255, 255, 255, 0.06)",
                      borderColor: "rgba(239, 68, 68, 0.6)",
                    }}
                  />
                </MotionBox>
              </Flex>
            </Flex>
          </Box>
        </Box>
      </Box>

      <Drawer
        isOpen={isOpen}
        placement="right"
        onClose={onClose}
        size="xs"
        blockScrollOnMount={false}
        returnFocusOnClose={false}
        closeOnOverlayClick
        closeOnEsc
        autoFocus={false}
        trapFocus={false}
      >
        <DrawerOverlay
          bg="rgba(0, 0, 0, 0.55)"
          sx={{ transition: "none !important", animation: "none !important" }}
        />
        <DrawerContent
          bg="rgba(8, 8, 8, 0.98)"
          borderLeft="1px solid rgba(255,255,255,0.1)"
          sx={{
            transition: "transform 0.2s ease-out !important",
            animation: "none !important",
          }}
        >
          <DrawerCloseButton color={HEADER_THEME.muted} _hover={{ color: HEADER_THEME.text }} />
          <DrawerHeader borderBottomWidth="1px" borderColor="rgba(255,255,255,0.08)">
            <BrandMark size="sm" />
          </DrawerHeader>

          <DrawerBody py={6}>
            <VStack spacing={2} align="stretch">
              {navItems.map((item) => {
                const isActive = location.pathname === item.to;
                return (
                  <Box
                    key={item.to}
                    as="button"
                    onClick={() => navigate(item.to)}
                    display="flex"
                    alignItems="center"
                    gap={3}
                    px={4}
                    py={3}
                    borderRadius={borderRadius.md}
                    bg={isActive ? "rgba(239, 68, 68, 0.14)" : "transparent"}
                    color={isActive ? HEADER_THEME.accent : HEADER_THEME.muted}
                    fontWeight={500}
                    w="full"
                    textAlign="left"
                    cursor="pointer"
                    _hover={{ bg: "rgba(255, 255, 255, 0.06)", color: HEADER_THEME.text }}
                  >
                    <Icon as={item.icon} boxSize={4} />
                    {item.label}
                    {isActive && <Box ml="auto" w="6px" h="6px" borderRadius="full" bg={HEADER_THEME.accent} />}
                  </Box>
                );
              })}

              {isAuthenticated && (
                <>
                  <Divider borderColor="rgba(255,255,255,0.08)" my={4} />
                  <Box
                    as="button"
                    onClick={() => navigate('/?profile=open')}
                    display="flex"
                    alignItems="center"
                    gap={3}
                    px={4}
                    py={3}
                    borderRadius={borderRadius.md}
                    color={HEADER_THEME.muted}
                    fontWeight={500}
                    w="full"
                    textAlign="left"
                    cursor="pointer"
                    _hover={{ bg: "rgba(255, 255, 255, 0.06)", color: HEADER_THEME.text }}
                  >
                    <Icon as={FaUser} boxSize={4} />
                    Профиль
                  </Box>
                  <Box
                    as="button"
                    onClick={() => logout()}
                    display="flex"
                    alignItems="center"
                    gap={3}
                    px={4}
                    py={3}
                    borderRadius={borderRadius.md}
                    color={HEADER_THEME.accent}
                    fontWeight={500}
                    w="full"
                    textAlign="left"
                    cursor="pointer"
                    _hover={{ bg: "rgba(239, 68, 68, 0.12)" }}
                  >
                    <Icon as={FaSignOutAlt} boxSize={4} />
                    Выйти
                  </Box>
                </>
              )}
            </VStack>
          </DrawerBody>
        </DrawerContent>
      </Drawer>
    </>
  );
}

export default Header;
