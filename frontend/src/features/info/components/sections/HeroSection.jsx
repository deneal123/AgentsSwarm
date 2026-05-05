import React from "react";
import { Box, HStack, Icon, VStack } from "@chakra-ui/react";
import { keyframes } from "@emotion/react";
import { FaUsers, FaGraduationCap, FaCode, FaRocket } from "react-icons/fa";
import { Body, Title } from "@ui/atoms/Typography";
import { colors, spacing, borderRadius } from "@theme/tokens";
import { MotionBox, MotionVStack } from "@ui/motionPrimitives";
import { GradientText } from "@ui/atoms/AnimatedText";
import Section from "@ui/atoms/Section";
import TiltCard from "@ui/atoms/TiltCard";
import FloatingOrbs from "@ui/atoms/FloatingOrbs";
import ParticlesBackground from "@ui/atoms/ParticlesBackground";

const pulse = keyframes`
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.05); }
`;

const float = keyframes`
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
`;

const shimmer = keyframes`
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
`;

const glow = keyframes`
  0%, 100% { box-shadow: 0 0 30px rgba(47, 116, 255, 0.3); }
  50% { box-shadow: 0 0 60px rgba(47, 116, 255, 0.5); }
`;

function StatCard({ icon, value, label, color, delay = 0 }) {
  return (
    <MotionBox
      initial={{ opacity: 0, y: 20, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.5, delay }}
    >
      <Box
        p={4}
        borderRadius={borderRadius.xl}
        bg="rgba(255,255,255,0.03)"
        border="1px solid"
        borderColor="whiteAlpha.100"
        position="relative"
        overflow="hidden"
        transition="all 0.3s ease"
        _hover={{
          bg: "rgba(255,255,255,0.06)",
          borderColor: `${color}40`,
          transform: "translateY(-3px)",
        }}
        css={{
          animation: `${float} 4s ease-in-out infinite`,
          animationDelay: `${delay * 0.5}s`,
        }}
      >
        {/* Glow */}
        <Box
          position="absolute"
          top="-50%"
          left="-50%"
          width="200%"
          height="200%"
          background={`radial-gradient(circle, ${color}15 0%, transparent 70%)`}
          opacity={0.5}
          pointerEvents="none"
        />

        <VStack spacing={2} align="center" position="relative" zIndex={1}>
          <Box
            p={2}
            borderRadius={borderRadius.lg}
            bg={`${color}20`}
            css={{
              animation: `${pulse} 3s ease-in-out infinite`,
              animationDelay: `${delay * 0.3}s`,
            }}
          >
            <Icon as={icon} boxSize={5} color={color} />
          </Box>
          <Box fontSize="2xl" fontWeight={700} color={colors.text.primary}>
            {value}
          </Box>
          <Box
            fontSize="xs"
            color={colors.text.tertiary}
            textTransform="uppercase"
            letterSpacing="wider"
          >
            {label}
          </Box>
        </VStack>
      </Box>
    </MotionBox>
  );
}

function HeroSection({ description }) {
  const stats = [
    { icon: FaUsers, value: "4", label: "Участника", color: colors.brand.primary },
    {
      icon: FaGraduationCap,
      value: "НИУ ВШЭ",
      label: "Университет",
      color: colors.brand.secondary,
    },
    { icon: FaCode, value: "ML", label: "Направление", color: "#38A169" },
    { icon: FaRocket, value: "2025", label: "Год", color: "#D69E2E" },
  ];

  return (
    <Section center pt={{ base: 10, md: 18 }} pb={{ base: 16, md: 20 }}>
      <TiltCard
        tiltMaxAngleX={2}
        tiltMaxAngleY={3}
        glareEnable={true}
        glareMaxOpacity={0.1}
        scale={1.01}
      >
        <Box
          position="relative"
          overflow="hidden"
          borderRadius={borderRadius["2xl"]}
          p={{ base: spacing[6], md: spacing[10] }}
          bg="linear-gradient(135deg, rgba(47, 116, 255, 0.08) 0%, rgba(139, 92, 246, 0.05) 50%, rgba(29, 209, 161, 0.08) 100%)"
          border="1px solid"
          borderColor="whiteAlpha.100"
          css={{
            animation: `${glow} 4s ease-in-out infinite`,
          }}
        >
          {/* Background effects */}
          <FloatingOrbs count={5} />
          <ParticlesBackground particleCount={40} />

          {/* Gradient mesh */}
          <Box
            position="absolute"
            top={0}
            left={0}
            right={0}
            bottom={0}
            opacity={0.4}
            background="radial-gradient(ellipse at 20% 80%, rgba(47, 116, 255, 0.15) 0%, transparent 50%), radial-gradient(ellipse at 80% 20%, rgba(29, 209, 161, 0.15) 0%, transparent 50%)"
            pointerEvents="none"
          />

          <MotionVStack
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            spacing={spacing["2xl"]}
            align="center"
            textAlign="center"
            position="relative"
            zIndex={1}
          >
            <MotionBox
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.3, duration: 0.5 }}
            >
              <Box
                px={4}
                py={2}
                borderRadius={borderRadius.full}
                bg="linear-gradient(135deg, rgba(47, 116, 255, 0.2), rgba(139, 92, 246, 0.2))"
                border="1px solid"
                borderColor={`${colors.brand.primary}40`}
                css={{
                  animation: `${pulse} 2s ease-in-out infinite`,
                }}
              >
                <HStack spacing={2}>
                  <Icon as={FaUsers} boxSize={4} color={colors.brand.primary} />
                  <Box
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
                    О нашей команде
                  </Box>
                </HStack>
              </Box>
            </MotionBox>

            <MotionBox
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.6 }}
            >
              <Title
                variant="large"
                fontSize={{ base: "36px", md: "48px", lg: "56px" }}
                lineHeight="1.2"
                maxW={{ base: "full", md: "900px" }}
                paddingTop={2}
                px={{ base: 4, md: 0 }}
              >
                Мы студенты
                <br />
                <GradientText
                  gradient={`linear-gradient(135deg, ${colors.brand.primary}, ${colors.brand.secondary}, ${colors.brand.tertiary})`}
                >
                  НИУ ВШЭ
                </GradientText>
              </Title>
            </MotionBox>

            <MotionBox
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.6 }}
            >
              <Body
                variant="large"
                fontSize={{ base: "16px", md: "18px" }}
                color={colors.text.secondary}
                maxW="800px"
                lineHeight="1.8"
              >
                {description}
              </Body>
            </MotionBox>

            {/* Stats Grid */}
            <MotionBox
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6, duration: 0.6 }}
              w="full"
              maxW="700px"
            >
              <HStack spacing={4} justify="center" flexWrap="wrap" pt={4}>
                {stats.map((stat, index) => (
                  <StatCard key={stat.label} {...stat} delay={0.7 + index * 0.1} />
                ))}
              </HStack>
            </MotionBox>
          </MotionVStack>
        </Box>
      </TiltCard>
    </Section>
  );
}

export default HeroSection;
