import React, { useState } from "react";
import { Container, Box, Heading, Text, HStack, SimpleGrid, useDisclosure } from "@chakra-ui/react";
import { motion, AnimatePresence } from "framer-motion";
import { css, keyframes } from "@emotion/react";
import { spacing, colors } from "@theme/tokens";
import { useLayoutControls } from "@context/LayoutContext";
import FloatingOrbs from "@ui/atoms/FloatingOrbs";
import ParticlesBackground from "@ui/atoms/ParticlesBackground";
import { GradientText } from "@ui/atoms/AnimatedText";
import DocumentCard from "./DocumentCard";
import DocumentModal from "./DocumentModal";
import { DOCUMENT_LIST } from "./legalContent";

const MotionBox = motion(Box);
const MotionHeading = motion(Heading);
const MotionText = motion(Text);

/* ───────── Keyframes ───────── */
const pulse = keyframes`
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
`;

const float = keyframes`
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
`;

/* ───────── Animation Variants ───────── */
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
      delayChildren: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.6,
      ease: [0.25, 0.46, 0.45, 0.94],
    },
  },
};

const heroVariants = {
  hidden: { opacity: 0, y: -20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.8,
      ease: "easeOut",
    },
  },
};

/* ───────── Hero Section ───────── */
function DocumentsHeroSection() {
  return (
    <Box
      position="relative"
      pt={{ base: 12, md: 16 }}
      pb={{ base: 8, md: 12 }}
      textAlign="center"
      overflow="hidden"
    >
      {/* Decorative background line */}
      <Box
        position="absolute"
        top="50%"
        left="50%"
        transform="translate(-50%, -50%)"
        w="80%"
        maxW="600px"
        h="1px"
        bg={`linear-gradient(90deg, transparent, ${colors.brand.primary}40, transparent)`}
        css={css`
          animation: ${pulse} 3s ease-in-out infinite;
        `}
      />

      <MotionBox variants={heroVariants} initial="hidden" animate="visible">
        {/* Icon */}
        <Box
          display="inline-flex"
          alignItems="center"
          justifyContent="center"
          w="80px"
          h="80px"
          mb={6}
          borderRadius="xl"
          bg={`linear-gradient(135deg, ${colors.brand.primary}20, ${colors.brand.secondary}20)`}
          border={`1px solid ${colors.brand.primary}30`}
          boxShadow={`0 0 40px ${colors.brand.primary}20`}
          css={css`
            animation: ${float} 4s ease-in-out infinite;
          `}
        >
          <Text fontSize="3xl">📜</Text>
        </Box>

        {/* Title */}
        <MotionHeading
          as="h1"
          fontSize={{ base: "2xl", md: "4xl", lg: "5xl" }}
          fontWeight="bold"
          mb={4}
          variants={itemVariants}
        >
          <GradientText>Документы и соглашения</GradientText>
        </MotionHeading>

        {/* Subtitle */}
        <MotionText
          fontSize={{ base: "md", md: "lg" }}
          color={colors.text.secondary}
          maxW="600px"
          mx="auto"
          lineHeight="1.7"
          variants={itemVariants}
        >
          Ознакомьтесь с условиями использования AI-агентов для здоровья и питания, политикой
          конфиденциальности медицинских данных и другими правовыми документами
        </MotionText>
      </MotionBox>

      {/* Decorative dots */}
      <HStack
        justify="center"
        spacing={2}
        mt={8}
        as={motion.div}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
      >
        {[0, 1, 2].map((i) => (
          <Box
            key={i}
            w="6px"
            h="6px"
            borderRadius="full"
            bg={colors.brand.primary}
            opacity={0.5 + i * 0.2}
          />
        ))}
      </HStack>
    </Box>
  );
}

/* ───────── Main Component ───────── */
export default function DocumentsPage() {
  const { setVariant, setFooterVisible } = useLayoutControls();
  const [selectedDocument, setSelectedDocument] = useState(null);
  const { isOpen, onOpen, onClose } = useDisclosure();

  React.useEffect(() => {
    setVariant("full");
    setFooterVisible(false);
    return () => {
      setVariant("container");
      setFooterVisible(true);
    };
  }, [setVariant, setFooterVisible]);

  const handleOpenDocument = (doc) => {
    setSelectedDocument(doc);
    onOpen();
  };

  const handleCloseDocument = () => {
    setSelectedDocument(null);
    onClose();
  };

  return (
    <Box as="main" bg={colors.background.darkPrimary} minH="calc(100vh - 80px)" position="relative">
      {/* Background Effects */}
      <FloatingOrbs count={3} />
      <ParticlesBackground particleCount={30} speed={0.3} />

      {/* Gradient overlay */}
      <Box
        position="absolute"
        top={0}
        left={0}
        right={0}
        h="50vh"
        bgGradient={`linear(to-b, ${colors.brand.primary}08, transparent)`}
        pointerEvents="none"
        zIndex={0}
      />

      {/* Content */}
      <Box position="relative" zIndex={1}>
        <Container maxW="6xl" px={{ base: spacing.md, md: spacing.lg }}>
          {/* Hero Section */}
          <DocumentsHeroSection />

          {/* Documents Grid */}
          <MotionBox
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            pb={{ base: 12, md: 16 }}
          >
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={{ base: 6, md: 8 }}>
              {DOCUMENT_LIST.map((doc, index) => (
                <MotionBox key={doc.id} variants={itemVariants}>
                  <DocumentCard
                    document={doc}
                    index={index}
                    onOpen={() => handleOpenDocument(doc)}
                  />
                </MotionBox>
              ))}
            </SimpleGrid>
          </MotionBox>

          {/* Footer note */}
          <MotionBox
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1, duration: 0.6 }}
            textAlign="center"
            pb={12}
          >
            <Box
              display="inline-block"
              px={6}
              py={3}
              borderRadius="full"
              bg={`${colors.brand.primary}10`}
              border={`1px solid ${colors.brand.primary}20`}
            >
              <Text fontSize="sm" color={colors.text.tertiary}>
                Последнее обновление документов: 29 декабря 2025 г.
              </Text>
            </Box>
          </MotionBox>
        </Container>
      </Box>

      {/* Document Modal */}
      <AnimatePresence>
        {isOpen && selectedDocument && (
          <DocumentModal
            document={selectedDocument}
            isOpen={isOpen}
            onClose={handleCloseDocument}
          />
        )}
      </AnimatePresence>
    </Box>
  );
}
