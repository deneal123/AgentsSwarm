import React, { useEffect, useState } from 'react';
import { Box, HStack, Text, VStack } from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { colors, borderRadius } from '@theme/tokens';

const MotionBox = motion(Box);

/**
 * TypingIndicator - Индикатор печати AI агента
 *
 * Показывает анимированные точки когда:
 * - AI обрабатывает сообщение
 * - AI генерирует ответ
 * - Выполняется фоновая задача
 */
function TypingIndicator({ agentName = "AI Агент", isVisible = false, message = "печатает..." }) {
  const [dots, setDots] = useState('');

  // Анимация точек
  useEffect(() => {
    if (!isVisible) {
      setDots('');
      return;
    }

    const interval = setInterval(() => {
      setDots(prev => {
        if (prev === '...') return '';
        return prev + '.';
      });
    }, 500);

    return () => clearInterval(interval);
  }, [isVisible]);

  if (!isVisible) return null;

  return (
    <MotionBox
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
      alignSelf="flex-start"
      maxW="200px"
    >
      <Box
        p={3}
        borderRadius={borderRadius.lg}
        bg="rgba(255,255,255,0.05)"
        border="1px solid rgba(255,255,255,0.1)"
        backdropFilter="blur(10px)"
      >
        <VStack align="start" spacing={2}>
          {/* Avatar и имя */}
          <HStack spacing={2}>
            <Box
              w={6}
              h={6}
              borderRadius="full"
              bg={`linear-gradient(135deg, ${colors.brand.primary}, ${colors.brand.secondary})`}
              display="flex"
              alignItems="center"
              justifyContent="center"
            >
              <Text fontSize="xs" fontWeight="bold" color="white">
                AI
              </Text>
            </Box>
            <Text fontSize="xs" color={colors.text.tertiary} fontWeight="medium">
              {agentName}
            </Text>
          </HStack>

          {/* Анимированные точки */}
          <HStack spacing={1} align="center">
            <Text color={colors.text.secondary} fontSize="sm">
              {message}
            </Text>
            <TypingDots />
          </HStack>
        </VStack>
      </Box>
    </MotionBox>
  );
}

// Компонент анимированных точек
function TypingDots() {
  return (
    <HStack spacing={1}>
      {[0, 1, 2].map((index) => (
        <MotionBox
          key={index}
          w={1}
          h={1}
          borderRadius="full"
          bg={colors.brand.primary}
          initial={{ opacity: 0.4 }}
          animate={{
            opacity: [0.4, 1, 0.4],
            scale: [1, 1.2, 1]
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            delay: index * 0.2,
            ease: "easeInOut"
          }}
        />
      ))}
    </HStack>
  );
}

// Компонент для отображения нескольких typing indicators
function MultiTypingIndicator({ typingUsers = [] }) {
  if (typingUsers.length === 0) return null;

  return (
    <VStack spacing={2} align="stretch">
      {typingUsers.map((userId) => (
        <TypingIndicator
          key={userId}
          agentName={`Агент ${userId}`}
          isVisible={true}
        />
      ))}
    </VStack>
  );
}

export default TypingIndicator;
export { MultiTypingIndicator };
