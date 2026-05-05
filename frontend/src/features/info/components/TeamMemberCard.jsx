import React from "react";
import { Avatar, Badge, Box, HStack, Icon, VStack, Tooltip, useToast } from "@chakra-ui/react";
import { keyframes } from "@emotion/react";
import { FiGithub, FiLinkedin, FiMail, FiMapPin, FiClipboard } from "react-icons/fi";
import { Body, Footnote, Title } from "@ui/atoms/Typography";
import { borderRadius, colors, spacing } from "@theme/tokens";
import { MotionBox } from "@ui/motionPrimitives";
import TiltCard from "@ui/atoms/TiltCard";

const pulse = keyframes`
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
`;

const float = keyframes`
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-5px); }
`;

function SocialIcon({ icon, href, label, ...motionProps }) {
  if (!href) return null;

  return (
    <MotionBox
      as="a"
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={label}
      title={label}
      whileHover={{ scale: 1.2, rotate: 5 }}
      whileTap={{ scale: 0.95 }}
      _focusVisible={{ boxShadow: `0 0 0 4px ${colors.brand.primary}33`, outline: "none" }}
      {...motionProps}
    >
      <Box
        p={2}
        borderRadius={borderRadius.lg}
        bg="rgba(255,255,255,0.05)"
        border="1px solid"
        borderColor="whiteAlpha.100"
        transition="all 0.2s ease"
        _hover={{
          bg: `${colors.brand.primary}20`,
          borderColor: `${colors.brand.primary}50`,
        }}
      >
        <Icon
          as={icon}
          boxSize={4}
          color={colors.text.secondary}
          _groupHover={{ color: colors.brand.primary }}
          transition="color 0.2s"
        />
      </Box>
    </MotionBox>
  );
}

