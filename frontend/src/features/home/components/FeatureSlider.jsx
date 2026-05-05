import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Badge,
  Box,
  Button,
  Flex,
  HStack,
  Stack,
  Icon,
  usePrefersReducedMotion,
} from "@chakra-ui/react";
import { MotionBox } from "@ui/motionPrimitives";
import { colors, borderRadius, gradients } from "@theme/tokens";
import { Subtitle, Body } from "@ui/atoms/Typography";
import PrimaryButton from "@ui/atoms/PrimaryButton";
import FeatureBadge from "@ui/atoms/FeatureBadge";
import { GradientText } from "@ui/atoms/AnimatedText";
import { FEATURE_SLIDES } from "@constants";
import { keyframes } from "@emotion/react";
import {
  FaDatabase,
  FaRocket,
  FaCubes,
  FaChartLine,
  FaShieldAlt,
  FaArrowLeft,
  FaArrowRight,
} from "react-icons/fa";

const slideIcons = {
  1: FaDatabase,
  2: FaRocket,
  3: FaCubes,
  4: FaChartLine,
  5: FaShieldAlt,
};

const SLIDE_TRANSITION = { duration: 0.85, ease: "easeInOut" };

const pulse = keyframes`
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.1); }
`;

const float = keyframes`
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
`;

function featureTransforms(offset) {
  if (offset === 0) {
    return {
      x: "0%",
      scale: 1,
      rotateY: 0,
      opacity: 1,
      filter: "blur(0px)",
      zIndex: 3,
    };
  }

  if (offset === 1) {
    return {
      x: "55%",
      scale: 0.82,
      rotateY: -20,
      opacity: 0.35,
      filter: "blur(3px)",
      zIndex: 2,
    };
  }

  if (offset === FEATURE_SLIDES.length - 1) {
    return {
      x: "-55%",
      scale: 0.82,
      rotateY: 20,
      opacity: 0.35,
      filter: "blur(3px)",
      zIndex: 2,
    };
  }

  return {
    x: "0%",
    scale: 0.7,
    rotateY: 0,
    opacity: 0,
    filter: "blur(6px)",
    zIndex: 1,
  };
}

