import React, { useMemo } from 'react';
import { MotionBox } from '@ui/motionPrimitives';
import { colors } from '@theme/tokens';

/**
 * FloatingParticles - Компонент с плавающими частицами для создания атмосферы
 *
 * Создает анимированные частицы, которые плавно перемещаются по экрану,
 * добавляя визуальную глубину и динамику интерфейсу.
 */
export function FloatingParticles({
  count = 20,
  colors: particleColors = [colors.brand.primary, colors.brand.secondary],
  size = 'sm',
  speed = 'medium',
  opacity = 0.1,
  blur = true
}) {
  // Размеры частиц в зависимости от пропса size
  const sizeMap = {
    xs: { min: 2, max: 4 },
    sm: { min: 3, max: 6 },
    md: { min: 4, max: 8 },
    lg: { min: 6, max: 12 }
  };

  // Скорости анимации
  const speedMap = {
    slow: { min: 20, max: 40 },
    medium: { min: 15, max: 30 },
    fast: { min: 10, max: 20 }
  };

  // Генерация частиц
  const particles = useMemo(() => {
    return Array.from({ length: count }, (_, i) => {
      const sizeRange = sizeMap[size];
      const speedRange = speedMap[speed];

      return {
        id: i,
        size: Math.random() * (sizeRange.max - sizeRange.min) + sizeRange.min,
        color: particleColors[Math.floor(Math.random() * particleColors.length)],
        x: Math.random() * 100,
        y: Math.random() * 100,
        duration: Math.random() * (speedRange.max - speedRange.min) + speedRange.min,
        delay: Math.random() * 5,
        direction: Math.random() > 0.5 ? 1 : -1
      };
    });
  }, [count, size, speed, particleColors]);

  return (
    <>
      {particles.map((particle) => (
        <MotionBox
          key={particle.id}
          position="absolute"
          left={`${particle.x}%`}
          top={`${particle.y}%`}
          w={`${particle.size}px`}
          h={`${particle.size}px`}
          bg={particle.color}
          borderRadius="50%"
          opacity={opacity}
          filter={blur ? 'blur(1px)' : 'none'}
          animate={{
            x: [0, particle.direction * 100, 0],
            y: [0, -50, 0],
            scale: [1, 1.2, 1],
            opacity: [opacity, opacity * 0.3, opacity]
          }}
          transition={{
            duration: particle.duration,
            repeat: Infinity,
            delay: particle.delay,
            ease: "easeInOut"
          }}
          pointerEvents="none"
        />
      ))}
    </>
  );
}

/**
 * FloatingOrbs - Более сложные плавающие сферы с градиентами
 *
 * Создает крупные сферические частицы с градиентными эффектами
 * для создания более dramatic визуального эффекта.
 */
export function FloatingOrbs({
  count = 5,
  size = 'lg',
  intensity = 'medium'
}) {
  const intensityMap = {
    subtle: {
      opacity: 0.05,
      blur: '20px',
      scale: [1, 1.1, 1]
    },
    medium: {
      opacity: 0.08,
      blur: '30px',
      scale: [1, 1.3, 1]
    },
    strong: {
      opacity: 0.12,
      blur: '40px',
      scale: [1, 1.5, 1]
    }
  };

  const settings = intensityMap[intensity];

  const orbs = useMemo(() => {
    return Array.from({ length: count }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      duration: 15 + Math.random() * 10,
      delay: Math.random() * 5,
      gradient: `radial-gradient(circle, ${colors.brand.primary}${Math.floor(Math.random() * 30 + 20).toString(16).padStart(2, '0')} 0%, transparent 70%)`
    }));
  }, [count]);

  return (
    <>
      {orbs.map((orb) => (
        <MotionBox
          key={orb.id}
          position="absolute"
          left={`${orb.x}%`}
          top={`${orb.y}%`}
          w={`${size === 'lg' ? 200 : 150}px`}
          h={`${size === 'lg' ? 200 : 150}px`}
          bg={orb.gradient}
          borderRadius="50%"
          opacity={settings.opacity}
          filter={`blur(${settings.blur})`}
          animate={{
            x: [0, 50, -30, 0],
            y: [0, -40, 60, 0],
            scale: settings.scale
          }}
          transition={{
            duration: orb.duration,
            repeat: Infinity,
            delay: orb.delay,
            ease: "easeInOut"
          }}
          pointerEvents="none"
        />
      ))}
    </>
  );
}
