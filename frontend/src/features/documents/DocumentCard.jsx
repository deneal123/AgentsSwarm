import React from "react";
import { Box, Heading, Text, Button, HStack, VStack, Badge } from "@chakra-ui/react";
import { css, keyframes } from "@emotion/react";
import { colors, borderRadius } from "@theme/tokens";
import TiltCard from "@ui/atoms/TiltCard";
import { ArrowForwardIcon } from "@chakra-ui/icons";

/* ───────── Keyframes ───────── */
const shimmer = keyframes`
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
`;

const pulse = keyframes`
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.05); }
`;

const float = keyframes`
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-4px); }
`;

/* ───────── Document Card ───────── */
export default function DocumentCard({ document, index, onOpen }) {
  const { title, subtitle, icon, lastUpdated, sections } = document;

  // Alternate gradient colors based on index
  const gradientColors = [
    [colors.brand.primary, colors.brand.secondary],
    [colors.brand.secondary, colors.brand.tertiary],
    [colors.brand.tertiary, colors.brand.primary],
    ["#f59e0b", "#ef4444"],
  ];

  const [color1, color2] = gradientColors[index % gradientColors.length];

  return (
    <TiltCard intensity="subtle">
      <Box
        position="relative"
        borderRadius={borderRadius.xl}
        overflow="hidden"
        bg={`linear-gradient(145deg, ${colors.background.darkPrimary}, ${colors.blur.mid})`}
        border={`1px solid ${colors.border.subtle}`}
        transition="all 0.4s cubic-bezier(0.4, 0, 0.2, 1)"
        cursor="pointer"
        onClick={onOpen}
        _hover={{
          borderColor: `${color1}60`,
          transform: "translateY(-4px)",
          boxShadow: `0 20px 40px -15px ${color1}30, 0 0 60px ${color1}15`,
        }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && onOpen()}
      >
        {/* Top gradient border */}
        <Box
          position="absolute"
          top={0}
          left={0}
          right={0}
          h="3px"
          bg={`linear-gradient(90deg, ${color1}, ${color2}, ${color1})`}
          backgroundSize="200% 100%"
          css={css`
            animation: ${shimmer} 4s linear infinite;
          `}
        />

        {/* Glow effect on hover */}
        <Box
          position="absolute"
          top="-50%"
          left="-50%"
          w="200%"
          h="200%"
          bg={`radial-gradient(circle at center, ${color1}08 0%, transparent 50%)`}
          opacity={0}
          transition="opacity 0.4s ease"
          pointerEvents="none"
          css={css`
            .chakra-box:hover > & {
              opacity: 1;
            }
          `}
        />

        {/* Content */}
        <Box px={{ base: 5, md: 6 }} py={{ base: 5, md: 6 }} position="relative">
          {/* Header */}
          <HStack spacing={4} mb={4} align="start">
            {/* Icon Container */}
            <Box position="relative">
              {/* Glow behind icon */}
              <Box
                position="absolute"
                inset={-2}
                borderRadius="xl"
                bg={`radial-gradient(circle, ${color1}30 0%, transparent 70%)`}
                filter="blur(8px)"
                css={css`
                  animation: ${pulse} 3s ease-in-out infinite;
                `}
              />
              <Box
                display="flex"
                alignItems="center"
                justifyContent="center"
                w="56px"
                h="56px"
                borderRadius="xl"
                bg={`linear-gradient(135deg, ${color1}25, ${color2}15)`}
                border={`1px solid ${color1}40`}
                position="relative"
                css={css`
                  animation: ${float} 5s ease-in-out infinite;
                `}
              >
                <Text fontSize="2xl">{icon}</Text>
              </Box>
            </Box>

            {/* Title & Subtitle */}
            <VStack align="start" spacing={2} flex={1}>
              <Heading
                as="h3"
                fontSize={{ base: "md", md: "lg" }}
                color={colors.text.primary}
                fontWeight="bold"
                lineHeight="1.3"
              >
                {title}
              </Heading>
              <Text fontSize="sm" color={colors.text.secondary} lineHeight="1.5" noOfLines={2}>
                {subtitle}
              </Text>
            </VStack>
          </HStack>

          {/* Divider */}
          <Box
            h="1px"
            bg={`linear-gradient(90deg, transparent, ${colors.border.subtle}, transparent)`}
            mb={4}
          />

          {/* Sections preview */}
          <VStack align="stretch" spacing={2} mb={5}>
            {sections.slice(0, 3).map((section, i) => (
              <HStack
                key={i}
                spacing={3}
                py={1.5}
                px={3}
                borderRadius="md"
                bg={`${color1}${8 - i * 2}`.padEnd(9, "0").slice(0, 9)}
                transition="all 0.2s ease"
                _hover={{
                  bg: `${color1}15`,
                  transform: "translateX(4px)",
                }}
              >
                <Box
                  w="6px"
                  h="6px"
                  borderRadius="full"
                  bg={color1}
                  boxShadow={`0 0 8px ${color1}`}
                  opacity={1 - i * 0.2}
                />
                <Text fontSize="sm" color={colors.text.tertiary} noOfLines={1} flex={1}>
                  {section.title}
                </Text>
              </HStack>
            ))}
            {sections.length > 3 && (
              <Text fontSize="xs" color={colors.text.quaternary} pl={3} mt={1}>
                + ещё {sections.length - 3} {sections.length - 3 === 1 ? "раздел" : "разделов"}
              </Text>
            )}
          </VStack>

          {/* Footer */}
          <HStack justify="space-between" align="center">
            {/* Meta info */}
            <HStack spacing={3}>
              <Badge
                bg={`${color1}20`}
                color={color1}
                fontSize="xs"
                px={2.5}
                py={1}
                borderRadius="full"
                fontWeight="medium"
              >
                {sections.length} разделов
              </Badge>
              <Text fontSize="xs" color={colors.text.quaternary}>
                {lastUpdated}
              </Text>
            </HStack>

            {/* Action button */}
            <Button
              size="sm"
              rightIcon={<ArrowForwardIcon />}
              bg="transparent"
              color={color1}
              fontWeight="medium"
              px={4}
              border={`1px solid ${color1}40`}
              borderRadius="full"
              _hover={{
                bg: `${color1}15`,
                borderColor: color1,
                transform: "translateX(2px)",
              }}
              transition="all 0.2s ease"
              onClick={(e) => {
                e.stopPropagation();
                onOpen();
              }}
            >
              Открыть
            </Button>
          </HStack>
        </Box>

        {/* Corner decorations */}
        <Box
          position="absolute"
          bottom={-40}
          right={-40}
          w="120px"
          h="120px"
          borderRadius="full"
          bg={`radial-gradient(circle, ${color2}15 0%, transparent 70%)`}
          pointerEvents="none"
        />
      </Box>
    </TiltCard>
  );
}
