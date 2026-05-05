import React, { useState } from "react";
import { Box, Button, Divider, HStack, Icon, Link, Text, VStack } from "@chakra-ui/react";
import { Global } from "@emotion/react";
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom";
import { EmailIcon } from "@chakra-ui/icons";
import { FaSignInAlt, FaExclamationCircle } from "react-icons/fa";
import { login } from "@api";
import { useAuth } from "@context/AuthContext";
import { AuthFormCard, AuthInput, PasswordInput } from "@features/auth/components";
import { borderRadius } from "@theme/tokens";
import extractErrorInfo from "@utils/errorHandler";

const AUTH_FONT_FAMILY =
  "'Avenir Next', 'SF Pro Display', 'Manrope', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif";

const AUTH_THEME = {
  pageBg: "#060606",
  accent: "#ef4444",
  accentHover: "#dc2626",
  border: "rgba(255, 255, 255, 0.15)",
  mutedText: "rgba(255, 255, 255, 0.62)",
};

function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { refreshSession, setAuthenticated } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const from = location.state?.from?.pathname || "/";
  const emailInvalid = email.length > 0 && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);

    if (emailInvalid) return;

    setIsLoading(true);
    try {
      await login({ email, password });
      try {
        await refreshSession();
      } catch {
        setAuthenticated(true);
      }
      navigate(from, { replace: true });
    } catch (err) {
      const { userMessage } = extractErrorInfo(err, {
        fallbackMessage: "Не удалось выполнить вход",
      });
      setError(userMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <Global
        styles={{
          'html, body': {
            scrollbarColor: 'rgba(239, 68, 68, 0.62) rgba(255, 255, 255, 0.08)',
            scrollbarWidth: 'thin',
          },
          'html::-webkit-scrollbar, body::-webkit-scrollbar': {
            width: '10px',
          },
          'html::-webkit-scrollbar-track, body::-webkit-scrollbar-track': {
            background: 'rgba(255, 255, 255, 0.08)',
          },
          'html::-webkit-scrollbar-thumb, body::-webkit-scrollbar-thumb': {
            background: 'linear-gradient(180deg, rgba(239, 68, 68, 0.72) 0%, rgba(220, 38, 38, 0.9) 100%)',
            borderRadius: '999px',
            border: '2px solid rgba(6, 6, 6, 0.9)',
          },
          'html::-webkit-scrollbar-thumb:hover, body::-webkit-scrollbar-thumb:hover': {
            background: 'linear-gradient(180deg, rgba(248, 113, 113, 0.9) 0%, rgba(239, 68, 68, 0.96) 100%)',
          },
        }}
      />

      <Box
        position="relative"
        minH="100vh"
        bg={AUTH_THEME.pageBg}
        display="flex"
        alignItems="center"
        justifyContent="center"
        py={{ base: 10, md: 16 }}
        px={4}
        fontFamily={AUTH_FONT_FAMILY}
        overflow="hidden"
      >
      <Box position="absolute" inset={0} pointerEvents="none" zIndex={0}>
        <Box
          position="absolute"
          top="-20%"
          left="-15%"
          width="55%"
          height="55%"
          background="radial-gradient(circle, rgba(239, 68, 68, 0.16) 0%, transparent 70%)"
          filter="blur(60px)"
        />
        <Box
          position="absolute"
          bottom="-18%"
          right="-10%"
          width="45%"
          height="45%"
          background="radial-gradient(circle, rgba(255, 255, 255, 0.08) 0%, transparent 70%)"
          filter="blur(60px)"
        />
        <Box
          position="absolute"
          inset={0}
          backgroundImage="linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)"
          backgroundSize="42px 42px"
          opacity={0.2}
        />
      </Box>

        <Box position="relative" zIndex={1} w="full" maxW="520px">
          <AuthFormCard as="form" onSubmit={handleSubmit}>
          <VStack w="full" align="stretch" spacing={5}>
            <VStack align="stretch" spacing={1}>
              <Text fontSize="xs" letterSpacing="0.18em" textTransform="uppercase" color={AUTH_THEME.mutedText}>
                GPTHub
              </Text>
              <HStack spacing={3} align="center">
                <Box
                  p={2}
                  borderRadius={borderRadius.md}
                  border="1px solid rgba(239, 68, 68, 0.45)"
                  bg="rgba(239, 68, 68, 0.12)"
                >
                  <Icon as={FaSignInAlt} color={AUTH_THEME.accent} boxSize={4} />
                </Box>
                <Text fontSize={{ base: "xl", md: "2xl" }} fontWeight="500" color="white">
                  Вход в рабочее пространство
                </Text>
              </HStack>
              <Text fontSize="sm" color={AUTH_THEME.mutedText}>
                Введите e-mail и пароль, чтобы продолжить работу.
              </Text>
            </VStack>

            {error && (
              <Box
                p={3}
                bg="rgba(239, 68, 68, 0.12)"
                border="1px solid rgba(239, 68, 68, 0.35)"
                borderRadius={borderRadius.lg}
              >
                <HStack spacing={2} align="start">
                  <Icon as={FaExclamationCircle} color={AUTH_THEME.accent} mt="2px" />
                  <VStack align="start" spacing={0}>
                    <Text fontSize="sm" fontWeight="500" color={AUTH_THEME.accent}>
                      Ошибка авторизации
                    </Text>
                    <Text fontSize="xs" color={AUTH_THEME.mutedText}>
                      {error}
                    </Text>
                  </VStack>
                </HStack>
              </Box>
            )}

            <AuthInput
              id="email"
              label="E-mail"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              icon={EmailIcon}
              isRequired
              isInvalid={emailInvalid}
              errorMessage="Неверный формат e-mail"
              autoComplete="email"
            />

            <PasswordInput
              id="password"
              label="Пароль"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Введите пароль"
              isRequired
              autoComplete="current-password"
            />

            <Button
              type="submit"
              w="full"
              h="50px"
              isLoading={isLoading}
              isDisabled={emailInvalid || !email || !password}
              leftIcon={<Icon as={FaSignInAlt} />}
              borderRadius="12px"
              bg={AUTH_THEME.accent}
              color="white"
              fontWeight="500"
              _hover={{ bg: AUTH_THEME.accentHover }}
              _active={{ bg: AUTH_THEME.accentHover }}
              _disabled={{ bg: "rgba(239, 68, 68, 0.35)", color: "rgba(255,255,255,0.55)" }}
            >
              {isLoading ? "Вход..." : "Войти"}
            </Button>

            <Divider borderColor={AUTH_THEME.border} />

            <HStack spacing={1} justify="center" fontSize="sm">
              <Text color={AUTH_THEME.mutedText}>Нет аккаунта?</Text>
              <Link
                as={RouterLink}
                to="/register"
                color={AUTH_THEME.accent}
                fontWeight="500"
                _hover={{ color: AUTH_THEME.accentHover, textDecoration: "none" }}
              >
                Зарегистрироваться
              </Link>
            </HStack>
          </VStack>
          </AuthFormCard>
        </Box>
      </Box>
    </>
  );
}

export default LoginPage;
