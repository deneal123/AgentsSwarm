import React from 'react';
import { Box } from '@chakra-ui/react';
import { ParticlesBackground } from '@shared/ui/atoms';
import { FloatingOrbs } from '@shared/ui/atoms';
import { colors, gradients } from '@theme/tokens';
import { keyframes } from '@emotion/react';

// Анимированные keyframes
const float = keyframes`
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  33% { transform: translateY(-10px) rotate(1deg); }
  66% { transform: translateY(5px) rotate(-0.5deg); }
`;

const glow = keyframes`
  0%, 100% {
    opacity: 0.3;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.1);
  }
`;

/**
 * HeroBackground - Фон главной страницы с частицами и эффектами
 *
 * Создает атмосферу для минималистичного интерфейса поиска:
 * - ParticlesBackground с коннекциями
 * - FloatingOrbs для динамики
 * - Градиентные оверлеи
 * - Grid паттерн
 */
function HeroBackground() {
  return (
    <Box
      position="absolute"
      inset={0}
      w="100%"
      h="100%"
      overflow="hidden"
      zIndex={0}
    >
      {/* Основной градиентный фон */}
      <Box
        position="absolute"
        inset={0}
        bg={gradients.aurora}
        opacity={0.3}
      />

      {/* Частицы */}
      <ParticlesBackground
        particleCount={150}
        connectionDistance={200}
        speed={0.4}
        particleColor={colors.brand.primary}
        opacity={0.8}
      />

      {/* Плавающие сферы */}
      <FloatingOrbs count={4} />

      {/* Дополнительные эффекты */}
      <Box
        position="absolute"
        top="20%"
        left="10%"
        w="200px"
        h="200px"
        borderRadius="full"
        bg={`radial-gradient(circle, ${colors.brand.secondary}20, transparent)`}
        filter="blur(40px)"
        animation={`${float} 8s ease-in-out infinite`}
      />

      <Box
        position="absolute"
        bottom="30%"
        right="15%"
        w="150px"
        h="150px"
        borderRadius="full"
        bg={`radial-gradient(circle, ${colors.brand.tertiary}15, transparent)`}
        filter="blur(30px)"
        animation={`${float} 6s ease-in-out infinite reverse`}
      />

      <Box
        position="absolute"
        top="60%"
        left="70%"
        w="100px"
        h="100px"
        borderRadius="full"
        bg={`radial-gradient(circle, ${colors.brand.primary}10, transparent)`}
        filter="blur(25px)"
        animation={`${glow} 10s ease-in-out infinite`}
      />

      {/* Grid паттерн */}
      <Box
        position="absolute"
        inset={0}
        backgroundImage="radial-gradient(circle at 1px 1px, rgba(255,255,255,0.02) 1px, transparent 0)"
        backgroundSize="30px 30px"
        opacity={0.3}
        pointerEvents="none"
      />

      {/* Subtle vignette effect */}
      <Box
        position="absolute"
        inset={0}
        bg="radial-gradient(circle at center, transparent 40%, rgba(0,0,0,0.1) 100%)"
        pointerEvents="none"
      />
    </Box>
  );
}

export default HeroBackground;
