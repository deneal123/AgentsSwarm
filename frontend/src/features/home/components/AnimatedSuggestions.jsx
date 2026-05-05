import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Box, Text } from '@chakra-ui/react';
import { MotionBox } from '@ui/motionPrimitives';
import { colors, borderRadius } from '@theme/tokens';
import { keyframes } from '@emotion/react';

// Анимированные подсказки, появляющиеся в разных местах
function AnimatedSuggestions({ suggestions, onSuggestionClick }) {
  const [visibleSuggestions, setVisibleSuggestions] = useState([]);
  const containerRef = useRef(null);
  const animationRef = useRef(null);

  // Позиции для подсказок - равномерно распределены, не слишком низко
  const positions = useMemo(() => [
    { x: '12%', y: '18%', transform: 'translateX(0%)' }, // Левый верх
    { x: '50%', y: '12%', transform: 'translateX(-50%)' }, // Центр верх
    { x: '88%', y: '18%', transform: 'translateX(-100%)' }, // Правый верх
    { x: '22%', y: '45%', transform: 'translateX(-15%)' }, // Левый центр
    { x: '78%', y: '42%', transform: 'translateX(-85%)' }, // Правый центр
    { x: '50%', y: '65%', transform: 'translateX(-50%)' }, // Центр низ
  ], []);

  useEffect(() => {
    let suggestionIndex = 0;
    let positionIndex = 0;

    const showNextSuggestion = () => {
      if (suggestionIndex >= suggestions.length) {
        suggestionIndex = 0; // Зацикливаем
      }

      const suggestion = suggestions[suggestionIndex];
      const position = positions[positionIndex % positions.length];

      const newSuggestion = {
        id: `${suggestion}_${Date.now()}`,
        text: suggestion,
        position,
        timestamp: Date.now(),
        positionIndex
      };

      setVisibleSuggestions(prev => {
        // Удаляем старые подсказки (старше 3 секунд)
        const filtered = prev.filter(s => Date.now() - s.timestamp < 3000);
        // Ограничиваем количество одновременно видимых подсказок до 3
        const limited = filtered.length >= 3 ? filtered.slice(-2) : filtered;
        return [...limited, newSuggestion];
      });

      suggestionIndex++;
      positionIndex++;
    };

    // Показываем первую подсказку сразу с небольшой задержкой
    setTimeout(showNextSuggestion, 1200);

    // Затем показываем остальные через интервалы с небольшим разбросом
    animationRef.current = setInterval(showNextSuggestion, 3800 + Math.random() * 400);

    return () => {
      if (animationRef.current) {
        clearInterval(animationRef.current);
      }
    };
  }, [suggestions, positions]);

  return (
    <Box
      ref={containerRef}
      position="relative"
      w="calc(100% + 40px)"
      h="250px"
      overflow="visible"
      mx="-20px"
      mt="-20px"
      mb="-10px"
    >
      {visibleSuggestions.map((suggestion) => (
        <SuggestionBubble
          key={suggestion.id}
          suggestion={suggestion}
          onClick={() => onSuggestionClick(suggestion.text)}
        />
      ))}
    </Box>
  );
}

// Отдельный компонент для подсказки
function SuggestionBubble({ suggestion, onClick }) {
  const [isHovered, setIsHovered] = useState(false);
  const [adjustedPosition, setAdjustedPosition] = useState(suggestion.position);
  const bubbleRef = useRef(null);

  // Корректировка позиции чтобы избежать обрезки
  useEffect(() => {
    if (bubbleRef.current) {
      const bubble = bubbleRef.current;
      const rect = bubble.getBoundingClientRect();
      const container = bubble.parentElement?.parentElement;
      const containerRect = container?.getBoundingClientRect();

      if (containerRect) {
        let newTransform = suggestion.position.transform;

        // Проверяем границы контейнера
        if (rect.right > containerRect.right - 20) {
          newTransform = 'translateX(-100%)';
        } else if (rect.left < containerRect.left + 20) {
          newTransform = 'translateX(0%)';
        }

        // Проверяем верхнюю границу
        if (rect.top < containerRect.top + 20) {
          // Если слишком близко к верху, можем скорректировать вертикальную позицию
          // Но пока оставим как есть, так как вертикальное позиционирование сложнее
        }

        if (newTransform !== suggestion.position.transform) {
          setAdjustedPosition({
            ...suggestion.position,
            transform: newTransform
          });
        }
      }
    }
  }, [suggestion.position]);

  // Анимация пульсации
  const pulseAnimation = keyframes`
    0%, 100% {
      transform: scale(1);
      opacity: 0.7;
    }
    50% {
      transform: scale(1.05);
      opacity: 1;
    }
  `;

  // Время жизни подсказки
  const age = Date.now() - suggestion.timestamp;
  const progress = Math.min(age / 3000, 1); // 3 секунды жизни
  const opacity = 1 - progress * 0.4; // Более плавное исчезновение

  return (
    <MotionBox
      ref={bubbleRef}
      position="absolute"
      left={adjustedPosition.x}
      top={adjustedPosition.y}
      transform={adjustedPosition.transform}
      zIndex={suggestion.timestamp % 10}
      initial={{ opacity: 0, scale: 0.9, y: 5 }}
      animate={{
        opacity: opacity,
        scale: isHovered ? 1.0 : 1,
        y: isHovered ? -1 : 0
      }}
      exit={{ opacity: 0, scale: 0.9, y: 5 }}
      transition={{
        duration: 0.3,
        ease: "easeOut",
        scale: { type: "spring", stiffness: 400, damping: 30 }
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
      cursor="pointer"
    >
      <Box
        bg="rgba(255,255,255,0.08)"
        backdropFilter="blur(15px)"
        border="1px solid rgba(255,255,255,0.1)"
        borderRadius={borderRadius.lg}
        px={4}
        py={3}
        maxW="200px"
        boxShadow="0 8px 32px rgba(0,0,0,0.2)"
        animation={`${pulseAnimation} 3s ease-in-out infinite`}
        _hover={{
          bg: "rgba(255,255,255,0.12)",
          borderColor: colors.brand.primary,
          boxShadow: `0 8px 32px ${colors.brand.primary}20`
        }}
        transition="all 0.3s ease"
      >
        <Text
          fontSize="sm"
          color={colors.text.secondary}
          textAlign="center"
          lineHeight="1.4"
          fontWeight={400}
          _hover={{ color: colors.text.primary }}
        >
          {suggestion.text}
        </Text>

        {/* Анимированная стрелка */}
        <Box
          position="absolute"
          bottom="-6px"
          left="50%"
          transform="translateX(-50%)"
          w={0}
          h={0}
          borderLeft="6px solid transparent"
          borderRight="6px solid transparent"
          borderTop={`6px solid rgba(255,255,255,0.1)`}
          opacity={0.6}
        />
      </Box>
    </MotionBox>
  );
}

export default AnimatedSuggestions;
