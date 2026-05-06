import React, { useRef } from "react";
import { Box, SimpleGrid, Stack, Icon, usePrefersReducedMotion } from "@chakra-ui/react";
import { MotionBox, motionKeyframes, motionVariants } from "@shared/ui/lib/motionPrimitives";
import { Subtitle, Body, Footnote } from "@shared/ui/atoms";
import { GradientText } from "@shared/ui/atoms";
import { colors, borderRadius, spacing } from "@theme/tokens";
import { CheckCircleIcon, TimeIcon, LockIcon, RepeatIcon } from "@chakra-ui/icons";
import { BENEFITS_CONTENT } from "@constants";

const iconMap = {
  CheckCircleIcon,
  TimeIcon,
  RepeatIcon,
  LockIcon,
};

const resolveIcon = (iconKey) => iconMap[iconKey] || CheckCircleIcon;

const resolveColor = (colorKey) => {
  if (!colorKey) return colors.brand.primary;
  if (colorKey.startsWith("#")) return colorKey;
  const parts = colorKey.split(".");
  return parts.reduce((acc, part) => (acc ? acc[part] : undefined), colors) || colorKey;
};

/**
 * BenefitCard - Individual benefit card with 3D hover effects
 */
function BenefitCard({ benefit, index }) {
  const cardRef = useRef(null);
  const prefersReducedMotion = usePrefersReducedMotion();
  const IconComponent = resolveIcon(benefit.icon);
  const benefitColor = resolveColor(benefit.color);

  const [transform, setTransform] = React.useState("");
  const [glowOpacity, setGlowOpacity] = React.useState(0);

  const handleMouseMove = (e) => {
    if (prefersReducedMotion || !cardRef.current) return;

    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    const rotateX = ((y - centerY) / centerY) * -8;
    const rotateY = ((x - centerX) / centerX) * 8;

    setTransform(
      `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`,
    );
    setGlowOpacity(1);
  };

  const handleMouseLeave = () => {
    setTransform("");
    setGlowOpacity(0);
  };

  return (
    <MotionBox
      ref={cardRef}
      variants={motionVariants.riseInItem}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{ transform, transformStyle: "preserve-3d" }}
      transition={{ duration: 0.15, ease: "easeOut" }}
      willChange="transform"
    >
      <Box
        position="relative"
        bg="rgba(8,10,18,0.95)"
        borderRadius={borderRadius.xl}
        p={{ base: 6, md: 7 }}
        border="1px solid rgba(255,255,255,0.06)"
        h="full"
        overflow="hidden"
        backdropFilter="blur(24px)"
        _before={{
          content: '""',
          position: "absolute",
          inset: "-2px",
          borderRadius: "inherit",
          bg: `linear-gradient(135deg, ${benefitColor}30, transparent 50%, ${benefitColor}20)`,
          opacity: glowOpacity,
          transition: "opacity 0.3s ease",
          zIndex: -1,
        }}
      >
        {/* Animated background gradient */}
        <Box
          position="absolute"
          inset="-50%"
          bg={`radial-gradient(circle at 30% 30%, ${benefitColor}15, transparent 50%)`}
          opacity={0.6}
          pointerEvents="none"
        />

        {/* Shimmer effect on hover */}
        <Box
          position="absolute"
          top={0}
          left="-100%"
          w="50%"
          h="100%"
          bg="linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent)"
          transform="skewX(-20deg)"
          animation={glowOpacity ? `${motionKeyframes.shimmer} 1.5s ease-in-out` : "none"}
          pointerEvents="none"
        />

        {/* Top accent line */}
        <Box
          position="absolute"
          top={0}
          left="20%"
          right="20%"
          h="2px"
          bg={`linear-gradient(90deg, transparent, ${benefitColor}, transparent)`}
          opacity={0.6}
        />

        <Stack spacing={4} position="relative" style={{ transform: "translateZ(20px)" }}>
          {/* Icon with floating animation */}
          <Box position="relative" w="fit-content">
            <Box
              position="absolute"
              inset={-2}
              bg={`radial-gradient(circle, ${benefitColor}30 0%, transparent 70%)`}
              filter="blur(10px)"
              animation={prefersReducedMotion ? "none" : `${motionKeyframes.pulse} 3s ease-in-out infinite`}
              style={{ animationDelay: `${index * 0.5}s` }}
            />
            <Box
              bg={`linear-gradient(135deg, ${benefitColor}20, rgba(255,255,255,0.02))`}
              borderRadius={borderRadius.lg}
              p={4}
              position="relative"
              border={`1px solid ${benefitColor}30`}
              animation={prefersReducedMotion ? "none" : `${motionKeyframes.float} 4s ease-in-out infinite`}
              style={{ animationDelay: `${index * 0.3}s` }}
            >
              <Icon
                as={IconComponent}
                boxSize={7}
                color={benefitColor}
                filter={`drop-shadow(0 0 8px ${benefitColor}60)`}
              />
            </Box>
          </Box>

          {/* Title */}
          <Subtitle variant="small" fontSize={{ base: "17px", md: "19px" }} fontWeight={600}>
            {benefit.title}
          </Subtitle>

          {/* Description */}
          <Body
            variant="small"
            color={colors.text.tertiary}
            fontSize={{ base: "13px", md: "14px" }}
            lineHeight="1.7"
          >
            {benefit.description}
          </Body>

          {/* Decorative element */}
          <Box
            w="40px"
            h="3px"
            borderRadius="full"
            bg={`linear-gradient(90deg, ${benefitColor}, transparent)`}
            opacity={0.6}
          />
        </Stack>

        {/* Corner decoration */}
        <Box
          position="absolute"
          bottom={4}
          right={4}
          w="40px"
          h="40px"
          borderBottom="1px solid"
          borderRight="1px solid"
          borderColor={`${benefitColor}20`}
          borderBottomRightRadius={borderRadius.md}
          opacity={0.5}
        />
      </Box>
    </MotionBox>
  );
}

