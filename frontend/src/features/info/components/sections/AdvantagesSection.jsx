import React from "react";
import { Box, SimpleGrid, Text, VStack, Icon, HStack } from "@chakra-ui/react";
import { keyframes } from "@emotion/react";
import { FaLightbulb } from "react-icons/fa";
import { Body, Footnote } from "@ui/atoms/Typography";
import { borderRadius, colors, spacing } from "@theme/tokens";
import { MotionBox, MotionVStack } from "@ui/motionPrimitives";
import { GradientText } from "@ui/atoms/AnimatedText";
import Section from "@ui/atoms/Section";
import TiltCard from "@ui/atoms/TiltCard";

const pulse = keyframes`
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.05); }
`;

const float = keyframes`
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-8px); }
`;

const shimmer = keyframes`
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
`;

function AdvantageCard({ feature, index }) {
  const emoji = feature.title.split(" ")[0];
  const title = feature.title.split(" ").slice(1).join(" ");

  // Different accent colors for variety
  const accentColors = [
    colors.brand.primary,
    colors.brand.secondary,
    colors.brand.tertiary,
    "#D69E2E",
    "#805AD5",
    "#00B5D8",
  ];
  const accentColor = accentColors[index % accentColors.length];

  return (
    <MotionBox
      initial={{ opacity: 0, y: 30, scale: 0.95 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
    >
      <TiltCard
        tiltMaxAngleX={6}
        tiltMaxAngleY={6}
        glareEnable={true}
        glareMaxOpacity={0.1}
        scale={1.02}
      >
        <Box
          bg="linear-gradient(135deg, rgba(47, 116, 255, 0.05) 0%, rgba(139, 92, 246, 0.03) 100%)"
          border="1px solid"
          borderColor="whiteAlpha.100"
          borderRadius={borderRadius.xl}
          p={{ base: spacing["2xl"], md: spacing["3xl"] }}
          h="full"
          minH={{ base: "220px", md: "260px" }}
          backdropFilter="blur(20px)"
          transition="all 0.3s ease"
          position="relative"
          overflow="hidden"
          _hover={{
            borderColor: `${accentColor}50`,
            boxShadow: `0 0 40px ${accentColor}20`,
          }}
          css={{
            animation: `${float} 5s ease-in-out infinite`,
            animationDelay: `${index * 0.3}s`,
          }}
        >
          {/* Top accent line */}
          <Box
            position="absolute"
            top={0}
            left={0}
            right={0}
            h="2px"
            bg={`linear-gradient(90deg, transparent, ${accentColor}, transparent)`}
            opacity={0.6}
          />

          {/* Background glow */}
          <Box
            position="absolute"
            top="-40%"
            right="-20%"
            width="80%"
            height="150%"
            background={`radial-gradient(circle, ${accentColor}08 0%, transparent 60%)`}
            pointerEvents="none"
          />

          <VStack spacing={spacing.lg} align="flex-start" h="full" position="relative" zIndex={1}>
            {/* Emoji & Title */}
            <HStack spacing={3} align="center">
              <Box
                p={3}
                borderRadius={borderRadius.xl}
                bg={`${accentColor}15`}
                border="1px solid"
                borderColor={`${accentColor}30`}
                css={{
                  animation: `${pulse} 3s ease-in-out infinite`,
                  animationDelay: `${index * 0.2}s`,
                }}
              >
                <Text fontSize="24px" lineHeight="1">
                  {emoji}
                </Text>
              </Box>
              <Footnote
                variant="large"
                color={colors.text.primary}
                fontWeight={600}
                fontSize="16px"
              >
                {title}
              </Footnote>
            </HStack>

            {/* Description */}
            <Body
              variant="small"
              color={colors.text.tertiary}
              fontSize={{ base: "13px", md: "14px" }}
              lineHeight="1.75"
            >
              {feature.description}
            </Body>
          </VStack>
        </Box>
      </TiltCard>
    </MotionBox>
  );
}

function AdvantagesSection({ advantages, title }) {
  return (
    <Section pt={{ base: 16, md: 20 }}>
      <MotionVStack
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8 }}
        spacing={{ base: spacing["6xl"], md: spacing["8xl"] }}
      >
        {/* Section Header */}
        <VStack spacing={4} align="center" textAlign="center">
          <MotionBox
            initial={{ scale: 0, opacity: 0 }}
            whileInView={{ scale: 1, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2, duration: 0.5 }}
          >
            <Box
              px={4}
              py={2}
              borderRadius={borderRadius.full}
              bg={`${colors.brand.primary}15`}
              border="1px solid"
              borderColor={`${colors.brand.primary}30`}
            >
              <HStack spacing={2}>
                <Icon as={FaLightbulb} boxSize={4} color={colors.brand.primary} />
                <Text
                  fontSize="sm"
                  fontWeight={600}
                  textTransform="uppercase"
                  letterSpacing="wider"
                  css={{
                    background: `linear-gradient(90deg, ${colors.brand.primary}, ${colors.brand.secondary}, ${colors.brand.primary})`,
                    backgroundSize: "200% auto",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    animation: `${shimmer} 3s linear infinite`,
                  }}
                >
                  Преимущества
                </Text>
              </HStack>
            </Box>
          </MotionBox>

          <Text
            fontSize={{ base: "28px", md: "36px" }}
            fontWeight={700}
            color={colors.text.primary}
          >
            <GradientText>{title || "Преимущества проекта"}</GradientText>
          </Text>
        </VStack>

        {/* Cards Grid */}
        <SimpleGrid
          columns={{ base: 1, md: 2, lg: 3 }}
          spacing={{ base: 6, md: 8 }}
          w="full"
          pt={{ base: 4, md: 6 }}
        >
          {advantages.map((feature, i) => (
            <AdvantageCard key={feature.title} feature={feature} index={i} />
          ))}
        </SimpleGrid>
      </MotionVStack>
    </Section>
  );
}

export default AdvantagesSection;