function TeamMemberCard({ member, index }) {
  const toast = useToast();

  return (
    <MotionBox
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6, delay: index * 0.15 }}
      h="full"
    >
      <TiltCard
        tiltMaxAngleX={8}
        tiltMaxAngleY={8}
        glareEnable={true}
        glareMaxOpacity={0.15}
        scale={1.02}
      >
        <Box
          bg="linear-gradient(135deg, rgba(47, 116, 255, 0.05) 0%, rgba(139, 92, 246, 0.03) 100%)"
          border="1px solid"
          borderColor="whiteAlpha.100"
          borderRadius={borderRadius["2xl"]}
          p={{ base: spacing.lg, md: spacing["2xl"] }}
          position="relative"
          overflow="hidden"
          h="auto"
          minH={{ base: "auto", md: "420px" }}
          backdropFilter="blur(20px)"
          transition="all 0.3s ease"
          _hover={{
            borderColor: `${colors.brand.primary}50`,
            boxShadow: `0 0 40px ${colors.brand.primary}25, 0 0 80px ${colors.brand.secondary}15`,
          }}
          css={{
            animation: `${float} 6s ease-in-out infinite`,
            animationDelay: `${index * 0.5}s`,
          }}
        >
          {/* Top gradient line */}
          <Box
            position="absolute"
            top="0"
            left="0"
            right="0"
            h="3px"
            bg={`linear-gradient(90deg, ${colors.brand.primary}, ${colors.brand.secondary}, ${colors.brand.tertiary})`}
            opacity={0.8}
          />

          {/* Background glow */}
          <Box
            position="absolute"
            top="-30%"
            left="-30%"
            width="160%"
            height="160%"
            background={`radial-gradient(circle at 30% 30%, ${colors.brand.primary}10 0%, transparent 50%)`}
            pointerEvents="none"
          />

          <VStack
            spacing={spacing.lg}
            align="center"
            w="full"
            px={{ base: 2, md: 4 }}
            mt={4}
            h="full"
            justify="space-between"
            position="relative"
            zIndex={1}
          >
            <VStack spacing={spacing.lg} align="center">
              {/* Avatar */}
              <MotionBox whileHover={{ scale: 1.1 }} transition={{ duration: 0.3 }}>
                <Box
                  p={1}
                  borderRadius="full"
                  bg={`linear-gradient(135deg, ${colors.brand.primary}, ${colors.brand.secondary})`}
                  css={{
                    animation: `${pulse} 3s ease-in-out infinite`,
                  }}
                >
                  <Avatar
                    name={member.name}
                    boxSize={{ base: "70px", md: "96px" }}
                    bg={colors.blur.medium}
                    color={colors.text.primary}
                    border="3px solid"
                    borderColor={colors.background.darkPrimary}
                  />
                </Box>
              </MotionBox>

              {/* Name & Role */}
              <VStack spacing={spacing.sm} align="center">
                <Title variant="small" fontSize="20px" textAlign="center">
                  {member.name}
                </Title>
                <Badge
                  px={3}
                  py={1}
                  borderRadius={borderRadius.full}
                  bg={`${colors.brand.primary}15`}
                  color={colors.brand.primary}
                  fontSize="12px"
                  fontWeight={600}
                  border="1px solid"
                  borderColor={`${colors.brand.primary}30`}
                  textTransform="uppercase"
                  letterSpacing="wider"
                >
                  {member.role}
                </Badge>
              </VStack>

              {/* Description */}
              <Body
                variant="medium"
                color={colors.text.secondary}
                textAlign="center"
                fontSize={{ base: "13px", md: "14px" }}
                lineHeight="1.7"
                noOfLines={4}
              >
                {member.description}
              </Body>

              {/* Location */}
              {member.location && (
                <HStack
                  spacing={2}
                  color={colors.text.tertiary}
                  px={3}
                  py={1.5}
                  borderRadius={borderRadius.lg}
                  bg="rgba(255,255,255,0.03)"
                  border="1px solid"
                  borderColor="whiteAlpha.100"
                >
                  <Icon as={FiMapPin} boxSize={3.5} color={colors.brand.primary} />
                  <Footnote variant="small" fontSize="12px">
                    {member.location}
                  </Footnote>
                </HStack>
              )}

              {/* Work */}
              {member.work && (
                <Box
                  bg="rgba(255,255,255,0.03)"
                  px={4}
                  py={2}
                  borderRadius={borderRadius.lg}
                  border="1px solid"
                  borderColor="whiteAlpha.100"
                  w="full"
                >
                  <Footnote
                    variant="small"
                    color={colors.text.tertiary}
                    textAlign="center"
                    fontSize="12px"
                  >
                    {member.work}
                  </Footnote>
                </Box>
              )}
            </VStack>

            {/* Social Links */}
            {(member.github || member.linkedin || member.email) && (
              <HStack spacing={2} pt={2} flexWrap="wrap" justify="center">
                {member.github && (
                  <Tooltip label="GitHub" aria-label="GitHub tooltip">
                    <Box>
                      <SocialIcon icon={FiGithub} href={member.github} label="GitHub" />
                    </Box>
                  </Tooltip>
                )}

                {member.linkedin && (
                  <Tooltip label="LinkedIn" aria-label="LinkedIn tooltip">
                    <Box>
                      <SocialIcon
                        icon={FiLinkedin}
                        href={member.linkedin}
                        label="LinkedIn"
                        whileHover={{ rotate: -5 }}
                      />
                    </Box>
                  </Tooltip>
                )}

                {member.email && (
                  <>
                    <Tooltip label="Написать email" aria-label="Email tooltip">
                      <Box>
                        <SocialIcon icon={FiMail} href={`mailto:${member.email}`} label="Email" />
                      </Box>
                    </Tooltip>

                    <Tooltip label="Копировать email" aria-label="Copy email tooltip">
                      <MotionBox
                        as="button"
                        onClick={async () => {
                          try {
                            await navigator.clipboard.writeText(member.email);
                            toast({ title: "Email скопирован", status: "success", duration: 2000 });
                          } catch (err) {
                            toast({
                              title: "Не удалось скопировать",
                              status: "error",
                              duration: 2000,
                            });
                          }
                        }}
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.95 }}
                        aria-label="Copy email"
                        style={{ background: "transparent", border: "none", cursor: "pointer" }}
                        _focusVisible={{
                          boxShadow: `0 0 0 4px ${colors.brand.primary}33`,
                          outline: "none",
                        }}
                      >
                        <Box
                          p={2}
                          borderRadius={borderRadius.lg}
                          bg="rgba(255,255,255,0.05)"
                          border="1px solid"
                          borderColor="whiteAlpha.100"
                          transition="all 0.2s ease"
                          _hover={{
                            bg: `${colors.brand.primary}20`,
                            borderColor: `${colors.brand.primary}50`,
                          }}
                        >
                          <Icon as={FiClipboard} boxSize={4} color={colors.text.secondary} />
                        </Box>
                      </MotionBox>
                    </Tooltip>
                  </>
                )}
              </HStack>
            )}
          </VStack>
        </Box>
      </TiltCard>
    </MotionBox>
  );
}

export default TeamMemberCard;
