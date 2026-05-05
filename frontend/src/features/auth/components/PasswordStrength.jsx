import React from "react";
import { Box, HStack, VStack, Text, Icon, usePrefersReducedMotion } from "@chakra-ui/react";
import { CheckCircleIcon, WarningIcon } from "@chakra-ui/icons";
import { keyframes } from "@emotion/react";
import { motion } from "framer-motion";
import { colors, borderRadius } from "@theme/tokens";

const MotionBox = motion(Box);

const pulse = keyframes`
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
`;

const shimmer = keyframes`
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
`;

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -15, scale: 0.95 },
  visible: {
    opacity: 1,
    x: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 150, damping: 15 },
  },
};

/**
 * PasswordStrength - индикатор силы пароля с проверками
 * Анимированные требования с иконками
 */
const PasswordStrength = ({ password }) => {
  const prefersReducedMotion = usePrefersReducedMotion();

  const checks = [
    {
      id: "length",
      label: "Минимум 8 символов",
      test: (pwd) => pwd.length >= 8,
    },
    {
      id: "letter",
      label: "Хотя бы одна буква",
      test: (pwd) => /[A-Za-zА-Яа-я]/.test(pwd),
    },
    {
      id: "digit",
      label: "Хотя бы одна цифра",
      test: (pwd) => /\d/.test(pwd),
    },
  ];

  const passedChecks = checks.filter((check) => check.test(password));
  const strengthPercentage = (passedChecks.length / checks.length) * 100;

  // Цвет прогресса в зависимости от силы
  const getProgressColor = () => {
    if (passedChecks.length === 0) return colors.text.tertiary;
    if (passedChecks.length === 1) return "#EF4444"; // red
    if (passedChecks.length === 2) return "#F59E0B"; // orange
    return "#00FF88"; // green
  };

  const getStrengthLabel = () => {
    if (passedChecks.length <= 1) return "Слабый";
    if (passedChecks.length === 2) return "Средний";
    return "Сильный";
  };

  const progressColor = getProgressColor();

  return (
    <MotionBox
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, type: "spring", stiffness: 100 }}
      mt={3}
      p={4}
      bg="rgba(6, 8, 15, 0.6)"
      borderRadius={borderRadius.lg}
      border="1px solid rgba(255, 255, 255, 0.08)"
      position="relative"
      overflow="hidden"
      _before={{
        content: '""',
        position: "absolute",
        top: 0,
        left: 0,
        width: "3px",
        height: "100%",
        background: progressColor,
        opacity: 0.8,
        transition: "background 0.3s ease",
      }}
    >
      {/* Background glow based on strength */}
      <Box
        position="absolute"
        top="-50%"
        right="-30%"
        width="150px"
        height="150px"
        background={`radial-gradient(circle, ${progressColor}20 0%, transparent 70%)`}
        filter="blur(40px)"
        transition="all 0.3s ease"
        pointerEvents="none"
      />

      {/* Progress bar section */}
      <Box mb={4} position="relative" zIndex={1}>
        <HStack justify="space-between" mb={2}>
          <Text fontSize="xs" color={colors.text.secondary}>
            Сила пароля
          </Text>
          <HStack spacing={1}>
            <Box
              w={2}
              h={2}
              borderRadius="full"
              bg={progressColor}
              animation={
                passedChecks.length === 3 && !prefersReducedMotion
                  ? `${pulse} 1.5s ease-in-out infinite`
                  : "none"
              }
            />
            <Text fontSize="xs" color={progressColor} fontWeight="600" transition="color 0.3s ease">
              {getStrengthLabel()}
            </Text>
          </HStack>
        </HStack>

        {/* Animated progress bar */}
        <Box
          h="6px"
          borderRadius="full"
          bg="rgba(255, 255, 255, 0.05)"
          overflow="hidden"
          position="relative"
        >
          <MotionBox
            initial={{ scaleX: 0 }}
            animate={{ scaleX: strengthPercentage / 100 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            h="100%"
            w="100%"
            borderRadius="full"
            background={`linear-gradient(90deg, ${progressColor}, ${progressColor}CC)`}
            position="relative"
            style={{ transformOrigin: "left", willChange: "transform" }}
            _after={{
              content: '""',
              position: "absolute",
              inset: 0,
              background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent)",
              backgroundSize: "200% 100%",
              animation: prefersReducedMotion ? "none" : `${shimmer} 2s linear infinite`,
            }}
          />
        </Box>
      </Box>

      {/* Requirements list */}
      <MotionBox variants={containerVariants} initial="hidden" animate="visible">
        <VStack align="stretch" spacing={2}>
          {checks.map((check) => {
            const passed = check.test(password);
            return (
              <MotionBox key={check.id} variants={itemVariants}>
                <HStack
                  spacing={3}
                  p={2}
                  borderRadius={borderRadius.md}
                  bg={passed ? "rgba(0, 255, 136, 0.05)" : "transparent"}
                  border="1px solid"
                  borderColor={passed ? "rgba(0, 255, 136, 0.2)" : "transparent"}
                  transition="all 0.2s ease"
                >
                  <Box
                    w={5}
                    h={5}
                    borderRadius="full"
                    bg={passed ? "rgba(0, 255, 136, 0.15)" : "rgba(255, 255, 255, 0.05)"}
                    display="flex"
                    alignItems="center"
                    justifyContent="center"
                    transition="all 0.2s ease"
                  >
                    <Icon
                      as={passed ? CheckCircleIcon : WarningIcon}
                      color={passed ? "#00FF88" : colors.text.tertiary}
                      w={3}
                      h={3}
                      transition="color 0.2s"
                    />
                  </Box>
                  <Text
                    fontSize="xs"
                    color={passed ? colors.text.primary : colors.text.tertiary}
                    fontWeight={passed ? "500" : "400"}
                    transition="all 0.2s ease"
                  >
                    {check.label}
                  </Text>
                  {passed && (
                    <MotionBox
                      initial={{ scale: 0, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ type: "spring", stiffness: 300, damping: 15 }}
                      ml="auto"
                    >
                      <Box
                        px={2}
                        py={0.5}
                        borderRadius="full"
                        bg="rgba(0, 255, 136, 0.1)"
                        border="1px solid rgba(0, 255, 136, 0.2)"
                      >
                        <Text fontSize="10px" color="#00FF88" fontWeight="600">
                          ✓
                        </Text>
                      </Box>
                    </MotionBox>
                  )}
                </HStack>
              </MotionBox>
            );
          })}
        </VStack>
      </MotionBox>
    </MotionBox>
  );
};

export default PasswordStrength;
