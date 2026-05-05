import React, { useMemo, useState } from "react";
import { Box, Button, Divider, HStack, Icon, Link, Text, VStack } from "@chakra-ui/react";
import { Global } from "@emotion/react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { EmailIcon } from "@chakra-ui/icons";
import { FaUserPlus, FaExclamationCircle, FaUser } from "react-icons/fa";
import { registerUser } from "@api";
import {
  AuthFormCard,
  AuthInput,
  PasswordInput,
  PasswordStrength,
} from "@features/auth/components";
import { AUTH_PRIMARY_BUTTON_SX } from "@features/auth/components/authButtonStyles";
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

function SignUpPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const emailInvalid = email.length > 0 && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

  const emailDomain = useMemo(() => (email.includes("@") ? email.split("@")[1] : ""), [email]);
  const softEmailDomainWarning = useMemo(() => {
    if (!email || emailInvalid) return "";
    if (!emailDomain.includes(".")) return "Проверьте домен e-mail (отсутствует точка)";
    const suspiciousTlds = ["invalid", "example", "local", "test"];
    const tld = emailDomain.split(".").pop()?.toLowerCase();
    if (tld && suspiciousTlds.includes(tld))
      return "Похоже на тестовый домен — убедитесь, что он корректен";
    return "";
  }, [email, emailDomain, emailInvalid]);

  const hasMinLen = password.length >= 8;
  const hasLetter = /[A-Za-zА-Яа-я]/.test(password);
  const hasDigit = /\d/.test(password);
  const passwordsMismatch = password && confirmPassword && password !== confirmPassword;
  const passwordStrongEnough = hasMinLen && hasLetter && hasDigit;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);

    if (emailInvalid || !passwordStrongEnough || passwordsMismatch) {
      return;
    }

    setIsLoading(true);
    try {
      await registerUser({ email, password, first_name: firstName || null });
      navigate("/login", { replace: true });
    } catch (err) {
      const { userMessage } = extractErrorInfo(err, {
        fallbackMessage: "Не удалось завершить регистрацию",
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
        py={{ base: 8, md: 16 }}
        px={{ base: 3, sm: 4 }}
        fontFamily={AUTH_FONT_FAMILY}
        overflow="hidden"
      >
      <Box position="absolute" inset={0} pointerEvents="none" zIndex={0}>
        <Box
          position="absolute"
          top="-20%"
          right="-12%"
          width="52%"
          height="52%"
          background="radial-gradient(circle, rgba(239, 68, 68, 0.16) 0%, transparent 70%)"
          filter="blur(60px)"
        />
        <Box
          position="absolute"
          bottom="-18%"
          left="-8%"
          width="44%"
          height="44%"
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

        <Box position="relative" zIndex={1} w="full" px={{ base: 3, sm: 4 }}>
          <AuthFormCard as="form" onSubmit={handleSubmit} maxW="520px">
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
                  <Icon as={FaUserPlus} color={AUTH_THEME.accent} boxSize={4} />
                </Box>
                <Text fontSize={{ base: "xl", md: "2xl" }} fontWeight="500" color="white">
                  Создание аккаунта
                </Text>
              </HStack>
              <Text fontSize="sm" color={AUTH_THEME.mutedText}>
                Заполните поля, чтобы открыть доступ к рабочему пространству.
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
                      Ошибка регистрации
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
              helperText={!emailInvalid && softEmailDomainWarning ? softEmailDomainWarning : null}
              autoComplete="email"
            />

            <Box w="full">
              <PasswordInput
                id="password"
                label="Пароль"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Минимум 8 символов, буквы и цифры"
                isRequired
                autoComplete="new-password"
              />
              {password && <PasswordStrength password={password} />}
            </Box>

            <PasswordInput
              id="confirmPassword"
              label="Подтверждение пароля"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Повторите пароль"
              isRequired
              isInvalid={passwordsMismatch}
              errorMessage="Пароли не совпадают"
              autoComplete="new-password"
            />

            <Divider borderColor={AUTH_THEME.border} />

            <AuthInput
              id="firstName"
              label="Имя"
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              placeholder="Ваше имя"
              icon={FaUser}
              autoComplete="given-name"
            />

            <Button
              type="submit"
              w="full"
              isLoading={isLoading}
              isDisabled={
                emailInvalid ||
                !passwordStrongEnough ||
                passwordsMismatch ||
                !email ||
                !password ||
                !confirmPassword
              }
              leftIcon={<Icon as={FaUserPlus} />}
              {...AUTH_PRIMARY_BUTTON_SX}
            >
              {isLoading ? "Регистрация..." : "Создать аккаунт"}
            </Button>

            <Divider borderColor={AUTH_THEME.border} />

            <HStack spacing={1} justify="center" fontSize="sm">
              <Text color={AUTH_THEME.mutedText}>Уже есть аккаунт?</Text>
              <Link
                as={RouterLink}
                to="/login"
                color={AUTH_THEME.accent}
                fontWeight="500"
                _hover={{ color: AUTH_THEME.accentHover, textDecoration: "none" }}
              >
                Войти
              </Link>
            </HStack>
          </VStack>
          </AuthFormCard>
        </Box>
      </Box>
    </>
  );
}

export default SignUpPage;
