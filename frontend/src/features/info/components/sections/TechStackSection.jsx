import React from "react";
import { Badge, Box, Flex, VStack, Text, HStack, Icon } from "@chakra-ui/react";
import { keyframes } from "@emotion/react";
import { FaCogs } from "react-icons/fa";
import { borderRadius, colors, spacing } from "@theme/tokens";
import { MotionBox } from "@ui/motionPrimitives";
import { GradientText } from "@ui/atoms/AnimatedText";
import Section from "@ui/atoms/Section";
import TiltCard from "@ui/atoms/TiltCard";

const pulse = keyframes`
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
`;

const float = keyframes`
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-3px) rotate(1deg); }
`;

const shimmer = keyframes`
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
`;

const glow = keyframes`
  0%, 100% { box-shadow: 0 0 20px rgba(47, 116, 255, 0.2); }
  50% { box-shadow: 0 0 40px rgba(47, 116, 255, 0.4); }
`;

// Tech categories with colors
const techCategories = {
  // Frontend
  React: { color: "#61DAFB", category: "frontend" },
  TypeScript: { color: "#3178C6", category: "frontend" },
  JavaScript: { color: "#F7DF1E", category: "frontend" },
  "Chakra UI": { color: "#319795", category: "frontend" },
  "Framer Motion": { color: "#FF0080", category: "frontend" },
  CSS: { color: "#1572B6", category: "frontend" },
  HTML: { color: "#E34F26", category: "frontend" },

  // Backend
  Python: { color: "#3776AB", category: "backend" },
  FastAPI: { color: "#009688", category: "backend" },
  Flask: { color: "#000000", category: "backend" },
  Django: { color: "#092E20", category: "backend" },
  PostgreSQL: { color: "#336791", category: "backend" },
  Redis: { color: "#DC382D", category: "backend" },
  Celery: { color: "#37814A", category: "backend" },

  // ML/AI
  "scikit-learn": { color: "#F7931E", category: "ml" },
  PyTorch: { color: "#EE4C2C", category: "ml" },
  TensorFlow: { color: "#FF6F00", category: "ml" },
  TPOT: { color: "#8B5CF6", category: "ml" },
  Pandas: { color: "#150458", category: "ml" },
  NumPy: { color: "#013243", category: "ml" },

  // DevOps
  Docker: { color: "#2496ED", category: "devops" },
  Kubernetes: { color: "#326CE5", category: "devops" },
  Nginx: { color: "#009639", category: "devops" },
  MinIO: { color: "#C72C48", category: "devops" },
  Prometheus: { color: "#E6522C", category: "devops" },
  Git: { color: "#F05032", category: "devops" },
};

function TechBadge({ tech, index }) {
  const techInfo = techCategories[tech] || { color: colors.brand.primary, category: "other" };

  return (
    <MotionBox
      initial={{ opacity: 0, scale: 0.8, y: 10 }}
      whileInView={{ opacity: 1, scale: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.03, duration: 0.4 }}
      whileHover={{ scale: 1.1, y: -3 }}
      whileTap={{ scale: 0.95 }}
    >
      <Badge
        px={{ base: 3, md: 4 }}
        py={{ base: 1.5, md: 2 }}
        borderRadius={borderRadius.xl}
        fontSize="13px"
        fontWeight={500}
        bg="rgba(255,255,255,0.03)"
        color={colors.text.primary}
        border="1px solid"
        borderColor={`${techInfo.color}40`}
        cursor="default"
        transition="all 0.3s ease"
        position="relative"
        overflow="hidden"
        _hover={{
          borderColor: techInfo.color,
          boxShadow: `0 0 25px ${techInfo.color}40`,
          bg: `${techInfo.color}15`,
        }}
        css={{
          animation: `${float} 4s ease-in-out infinite`,
          animationDelay: `${index * 0.1}s`,
        }}
      >
        {/* Color indicator dot */}
        <Box
          position="absolute"
          left={2}
          top="50%"
          transform="translateY(-50%)"
          w={1.5}
          h={1.5}
          borderRadius="full"
          bg={techInfo.color}
          css={{
            animation: `${pulse} 2s ease-in-out infinite`,
            animationDelay: `${index * 0.05}s`,
          }}
        />
        <Box pl={3}>{tech}</Box>
      </Badge>
    </MotionBox>
  );
}

function TechStackSection({ techStack }) {
  return (
    <Section pt={{ base: spacing["6xl"], md: spacing["8xl"] }}>
      <MotionBox
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8 }}
        w="full"
        mt={0}
        px={{ base: 0 }}
        py={{ base: 8, md: 12 }}
      >
        <TiltCard
          tiltMaxAngleX={2}
          tiltMaxAngleY={3}
          glareEnable={true}
          glareMaxOpacity={0.08}
          scale={1.01}
        >
          <Box
            bg="linear-gradient(135deg, rgba(47, 116, 255, 0.06) 0%, rgba(139, 92, 246, 0.04) 50%, rgba(29, 209, 161, 0.06) 100%)"
            border="1px solid"
            borderColor="whiteAlpha.100"
            borderRadius={borderRadius["2xl"]}
            p={{ base: spacing["2xl"], md: spacing["4xl"] }}
            backdropFilter="blur(20px)"
            position="relative"
            overflow="hidden"
            css={{
              animation: `${glow} 4s ease-in-out infinite`,
            }}
          >
            {/* Background decorations */}
            <Box
              position="absolute"
              top="-20%"
              left="-10%"
              width="50%"
              height="140%"
              background={`radial-gradient(circle, ${colors.brand.primary}08 0%, transparent 60%)`}
              pointerEvents="none"
            />
            <Box
              position="absolute"
              bottom="-20%"
              right="-10%"
              width="50%"
              height="140%"
              background={`radial-gradient(circle, ${colors.brand.secondary}08 0%, transparent 60%)`}
              pointerEvents="none"
            />

            <VStack spacing={spacing["2xl"]} position="relative" zIndex={1}>
              {/* Header */}
              <VStack spacing={3} align="center">
                <Box
                  px={4}
                  py={2}
                  borderRadius={borderRadius.full}
                  bg={`${colors.brand.primary}15`}
                  border="1px solid"
                  borderColor={`${colors.brand.primary}30`}
                >
                  <HStack spacing={2}>
                    <Icon as={FaCogs} boxSize={4} color={colors.brand.primary} />
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
                      Технологии
                    </Text>
                  </HStack>
                </Box>

                <Text
                  fontSize={{ base: "24px", md: "28px" }}
                  fontWeight={700}
                  color={colors.text.primary}
                  textAlign="center"
                >
                  <GradientText>Наш технологический стек</GradientText>
                </Text>
              </VStack>

              {/* Tech badges */}
              <Flex
                flexWrap="wrap"
                gap={3}
                justify="center"
                align="center"
                maxW="900px"
                py={6}
                margin="0 auto"
              >
                {techStack.map((tech, i) => (
                  <TechBadge key={tech} tech={tech} index={i} />
                ))}
              </Flex>
            </VStack>
          </Box>
        </TiltCard>
      </MotionBox>
    </Section>
  );
}

export default TechStackSection;
