import React from "react";
import PropTypes from "prop-types";
import { Badge, Box, Container, HStack, Text, VStack, Wrap, WrapItem } from "@chakra-ui/react";
import { NavLink } from "react-router-dom";
import { MotionBox, MotionVStack } from "@shared/ui/lib/motionPrimitives";
import { Title, Body, Footnote } from "@shared/ui/atoms";
import { PrimaryButton } from "@shared/ui/atoms";
import { SecondaryButton } from "@shared/ui/atoms";
import { GradientText, ParticlesBackground, FloatingOrbs, TiltCard } from "@shared/ui/atoms";
import Logo from "@shared/ui/assets/common/Logo";
import HeroBackground from "@features/home/components/HeroBackground";
import SearchInterface from "@features/home/components/SearchInterface";
import { colors, borderRadius } from "@theme/tokens";
import { HERO_COPY, HERO_TECH_STACK } from "@/constants";

const HERO_VARIANTS = {
  assistant: {
    headlineTop: "Спросите AI",
    headlineHighlight: "о здоровье и питании",
    description: "Получите персональные рекомендации по питанию, планам тренировок и здоровому образу жизни",
    showSearch: true,
    showPlatformMeta: false,
    minH: "100vh",
  },
  platform: {
    headlineTop: "Обработка данных",
    headlineHighlight: HERO_COPY.titleHighlight,
    description: HERO_COPY.descriptionPrimary,
    showSearch: false,
    showPlatformMeta: true,
    minH: "auto",
  },
};

function HeroSectionCanonical({ variant, isAuthenticated }) {
  const cfg = HERO_VARIANTS[variant] || HERO_VARIANTS.assistant;

  return (
    <Box position="relative" w="100%" minH={cfg.minH} display="flex" alignItems="center" justifyContent="center" overflow="hidden">
      {variant === "assistant" ? <HeroBackground /> : null}
      <Container maxW="7xl" position="relative" zIndex={1} py={{ base: 12, md: 16 }}>
        <TiltCard w="full" borderRadius={{ base: borderRadius.xl, md: borderRadius["2xl"] }}>
          <Box position="relative" p={{ base: 6, md: 10 }} overflow="hidden">
            {variant === "platform" ? (
              <>
                <FloatingOrbs count={2} />
                <ParticlesBackground particleCount={20} connectionDistance={100} speed={0.3} opacity={0.8} />
              </>
            ) : null}
            <MotionVStack spacing={8} align="center" textAlign="center" initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}>
              {cfg.showPlatformMeta ? (
                <HStack spacing={3}>
                  <Logo boxSize={8} priority />
                  <VStack spacing={0} align="start">
                    <Footnote color={colors.text.secondary}>{HERO_COPY.brandFootnote}</Footnote>
                    <Box h="2px" w="40px" bg={`linear-gradient(90deg, ${colors.brand.primary}, transparent)`} />
                  </VStack>
                </HStack>
              ) : null}

              {cfg.showPlatformMeta ? (
                <Wrap justify="center" spacing={2}>
                  {HERO_TECH_STACK.map((tech) => (
                    <WrapItem key={tech}>
                      <Badge px={3} py={1.5} borderRadius={borderRadius.lg} bg="rgba(255,255,255,0.06)" color={colors.text.secondary}>
                        {tech}
                      </Badge>
                    </WrapItem>
                  ))}
                </Wrap>
              ) : null}

              <VStack spacing={4}>
                <Title variant="large" fontSize={{ base: "3xl", md: "5xl", lg: "6xl" }} lineHeight="1.1">
                  <Text as="span" display="block">{cfg.headlineTop}</Text>
                  <GradientText as="span" display="block" gradient={`linear-gradient(135deg, ${colors.brand.primary}, ${colors.brand.secondary}, ${colors.brand.tertiary})`}>
                    {cfg.headlineHighlight}
                  </GradientText>
                </Title>
                <Body maxW="640px" color={colors.text.secondary} fontSize={{ base: "md", md: "lg" }}>
                  {cfg.description}
                </Body>
              </VStack>

              {cfg.showSearch ? (
                <MotionBox w="full" maxW="600px" initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}>
                  <SearchInterface />
                </MotionBox>
              ) : (
                <HStack spacing={4} flexWrap="wrap" justify="center">
                  <PrimaryButton as={NavLink} to={isAuthenticated ? HERO_COPY.authenticatedPrimaryCta.to : HERO_COPY.guestPrimaryCta.to} size="lg">
                    {isAuthenticated ? HERO_COPY.authenticatedPrimaryCta.label : HERO_COPY.guestPrimaryCta.label}
                  </PrimaryButton>
                  <SecondaryButton as={NavLink} to={isAuthenticated ? HERO_COPY.authenticatedSecondaryCta.to : HERO_COPY.guestSecondaryCta.to} size="lg">
                    {isAuthenticated ? HERO_COPY.authenticatedSecondaryCta.label : HERO_COPY.guestSecondaryCta.label}
                  </SecondaryButton>
                </HStack>
              )}
            </MotionVStack>
          </Box>
        </TiltCard>
      </Container>
    </Box>
  );
}

HeroSectionCanonical.propTypes = {
  variant: PropTypes.oneOf(["assistant", "platform"]),
  isAuthenticated: PropTypes.bool,
};

HeroSectionCanonical.defaultProps = {
  variant: "assistant",
  isAuthenticated: false,
};

export default HeroSectionCanonical;
