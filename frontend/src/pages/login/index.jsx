import React, { useState } from "react";
import { Box, Button, Divider, HStack, Icon, Link, Text, VStack } from "@chakra-ui/react";
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom";
import { EmailIcon } from "@chakra-ui/icons";
import { FaExclamationCircle, FaSignInAlt } from "react-icons/fa";
import { login } from "@api";
import { useAuth } from "@context/AuthContext";
import { AuthFormCard, AuthInput, AuthPageHeader, AuthPageShell, PasswordInput } from "@features/auth";
import { borderRadius } from "@theme/tokens";
import { AUTH_THEME } from "@features/auth";
import extractErrorInfo from "@utils/errorHandler";

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
      const { userMessage } = extractErrorInfo(err, { fallbackMessage: "Не удалось выполнить вход" });
      setError(userMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthPageShell
      containerProps={{ py: { base: 10, md: 16 }, px: 4 }}
      topGradient={{ top: "-20%", left: "-15%", width: "55%", height: "55%", background: "radial-gradient(circle, rgba(239, 68, 68, 0.16) 0%, transparent 70%)" }}
      bottomGradient={{ bottom: "-18%", right: "-10%", width: "45%", height: "45%", background: "radial-gradient(circle, rgba(255, 255, 255, 0.08) 0%, transparent 70%)" }}
    >
      <Box position="relative" zIndex={1} w="full" maxW="520px">
        <AuthFormCard as="form" onSubmit={handleSubmit}>
          <VStack w="full" align="stretch" spacing={5}>
            <AuthPageHeader
              icon={FaSignInAlt}
              title="Вход в рабочее пространство"
              description="Введите e-mail и пароль, чтобы продолжить работу."
            />

            {error && (
              <Box p={3} bg="rgba(239, 68, 68, 0.12)" border="1px solid rgba(239, 68, 68, 0.35)" borderRadius={borderRadius.lg}>
                <HStack spacing={2} align="start">
                  <Icon as={FaExclamationCircle} color={AUTH_THEME.accent} mt="2px" />
                  <VStack align="start" spacing={0}>
                    <Text fontSize="sm" fontWeight="500" color={AUTH_THEME.accent}>Ошибка авторизации</Text>
                    <Text fontSize="xs" color={AUTH_THEME.mutedText}>{error}</Text>
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
              <Link as={RouterLink} to="/register" color={AUTH_THEME.accent} fontWeight="500" _hover={{ color: AUTH_THEME.accentHover, textDecoration: "none" }}>
                Зарегистрироваться
              </Link>
            </HStack>
          </VStack>
        </AuthFormCard>
      </Box>
    </AuthPageShell>
  );
}

export default LoginPage;
