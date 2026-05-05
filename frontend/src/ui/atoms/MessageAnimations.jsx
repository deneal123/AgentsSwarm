import React from 'react';
import { MotionBox, MotionVStack } from '@ui/motionPrimitives';
import { Box, VStack, HStack, Spinner } from '@chakra-ui/react';
import { colors } from '@theme/tokens';

/**
 * MessageEntrance - Анимированный вход сообщений с эффектом появления
 *
 * Поддерживает разные направления и задержки для создания
 * естественного потока сообщений в чате.
 */
export function MessageEntrance({
  children,
  delay = 0,
  direction = 'up',
  stagger = false,
  staggerChildren = 0.1
}) {
  const directionMap = {
    up: { y: 20 },
    down: { y: -20 },
    left: { x: 20 },
    right: { x: -20 },
    scale: { scale: 0.9 }
  };

  const initialOffset = directionMap[direction] || directionMap.up;

  const containerVariants = stagger ? {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: staggerChildren,
        delayChildren: delay
      }
    }
  } : {};

  const itemVariants = {
    hidden: {
      opacity: 0,
      ...initialOffset
    },
    visible: {
      opacity: 1,
      x: 0,
      y: 0,
      scale: 1,
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 24,
        delay: delay
      }
    }
  };

  if (stagger) {
    return (
      <MotionVStack
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        spacing={2}
      >
        {React.Children.map(children, (child) => (
          <MotionBox variants={itemVariants}>
            {child}
          </MotionBox>
        ))}
      </MotionVStack>
    );
  }

  return (
    <MotionBox
      initial={{
        opacity: 0,
        ...initialOffset
      }}
      animate={{
        opacity: 1,
        x: 0,
        y: 0,
        scale: 1
      }}
      transition={{
        type: "spring",
        stiffness: 300,
        damping: 24,
        delay
      }}
    >
      {children}
    </MotionBox>
  );
}

/**
 * TypingPulse - Анимированный индикатор печати
 *
 * Создает пульсирующий эффект для показа активности агента
 * с настраиваемой интенсивностью и стилем.
 */
export function TypingPulse({
  isActive = true,
  size = 'md',
  intensity = 'medium',
  style = 'dots'
}) {
  const sizeMap = {
    sm: { container: 16, dot: 3 },
    md: { container: 24, dot: 4 },
    lg: { container: 32, dot: 5 }
  };

  const intensityMap = {
    subtle: {
      scale: [1, 1.1, 1],
      opacity: [0.6, 0.9, 0.6]
    },
    medium: {
      scale: [1, 1.2, 1],
      opacity: [0.4, 1, 0.4]
    },
    strong: {
      scale: [1, 1.4, 1],
      opacity: [0.3, 1, 0.3]
    }
  };

  const settings = {
    size: sizeMap[size],
    intensity: intensityMap[intensity]
  };

  if (style === 'spinner') {
    return (
      <MotionBox
        animate={isActive ? { rotate: 360 } : {}}
        transition={{
          duration: 1,
          repeat: isActive ? Infinity : 0,
          ease: "linear"
        }}
      >
        <Spinner size={size} color={colors.brand.primary} />
      </MotionBox>
    );
  }

  if (style === 'pulse') {
    return (
      <MotionBox
        w={`${settings.size.container}px`}
        h={`${settings.size.container}px`}
        bg={colors.brand.primary}
        borderRadius="50%"
        animate={isActive ? settings.intensity : {}}
        transition={{
          duration: 1.5,
          repeat: isActive ? Infinity : 0,
          ease: "easeInOut"
        }}
        opacity={isActive ? 0.8 : 0.3}
      />
    );
  }

  // Default dots style
  return (
    <HStack spacing={1} h={`${settings.size.container}px`} align="center">
      {[0, 1, 2].map((i) => (
        <MotionBox
          key={i}
          w={`${settings.size.dot}px`}
          h={`${settings.size.dot}px`}
          bg={colors.brand.primary}
          borderRadius="50%"
          animate={isActive ? {
            scale: settings.intensity.scale,
            opacity: settings.intensity.opacity
          } : {}}
          transition={{
            duration: 1.5,
            repeat: isActive ? Infinity : 0,
            delay: i * 0.2,
            ease: "easeInOut"
          }}
        />
      ))}
    </HStack>
  );
}

/**
 * MessageReaction - Анимированная реакция на сообщение
 *
 * Показывает реакции (лайки, дизлайки) с плавными анимациями появления
 */
export function MessageReaction({
  children,
  trigger = false,
  type = 'bounce'
}) {
  const reactionVariants = {
    bounce: {
      scale: [1, 1.3, 1],
      rotate: [0, 10, -10, 0],
      transition: { duration: 0.6 }
    },
    pop: {
      scale: [0, 1.2, 1],
      transition: { type: "spring", stiffness: 400, damping: 10 }
    },
    shake: {
      x: [0, -5, 5, -5, 5, 0],
      transition: { duration: 0.5 }
    }
  };

  return (
    <MotionBox
      animate={trigger ? reactionVariants[type] : {}}
      whileHover={{ scale: 1.1 }}
      whileTap={{ scale: 0.95 }}
      cursor="pointer"
    >
      {children}
    </MotionBox>
  );
}

/**
 * MessageStagger - Групповая анимация сообщений
 *
 * Создает эффект последовательного появления группы сообщений
 * для создания более естественного чата.
 */
export function MessageStagger({ children, staggerDelay = 0.1 }) {
  return (
    <MotionVStack
      spacing={3}
      initial="hidden"
      animate="visible"
      variants={{
        hidden: { opacity: 0 },
        visible: {
          opacity: 1,
          transition: {
            staggerChildren: staggerDelay
          }
        }
      }}
    >
      {React.Children.map(children, (child) => (
        <MotionBox
          variants={{
            hidden: { opacity: 0, y: 20 },
            visible: {
              opacity: 1,
              y: 0,
              transition: {
                type: "spring",
                stiffness: 300,
                damping: 24
              }
            }
          }}
        >
          {child}
        </MotionBox>
      ))}
    </MotionVStack>
  );
}

/**
 * SlideInMessage - Сообщение с эффектом скольжения
 *
 * Анимирует появление сообщения с эффектом скольжения
 * из-за края экрана.
 */
export function SlideInMessage({
  children,
  direction = 'right',
  delay = 0,
  distance = 100
}) {
  const directionMap = {
    left: { x: -distance },
    right: { x: distance },
    up: { y: distance },
    down: { y: -distance }
  };

  const initialOffset = directionMap[direction] || directionMap.right;

  return (
    <MotionBox
      initial={{
        opacity: 0,
        ...initialOffset
      }}
      animate={{
        opacity: 1,
        x: 0,
        y: 0
      }}
      transition={{
        type: "spring",
        stiffness: 200,
        damping: 20,
        delay
      }}
    >
      {children}
    </MotionBox>
  );
}