export default function FeatureSlider() {
  const [index, setIndex] = useState(0);
  const [isPaused, setPaused] = useState(false);
  const [touchStart, setTouchStart] = useState(null);
  const [touchEnd, setTouchEnd] = useState(null);
  const prefersReducedMotion = usePrefersReducedMotion();
  const motionEnabled = !prefersReducedMotion;

  // Минимальное расстояние свайпа (в пикселях)
  const minSwipeDistance = 50;

  // Переход к конкретному слайду по индексу
  const goToSlide = useCallback((slideIndex) => {
    const length = FEATURE_SLIDES.length;
    setIndex(((slideIndex % length) + length) % length);
  }, []);

  // Переход на следующий/предыдущий слайд (смещение)
  const goByOffset = useCallback((offset) => {
    setIndex((prev) => {
      const length = FEATURE_SLIDES.length;
      return (((prev + offset) % length) + length) % length;
    });
  }, []);

  const onTouchStart = (e) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const onTouchMove = (e) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const onTouchEnd = () => {
    if (!touchStart || !touchEnd) return;

    const distance = touchStart - touchEnd;
    const isLeftSwipe = distance > minSwipeDistance;
    const isRightSwipe = distance < -minSwipeDistance;

    if (isLeftSwipe) {
      goByOffset(1);
    } else if (isRightSwipe) {
      goByOffset(-1);
    }

    // Сброс состояний для следующего свайпа
    setTouchStart(null);
    setTouchEnd(null);
  };

  useEffect(() => {
    if (!motionEnabled || isPaused || FEATURE_SLIDES.length <= 1) return undefined;
    const id = setInterval(() => goByOffset(1), 3500);
    return () => clearInterval(id);
  }, [goByOffset, isPaused, motionEnabled]);

  const indicators = useMemo(
    () =>
      FEATURE_SLIDES.map((slide, slideIdx) => (
        <MotionBox
          key={slide.id}
          whileHover={motionEnabled ? { scale: 1.2 } : undefined}
          whileTap={motionEnabled ? { scale: 0.9 } : undefined}
        >
          <Button
            size="xs"
            minW="auto"
            w={slideIdx === index ? "32px" : "10px"}
            h="10px"
            borderRadius="full"
            bg={
              slideIdx === index
                ? `linear-gradient(90deg, ${colors.brand.primary}, ${colors.brand.secondary})`
                : "rgba(255,255,255,0.15)"
            }
            border="1px solid"
            borderColor={slideIdx === index ? "transparent" : "rgba(255,255,255,0.1)"}
            boxShadow={slideIdx === index ? `0 0 15px ${colors.brand.primary}60` : undefined}
            _hover={{
              bg:
                slideIdx === index
                  ? `linear-gradient(90deg, ${colors.brand.primary}, ${colors.brand.secondary})`
                  : "rgba(255,255,255,0.25)",
            }}
            onClick={() => goToSlide(slideIdx)}
            aria-label={`Перейти к слайду ${slideIdx + 1}`}
            transition="all 0.4s ease"
            p={0}
          />
        </MotionBox>
      )),
    [goToSlide, index, motionEnabled],
  );

  return (
    <Stack spacing={{ base: 8, md: 12 }} align="center" w="full" position="relative">
      {/* Background effects */}
      <Box
        position="absolute"
        inset="-50%"
        background={gradients.horizon}
        opacity={0.1}
        filter="blur(180px)"
        pointerEvents="none"
      />

      {/* Animated orbs */}
      <Box
        position="absolute"
        top="-20%"
        left="10%"
        w="300px"
        h="300px"
        borderRadius="full"
        bg={`radial-gradient(circle, ${colors.brand.primary}15 0%, transparent 70%)`}
        filter="blur(60px)"
        animation={motionEnabled ? `${pulse} 6s ease-in-out infinite` : "none"}
        pointerEvents="none"
      />
      <Box
        position="absolute"
        bottom="-10%"
        right="5%"
        w="250px"
        h="250px"
        borderRadius="full"
        bg={`radial-gradient(circle, ${colors.brand.secondary}15 0%, transparent 70%)`}
        filter="blur(60px)"
        animation={motionEnabled ? `${pulse} 8s ease-in-out infinite` : "none"}
        style={{ animationDelay: "2s" }}
        pointerEvents="none"
      />

      {/* Header */}
      <MotionBox
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        textAlign="center"
        w="full"
        position="relative"
        zIndex={1}
      >
        <FeatureBadge mb={4}>✨ Возможности платформы</FeatureBadge>
        <Subtitle variant="large" fontSize={{ base: "28px", md: "38px" }} mb={3} fontWeight={600}>
          <GradientText>Всё необходимое в одном интерфейсе</GradientText>
        </Subtitle>
        <Body
          variant="medium"
          color={colors.text.tertiary}
          maxW="800px"
          mx="auto"
          fontSize={{ base: "14px", md: "16px" }}
          lineHeight="1.7"
        >
          Интерактивный тур по ключевым функциям: от обучения моделей до мониторинга.
        </Body>
      </MotionBox>

      <Box
        position="relative"
        w="full"
        maxW="1400px"
        mx="auto"
        px={{ base: 4, md: 8, lg: 12 }}
        overflow="hidden"
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        {/* Navigation arrows */}
        <HStack
          position="absolute"
          top="50%"
          left={{ base: 2, md: 4 }}
          right={{ base: 2, md: 4 }}
          transform="translateY(-50%)"
          justify="space-between"
          zIndex={10}
          pointerEvents="none"
        >
          <MotionBox
            whileHover={motionEnabled ? { scale: 1.1 } : undefined}
            whileTap={motionEnabled ? { scale: 0.9 } : undefined}
            pointerEvents="auto"
          >
            <Button
              onClick={() => goByOffset(-1)}
              size="lg"
              borderRadius="full"
              bg="rgba(0,0,0,0.5)"
              border="1px solid rgba(255,255,255,0.1)"
              backdropFilter="blur(10px)"
              _hover={{ bg: "rgba(0,0,0,0.7)", borderColor: colors.brand.primary }}
              p={3}
            >
              <Icon as={FaArrowLeft} boxSize={4} color={colors.text.primary} />
            </Button>
          </MotionBox>
          <MotionBox
            whileHover={motionEnabled ? { scale: 1.1 } : undefined}
            whileTap={motionEnabled ? { scale: 0.9 } : undefined}
            pointerEvents="auto"
          >
            <Button
              onClick={() => goByOffset(1)}
              size="lg"
              borderRadius="full"
              bg="rgba(0,0,0,0.5)"
              border="1px solid rgba(255,255,255,0.1)"
              backdropFilter="blur(10px)"
              _hover={{ bg: "rgba(0,0,0,0.7)", borderColor: colors.brand.primary }}
              p={3}
            >
              <Icon as={FaArrowRight} boxSize={4} color={colors.text.primary} />
            </Button>
          </MotionBox>
        </HStack>

        <Box
          position="relative"
          w="full"
          h={{ base: "520px", md: "580px" }}
          perspective="2000px"
          overflow="visible"
          borderRadius={{ base: borderRadius.xl, md: borderRadius["2xl"] }}
          border="1px solid rgba(255,255,255,0.03)"
          bg={`linear-gradient(150deg, rgba(3, 4, 8, 0.98), rgba(5, 6, 12, 0.95))`}
          boxShadow="0 50px 100px rgba(0,0,0,0.6)"
          _before={{
            content: '""',
            position: "absolute",
            inset: 0,
            borderRadius: "inherit",
            background:
              "radial-gradient(circle at 50% 0%, rgba(47,116,255,0.08) 0%, transparent 50%)",
            pointerEvents: "none",
          }}
        >
          {/* Grid pattern inside slider */}
          <Box
            position="absolute"
            inset={0}
            borderRadius="inherit"
            backgroundImage="radial-gradient(circle at 1px 1px, rgba(255,255,255,0.015) 1px, transparent 0)"
            backgroundSize="40px 40px"
            opacity={0.8}
            pointerEvents="none"
          />

          <Flex
            justify="center"
            align="center"
            w="full"
            h="full"
            position="relative"
            overflow="visible"
            zIndex={1}
          >
            {FEATURE_SLIDES.map((slide, slideIdx) => {
              const offset = (slideIdx - index + FEATURE_SLIDES.length) % FEATURE_SLIDES.length;
              const SlideIcon = slideIcons[slide.id] || FaRocket;
              const animateProps = motionEnabled
                ? featureTransforms(offset)
                : {
                    x: "0%",
                    scale: 1,
                    rotateY: 0,
                    opacity: offset === 0 ? 1 : 0,
                    filter: "blur(0px)",
                    zIndex: offset === 0 ? 3 : 1,
                  };

              return (
                <MotionBox
                  key={slide.id}
                  position="absolute"
                  top="50%"
                  left="50%"
                  style={{ translateX: "-50%", translateY: "-50%" }}
                  w={{ base: "88%", md: "75%", lg: "65%" }}
                  maxW="720px"
                  minH={{ base: "420px", md: "500px" }}
                  borderRadius="2xl"
                  overflow="hidden"
                  boxShadow={
                    offset === 0
                      ? `0 35px 80px rgba(10,14,25,0.85), 0 0 60px ${colors.brand.primary}30`
                      : "0 20px 40px rgba(5,7,13,0.65)"
                  }
                  bg="rgba(8,10,18,0.95)"
                  animate={animateProps}
                  transition={motionEnabled ? SLIDE_TRANSITION : { duration: 0 }}
                  backgroundImage={`${slide.gradient}, radial-gradient(circle at top, rgba(255,255,255,0.06), transparent 55%)`}
                  backgroundSize="cover"
                  backgroundPosition="center"
                  role="group"
                  _before={
                    offset === 0
                      ? {
                          content: '""',
                          position: "absolute",
                          inset: 0,
                          borderRadius: "inherit",
                          padding: "2px",
                          background: `linear-gradient(135deg, ${colors.brand.primary} 0%, ${colors.brand.secondary} 50%, ${colors.brand.tertiary} 100%)`,
                          WebkitMask:
                            "linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)",
                          WebkitMaskComposite: "xor",
                          maskComposite: "exclude",
                          pointerEvents: "none",
                          animation: motionEnabled ? "rotate-gradient 8s linear infinite" : "none",
                        }
                      : {
                          content: '""',
                          position: "absolute",
                          inset: 0,
                          borderRadius: "inherit",
                          padding: "1px",
                          background: "rgba(255,255,255,0.05)",
                          WebkitMask:
                            "linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)",
                          WebkitMaskComposite: "xor",
                          maskComposite: "exclude",
                          pointerEvents: "none",
                        }
                  }
                >
                  {/* Inner backdrop */}
                  <Box
                    position="absolute"
                    inset={0}
                    bg="rgba(5,6,12,0.8)"
                    backdropFilter="blur(20px)"
                  />

                  <Stack
                    spacing={4}
                    position="relative"
                    h="full"
                    justify="space-between"
                    p={{ base: 6, md: 8, lg: 10 }}
                  >
                    <Stack spacing={4}>
                      {/* Badge with icon */}
                      <HStack spacing={3}>
                        <Box
                          p={2}
                          borderRadius={borderRadius.md}
                          bg={`${colors.brand.primary}15`}
                          border={`1px solid ${colors.brand.primary}30`}
                          animation={
                            offset === 0 && motionEnabled
                              ? `${float} 3s ease-in-out infinite`
                              : "none"
                          }
                        >
                          <Icon as={SlideIcon} boxSize={4} color={colors.brand.primary} />
                        </Box>
                        <Badge
                          bg="rgba(255,255,255,0.06)"
                          color={colors.text.primary}
                          borderRadius={borderRadius.full}
                          px={4}
                          py={2}
                          fontSize="10px"
                          fontWeight={600}
                          textTransform="uppercase"
                          letterSpacing="0.12em"
                          border="1px solid rgba(255,255,255,0.12)"
                        >
                          {slide.badge}
                        </Badge>
                      </HStack>

                      <Subtitle
                        variant="medium"
                        fontSize={{ base: "18px", md: "24px" }}
                        lineHeight="1.3"
                        fontWeight={600}
                        pt={2}
                      >
                        {offset === 0 ? <GradientText>{slide.title}</GradientText> : slide.title}
                      </Subtitle>

                      <Body
                        variant="small"
                        color={colors.text.tertiary}
                        fontSize={{ base: "13px", md: "15px" }}
                        lineHeight="1.7"
                        maxW="540px"
                      >
                        {slide.description}
                      </Body>
                    </Stack>

                    {offset === 0 && (
                      <HStack spacing={3} pt={4}>
                        <MotionBox
                          whileHover={motionEnabled ? { scale: 1.05, y: -2 } : undefined}
                          whileTap={motionEnabled ? { scale: 0.95 } : undefined}
                        >
                          <PrimaryButton
                            size="sm"
                            fontSize="12px"
                            px={6}
                            boxShadow={`0 4px 15px ${colors.brand.primary}40`}
                          >
                            Подробнее →
                          </PrimaryButton>
                        </MotionBox>
                        <MotionBox
                          whileHover={motionEnabled ? { scale: 1.05 } : undefined}
                          whileTap={motionEnabled ? { scale: 0.95 } : undefined}
                        >
                          <Button
                            variant="ghost"
                            size="sm"
                            fontSize="12px"
                            color={colors.text.secondary}
                            _hover={{
                              bg: "rgba(255,255,255,0.05)",
                              color: colors.text.primary,
                            }}
                          >
                            Документация
                          </Button>
                        </MotionBox>
                      </HStack>
                    )}
                  </Stack>

                  {/* Slide number indicator */}
                  <Box
                    position="absolute"
                    bottom={4}
                    right={4}
                    px={3}
                    py={1}
                    borderRadius={borderRadius.md}
                    bg="rgba(0,0,0,0.3)"
                    backdropFilter="blur(10px)"
                    border="1px solid rgba(255,255,255,0.05)"
                  >
                    <Body variant="small" fontSize="11px" color={colors.text.tertiary}>
                      {slideIdx + 1} / {FEATURE_SLIDES.length}
                    </Body>
                  </Box>
                </MotionBox>
              );
            })}
          </Flex>
        </Box>

        {/* Enhanced Indicator Dots */}
        <HStack justify="center" gap={3} mt={{ base: 8, md: 10 }}>
          {indicators}
        </HStack>

        {/* Progress bar */}
        <Box
          position="relative"
          w="200px"
          h="2px"
          bg="rgba(255,255,255,0.1)"
          borderRadius="full"
          mx="auto"
          mt={4}
          overflow="hidden"
        >
          <MotionBox
            position="absolute"
            top={0}
            left={0}
            h="full"
            w="100%"
            bg={`linear-gradient(90deg, ${colors.brand.primary}, ${colors.brand.secondary})`}
            borderRadius="full"
            animate={{ scaleX: (index + 1) / FEATURE_SLIDES.length }}
            style={{ transformOrigin: "left", willChange: "transform" }}
            transition={{ duration: 0.5 }}
          />
        </Box>
      </Box>
    </Stack>
  );
}
