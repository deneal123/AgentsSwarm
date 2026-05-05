import React from "react";
import { Box, HStack, Icon, Tooltip, Text } from "@chakra-ui/react";
import { keyframes } from "@emotion/react";
import { FiGithub, FiMail, FiMessageCircle, FiSend } from "react-icons/fi";
import { FaEnvelope } from "react-icons/fa";
import { Body, Title } from "@ui/atoms/Typography";
import { borderRadius, colors, spacing } from "@theme/tokens";
import { ORG_GITHUB_URL, ORG_VK_URL } from "@constants";
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
  50% { transform: translateY(-5px); }
`;

const shimmer = keyframes`
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
`;

const glow = keyframes`
  0%, 100% { box-shadow: 0 0 30px rgba(47, 116, 255, 0.3); }
  50% { box-shadow: 0 0 50px rgba(47, 116, 255, 0.5); }
`;

function ContactButton({ href, icon, label, isPrimary = false, delay = 0 }) {
  return (
    <MotionBox
      whileHover={{ scale: 1.05, y: -3 }}
      whileTap={{ scale: 0.95 }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
    >
      <Tooltip label={label} aria-label={`${label} tooltip`}>
        <Box
          as="a"
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={label}
          px={{ base: 5, md: 8 }}
          py={{ base: 3, md: 4 }}
          minW={{ base: "140px", md: "auto" }}
          borderRadius={borderRadius.xl}
          fontSize={{ base: "14px", md: "16px" }}
          fontWeight={600}
          display="flex"
          alignItems="center"
          justifyContent="center"
          gap={3}
          transition="all 0.3s ease"
          position="relative"
          overflow="hidden"
          bg={
            isPrimary
              ? `linear-gradient(135deg, ${colors.brand.primary}, ${colors.brand.secondary})`
              : "rgba(255,255,255,0.03)"
          }
          color={colors.text.primary}
          border="1px solid"
          borderColor={isPrimary ? "transparent" : "whiteAlpha.200"}
          _hover={{
            boxShadow: isPrimary
              ? `0 0 40px ${colors.brand.primary}50`
              : `0 0 30px ${colors.brand.primary}30`,
            borderColor: isPrimary ? "transparent" : `${colors.brand.primary}50`,
          }}
          _focusVisible={{
            boxShadow: `0 0 0 4px ${colors.brand.primary}33`,
            outline: "none",
          }}
          css={
            isPrimary
              ? {
                  "&::before": {
                    content: '""',
                    position: "absolute",
                    top: 0,
                    left: "-100%",
                    width: "100%",
                    height: "100%",
                    background:
                      "linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)",
                    animation: `${shimmer} 2s linear infinite`,
                  },
                }
              : undefined
          }
        >
          <Icon as={icon} boxSize={5} />
          {label}
        </Box>
      </Tooltip>
    </MotionBox>
  );
}

function ContactSection() {
  return (
    <Section
      center
      pt={{ base: spacing["8xl"], md: spacing["10xl"], lg: spacing["10xl"] }}
      pb={{ base: spacing["6xl"], md: spacing["8xl"] }}
    >
      <TiltCard
        tiltMaxAngleX={3}
        tiltMaxAngleY={4}
        glareEnable={true}
        glareMaxOpacity={0.1}
        scale={1.01}
      >
        <Box
          position="relative"
          overflow="hidden"
          borderRadius={borderRadius["2xl"]}
          p={{ base: spacing["3xl"], md: spacing["5xl"] }}
          bg="linear-gradient(135deg, rgba(47, 116, 255, 0.08) 0%, rgba(139, 92, 246, 0.05) 50%, rgba(29, 209, 161, 0.08) 100%)"
          border="1px solid"
          borderColor="whiteAlpha.100"
          css={{
            animation: `${glow} 4s ease-in-out infinite`,
          }}
        >
          {/* Background decorations */}
          <Box
            position="absolute"
            top="-30%"
            left="-20%"
            width="60%"
            height="160%"
            background={`radial-gradient(circle, ${colors.brand.primary}10 0%, transparent 60%)`}
            pointerEvents="none"
          />
          <Box
            position="absolute"
            bottom="-30%"
            right="-20%"
            width="60%"
            height="160%"
            background={`radial-gradient(circle, ${colors.brand.secondary}10 0%, transparent 60%)`}
            pointerEvents="none"
          />

          <MotionVStack
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.2 }}
            spacing={spacing.xl}
            textAlign="center"
            position="relative"
            zIndex={1}
          >
            {/* Badge */}
            <MotionBox
              initial={{ scale: 0, opacity: 0 }}
              whileInView={{ scale: 1, opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.3, duration: 0.5 }}
            >
              <Box
                px={4}
                py={2}
                borderRadius={borderRadius.full}
                bg={`${colors.brand.primary}15`}
                border="1px solid"
                borderColor={`${colors.brand.primary}30`}
                css={{
                  animation: `${pulse} 2s ease-in-out infinite`,
                }}
              >
                <HStack spacing={2}>
                  <Icon as={FaEnvelope} boxSize={4} color={colors.brand.primary} />
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
                    Контакты
                  </Text>
                </HStack>
              </Box>
            </MotionBox>

            {/* Title */}
            <Title variant="small" fontSize={{ base: "28px", md: "36px" }}>
              <GradientText>Появились вопросы?</GradientText>
            </Title>

            {/* Description */}
            <Body
              variant="medium"
              color={colors.text.secondary}
              maxW="600px"
              fontSize={{ base: "14px", md: "16px" }}
              mx="auto"
              lineHeight="1.8"
            >
              Пишите в контакты организации GitHub или напрямую разработчикам. Мы всегда рады
              обратной связи и новым идеям!
            </Body>

            {/* Buttons */}
            <HStack spacing={4} pt={4} justify="center" flexWrap="wrap">
              {ORG_GITHUB_URL && (
                <ContactButton
                  href={ORG_GITHUB_URL}
                  icon={FiGithub}
                  label="GitHub"
                  isPrimary={true}
                  delay={0.4}
                />
              )}

              {ORG_VK_URL && (
                <ContactButton
                  href={ORG_VK_URL}
                  icon={FiMessageCircle}
                  label="Связаться"
                  delay={0.5}
                />
              )}
            </HStack>

            {/* Decorative floating icons */}
            <Box position="relative" w="full" h="40px" mt={4}>
              {[FiSend, FiMail, FiGithub].map((IconComp, i) => (
                <MotionBox
                  key={i}
                  position="absolute"
                  left={`${25 + i * 25}%`}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 0.3, y: 0 }}
                  transition={{ delay: 0.6 + i * 0.1, duration: 0.5 }}
                  css={{
                    animation: `${float} ${3 + i * 0.5}s ease-in-out infinite`,
                    animationDelay: `${i * 0.3}s`,
                  }}
                >
                  <Icon as={IconComp} boxSize={5} color={colors.text.muted} />
                </MotionBox>
              ))}
            </Box>
          </MotionVStack>
        </Box>
      </TiltCard>
    </Section>
  );
}

export default ContactSection;