function BenefitsSection() {
  const prefersReducedMotion = usePrefersReducedMotion();

  return (
    <Box
      w="full"
      position="relative"
      borderRadius={{ base: borderRadius.lg, md: borderRadius["2xl"] }}
      overflow="hidden"
      px={{ base: spacing.md, md: spacing.xl }}
      py={{ base: spacing.xl, md: spacing["3xl"] }}
      bg={`linear-gradient(145deg, rgba(4,6,12,0.95), rgba(7,9,18,0.85))`}
      border="1px solid rgba(255,255,255,0.04)"
      boxShadow="0 40px 100px rgba(0,0,0,0.5)"
    >
      {/* Animated background orbs */}
      <Box
        position="absolute"
        top="-20%"
        left="-10%"
        w="400px"
        h="400px"
        borderRadius="full"
        bg={`radial-gradient(circle, ${colors.brand.primary}15 0%, transparent 70%)`}
        filter="blur(80px)"
        animation={prefersReducedMotion ? "none" : `${pulse} 8s ease-in-out infinite`}
        pointerEvents="none"
      />
      <Box
        position="absolute"
        bottom="-10%"
        right="-10%"
        w="350px"
        h="350px"
        borderRadius="full"
        bg={`radial-gradient(circle, ${colors.brand.secondary}15 0%, transparent 70%)`}
        filter="blur(80px)"
        animation={prefersReducedMotion ? "none" : `${pulse} 10s ease-in-out infinite`}
        style={{ animationDelay: "2s" }}
        pointerEvents="none"
      />

      {/* Grid pattern */}
      <Box
        position="absolute"
        inset={0}
        backgroundImage="radial-gradient(circle at 1px 1px, rgba(255,255,255,0.02) 1px, transparent 0)"
        backgroundSize="32px 32px"
        opacity={0.5}
        pointerEvents="none"
      />

      <Stack spacing={{ base: 10, md: 14 }} align="center" position="relative" zIndex={1}>
        {/* Section Header */}
        <MotionBox
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <Stack spacing={4} align="center" textAlign="center" maxW="800px">
            {/* Badge */}
            <Box
              px={4}
              py={2}
              borderRadius={borderRadius.full}
              bg="rgba(47, 116, 255, 0.1)"
              border="1px solid rgba(47, 116, 255, 0.2)"
            >
              <Footnote
                variant="medium"
                color={colors.brand.primary}
                textTransform="uppercase"
                letterSpacing="0.15em"
                fontWeight={600}
                fontSize="11px"
              >
                ✦ {BENEFITS_CONTENT.title}
              </Footnote>
            </Box>

            <Subtitle variant="large" fontSize={{ base: "28px", md: "36px" }} fontWeight={600}>
              <GradientText>{BENEFITS_CONTENT.subtitle}</GradientText>
            </Subtitle>

            <Body
              variant="medium"
              color={colors.text.tertiary}
              maxW="650px"
              fontSize={{ base: "14px", md: "16px" }}
              lineHeight="1.7"
            >
              {BENEFITS_CONTENT.description}
            </Body>
          </Stack>
        </MotionBox>

        {/* Benefits Grid */}
        <MotionBox
          w="full"
          variants={motionVariants.staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
        >
          <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={{ base: 5, md: 6 }} w="full">
            {BENEFITS_CONTENT.items.map((benefit, index) => (
              <BenefitCard key={index} benefit={benefit} index={index} />
            ))}
          </SimpleGrid>
        </MotionBox>
      </Stack>
    </Box>
  );
}

export default BenefitsSection;
