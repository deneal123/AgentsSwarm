import React, { useMemo, useState } from "react";
import { Box, Button, Divider, HStack, Icon, Link, Text, VStack } from "@chakra-ui/react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { EmailIcon } from "@chakra-ui/icons";
import { FaExclamationCircle, FaUser, FaUserPlus } from "react-icons/fa";
import { registerUser } from "@api";
import { AuthFormCard, AuthInput, AuthPageHeader, AuthPageShell, PasswordInput, PasswordStrength } from "@features/auth";
import { AUTH_PRIMARY_BUTTON_SX } from "@features/auth";
import { borderRadius } from "@theme/tokens";
import { AUTH_THEME } from "@features/auth";
import extractErrorInfo from "@utils/errorHandler";

export default function SignupWidget() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const emailInvalid = email.length > 0 && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  const emailDomain = useMemo(() => (email.includes("@") ? email.split("@")[1] : ""), [email]);
  const softEmailDomainWarning = useMemo(() => { if (!email || emailInvalid) return ""; if (!emailDomain.includes(".")) return "Проверьте домен e-mail (отсутствует точка)"; const suspiciousTlds = ["invalid", "example", "local", "test"]; const tld = emailDomain.split(".").pop()?.toLowerCase(); return tld && suspiciousTlds.includes(tld) ? "Похоже на тестовый домен — убедитесь, что он корректен" : ""; }, [email, emailDomain, emailInvalid]);
  const hasMinLen = password.length >= 8;
  const hasLetter = /[A-Za-zА-Яа-я]/.test(password);
  const hasDigit = /\d/.test(password);
  const passwordsMismatch = password && confirmPassword && password !== confirmPassword;
  const passwordStrongEnough = hasMinLen && hasLetter && hasDigit;
  const handleSubmit = async (event) => { event.preventDefault(); setError(null); if (emailInvalid || !passwordStrongEnough || passwordsMismatch) return; setIsLoading(true); try { await registerUser({ email, password, first_name: firstName || null }); navigate("/login", { replace: true }); } catch (err) { const { userMessage } = extractErrorInfo(err, { fallbackMessage: "Не удалось завершить регистрацию" }); setError(userMessage); } finally { setIsLoading(false); } };
  return <AuthPageShell><Box position="relative" zIndex={1} w="full" px={{ base: 3, sm: 4 }}><AuthFormCard as="form" onSubmit={handleSubmit} maxW="520px"><VStack w="full" align="stretch" spacing={5}><AuthPageHeader icon={FaUserPlus} title="Создание аккаунта" description="Заполните поля, чтобы открыть доступ к рабочему пространству." />{error && <Box p={3} bg="rgba(239, 68, 68, 0.12)" border="1px solid rgba(239, 68, 68, 0.35)" borderRadius={borderRadius.lg}><HStack spacing={2} align="start"><Icon as={FaExclamationCircle} color={AUTH_THEME.accent} mt="2px" /><VStack align="start" spacing={0}><Text fontSize="sm" fontWeight="500" color={AUTH_THEME.accent}>Ошибка регистрации</Text><Text fontSize="xs" color={AUTH_THEME.mutedText}>{error}</Text></VStack></HStack></Box>}<AuthInput id="email" label="E-mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" icon={EmailIcon} isRequired isInvalid={emailInvalid} errorMessage="Неверный формат e-mail" helperText={!emailInvalid && softEmailDomainWarning ? softEmailDomainWarning : null} autoComplete="email" /><Box w="full"><PasswordInput id="password" label="Пароль" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Минимум 8 символов, буквы и цифры" isRequired autoComplete="new-password" />{password && <PasswordStrength password={password} />}</Box><PasswordInput id="confirmPassword" label="Подтверждение пароля" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Повторите пароль" isRequired isInvalid={passwordsMismatch} errorMessage="Пароли не совпадают" autoComplete="new-password" /><Divider borderColor={AUTH_THEME.border} /><AuthInput id="firstName" label="Имя" type="text" value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder="Ваше имя" icon={FaUser} autoComplete="given-name" /><Button type="submit" w="full" isLoading={isLoading} isDisabled={emailInvalid || !passwordStrongEnough || passwordsMismatch || !email || !password || !confirmPassword} leftIcon={<Icon as={FaUserPlus} />} {...AUTH_PRIMARY_BUTTON_SX}>{isLoading ? "Регистрация..." : "Создать аккаунт"}</Button><Divider borderColor={AUTH_THEME.border} /><HStack spacing={1} justify="center" fontSize="sm"><Text color={AUTH_THEME.mutedText}>Уже есть аккаунт?</Text><Link as={RouterLink} to="/login" color={AUTH_THEME.accent} fontWeight="500" _hover={{ color: AUTH_THEME.accentHover, textDecoration: "none" }}>Войти</Link></HStack></VStack></AuthFormCard></Box></AuthPageShell>;
}
