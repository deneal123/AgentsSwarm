import React from "react";
import {
  Box,
  Heading,
  Text,
  VStack,
  HStack,
  IconButton,
  Badge,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  useBreakpointValue,
  Flex,
} from "@chakra-ui/react";
import { motion, AnimatePresence } from "framer-motion";
import { css, keyframes } from "@emotion/react";
import { colors, borderRadius, gradients } from "@theme/tokens";
import { CloseIcon } from "@chakra-ui/icons";

const MotionBox = motion(Box);
const MotionFlex = motion(Flex);

/* ───────── Keyframes ───────── */
const shimmer = keyframes`
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
`;

const glow = keyframes`
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.6; }
`;

/* ───────── Animation Variants ───────── */
const overlayVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.3 } },
  exit: { opacity: 0, transition: { duration: 0.2 } },
};

const modalVariants = {
  hidden: {
    opacity: 0,
    scale: 0.9,
    y: 50,
  },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: [0.25, 0.46, 0.45, 0.94],
    },
  },
  exit: {
    opacity: 0,
    scale: 0.9,
    y: 50,
    transition: { duration: 0.25 },
  },
};

const contentVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      delay: 0.15,
      staggerChildren: 0.08,
    },
  },
};

const sectionVariants = {
  hidden: { opacity: 0, x: -10 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.3 },
  },
};

/* ───────── Document Modal ───────── */
export default function DocumentModal({ document: docData, isOpen, onClose }) {
  const { title, subtitle, icon, lastUpdated, sections } = docData;
  const modalWidth = useBreakpointValue({ base: "95vw", md: "80vw", lg: "65vw" });

  // Handle escape key
  React.useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [onClose]);

  // Prevent body scroll when modal is open
  React.useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <AnimatePresence mode="wait">
      {isOpen && (
        <>
          {/* Overlay */}
          <MotionBox
            key="overlay"
            position="fixed"
            top={0}
            left={0}
            right={0}
            bottom={0}
            bg="blackAlpha.800"
            backdropFilter="blur(12px)"
            zIndex={1000}
            variants={overlayVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            onClick={onClose}
          />

          {/* Modal Wrapper - Centered with Flexbox */}
          <MotionFlex
            key="modal"
            position="fixed"
            top={0}
            left={0}
            right={0}
            bottom={0}
            zIndex={1001}
            alignItems="center"
            justifyContent="center"
            pointerEvents="none"
            p={{ base: 4, md: 6 }}
          >
            <MotionBox
              variants={modalVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              w={modalWidth}
              maxW="900px"
              maxH={{ base: "90vh", md: "85vh" }}
              pointerEvents="auto"
              onClick={(e) => e.stopPropagation()}
            >
              <Box
                position="relative"
                borderRadius={borderRadius.xl}
                overflow="hidden"
                bg={colors.background.darkPrimary}
                border={`1px solid ${colors.border.medium}`}
                boxShadow={`0 25px 60px -15px rgba(0, 0, 0, 0.6), 0 0 80px ${colors.brand.primary}15`}
              >
                {/* Header */}
                <Box
                  position="relative"
                  px={{ base: 5, md: 8 }}
                  py={{ base: 5, md: 6 }}
                  bg={`linear-gradient(135deg, ${colors.brand.primary}12, ${colors.brand.secondary}08)`}
                  borderBottom={`1px solid ${colors.border.subtle}`}
                >
                  {/* Top gradient line with shimmer */}
                  <Box
                    position="absolute"
                    top={0}
                    left={0}
                    right={0}
                    h="3px"
                    bg={`linear-gradient(90deg, ${colors.brand.primary}, ${colors.brand.secondary}, ${colors.brand.tertiary}, ${colors.brand.primary})`}
                    backgroundSize="300% 100%"
                    css={css`
                      animation: ${shimmer} 3s linear infinite;
                    `}
                  />

                  <HStack justify="space-between" align="start">
                    <HStack spacing={4}>
                      {/* Icon */}
                      <Box
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                        w={{ base: "50px", md: "64px" }}
                        h={{ base: "50px", md: "64px" }}
                        borderRadius="xl"
                        bg={`linear-gradient(135deg, ${colors.brand.primary}20, ${colors.brand.secondary}20)`}
                        border={`1px solid ${colors.brand.primary}30`}
                        boxShadow={`0 0 30px ${colors.brand.primary}25`}
                      >
                        <Text fontSize={{ base: "2xl", md: "3xl" }}>{icon}</Text>
                      </Box>

                      {/* Title */}
                      <VStack align="start" spacing={1}>
                        <Heading
                          as="h2"
                          fontSize={{ base: "lg", md: "xl", lg: "2xl" }}
                          fontWeight="bold"
                          bgGradient={gradients.prism}
                          bgClip="text"
                        >
                          {title}
                        </Heading>
                        <HStack spacing={3} flexWrap="wrap">
                          <Text fontSize="sm" color={colors.text.secondary}>
                            {subtitle}
                          </Text>
                          <Badge
                            bg={`${colors.brand.primary}20`}
                            color={colors.brand.primary}
                            fontSize="xs"
                            px={2.5}
                            py={0.5}
                            borderRadius="full"
                          >
                            {lastUpdated}
                          </Badge>
                        </HStack>
                      </VStack>
                    </HStack>

                    {/* Close button */}
                    <IconButton
                      icon={<CloseIcon boxSize={3} />}
                      size="sm"
                      minW="44px"
                      minH="44px"
                      variant="ghost"
                      color={colors.text.tertiary}
                      borderRadius="full"
                      border={`1px solid ${colors.border.subtle}`}
                      _hover={{
                        bg: `${colors.brand.primary}15`,
                        borderColor: colors.brand.primary,
                        color: colors.brand.primary,
                      }}
                      onClick={onClose}
                      aria-label="Закрыть"
                    />
                  </HStack>
                </Box>

                {/* Content */}
                <Box
                  maxH={{ base: "calc(90vh - 220px)", md: "calc(85vh - 200px)" }}
                  overflowY="auto"
                  px={{ base: 5, md: 8 }}
                  py={{ base: 5, md: 6 }}
                  css={css`
                    &::-webkit-scrollbar {
                      width: 6px;
                    }
                    &::-webkit-scrollbar-track {
                      background: transparent;
                    }
                    &::-webkit-scrollbar-thumb {
                      background: ${colors.border.medium};
                      border-radius: 3px;
                    }
                    &::-webkit-scrollbar-thumb:hover {
                      background: ${colors.brand.primary}60;
                    }
                  `}
                >
                  <MotionBox variants={contentVariants} initial="hidden" animate="visible">
                    <Accordion allowMultiple defaultIndex={[0]}>
                      {sections.map((section, index) => (
                        <MotionBox key={index} variants={sectionVariants}>
                          <AccordionItem
                            border="none"
                            mb={3}
                            borderRadius={borderRadius.lg}
                            overflow="hidden"
                          >
                            <AccordionButton
                              bg={`${colors.brand.primary}06`}
                              border={`1px solid ${colors.border.subtle}`}
                              borderRadius={borderRadius.lg}
                              px={5}
                              py={4}
                              _hover={{
                                bg: `${colors.brand.primary}12`,
                                borderColor: `${colors.brand.primary}40`,
                              }}
                              _expanded={{
                                bg: `${colors.brand.primary}10`,
                                borderColor: `${colors.brand.primary}30`,
                                borderBottomRadius: 0,
                              }}
                              transition="all 0.2s ease"
                            >
                              <HStack flex="1" textAlign="left" spacing={3}>
                                <Box
                                  w="8px"
                                  h="8px"
                                  borderRadius="full"
                                  bg={colors.brand.primary}
                                  boxShadow={`0 0 12px ${colors.brand.primary}`}
                                />
                                <Heading
                                  as="h3"
                                  size="sm"
                                  color={colors.text.primary}
                                  fontWeight="semibold"
                                >
                                  {section.title}
                                </Heading>
                              </HStack>
                              <AccordionIcon color={colors.brand.primary} />
                            </AccordionButton>

                            <AccordionPanel
                              bg={`${colors.brand.primary}04`}
                              borderX={`1px solid ${colors.border.subtle}`}
                              borderBottom={`1px solid ${colors.border.subtle}`}
                              borderBottomRadius={borderRadius.lg}
                              px={5}
                              py={5}
                            >
                              <Text
                                fontSize="sm"
                                color={colors.text.secondary}
                                lineHeight="1.9"
                                whiteSpace="pre-line"
                              >
                                {section.content}
                              </Text>
                            </AccordionPanel>
                          </AccordionItem>
                        </MotionBox>
                      ))}
                    </Accordion>
                  </MotionBox>
                </Box>

                {/* Footer */}
                <Box
                  px={{ base: 5, md: 8 }}
                  py={4}
                  bg={`${colors.brand.primary}04`}
                  borderTop={`1px solid ${colors.border.subtle}`}
                >
                  <HStack justify="space-between" align="center">
                    <Text fontSize="xs" color={colors.text.quaternary}>
                      © {new Date().getFullYear()} GPTHub by InCellCorp. Все права защищены.
                    </Text>
                    <HStack spacing={2}>
                      <Box
                        w="6px"
                        h="6px"
                        borderRadius="full"
                        bg={colors.success}
                        css={css`
                          animation: ${glow} 2s ease-in-out infinite;
                        `}
                      />
                      <Text fontSize="xs" color={colors.text.tertiary}>
                        Документ актуален
                      </Text>
                    </HStack>
                  </HStack>
                </Box>

                {/* Corner decorations */}
                <Box
                  position="absolute"
                  top={-60}
                  right={-60}
                  w="180px"
                  h="180px"
                  borderRadius="full"
                  bg={`radial-gradient(circle, ${colors.brand.primary}08 0%, transparent 70%)`}
                  pointerEvents="none"
                />
                <Box
                  position="absolute"
                  bottom={-40}
                  left={-40}
                  w="120px"
                  h="120px"
                  borderRadius="full"
                  bg={`radial-gradient(circle, ${colors.brand.secondary}08 0%, transparent 70%)`}
                  pointerEvents="none"
                />
              </Box>
            </MotionBox>
          </MotionFlex>
        </>
      )}
    </AnimatePresence>
  );
}
