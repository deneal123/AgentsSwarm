import React, { memo, useMemo } from "react";
import { Box, Flex, HStack, Text } from "@chakra-ui/react";
import { SummaryPanel } from "@ui/molecules";
import { Title, Body } from "@ui/atoms";
import { colors, borderRadius, gradients, spacing } from "@theme/tokens";

const PageHeader = memo(function PageHeader({
  title,
  subtitle,
  description,
  eyebrow,
  actions,
  right,
  metrics,
  ...rest
}) {
  // Мемоизация преобразования метрик
  const summaryItems = useMemo(() => {
    if (!Array.isArray(metrics) || metrics.length === 0) return null;
    return metrics.map((m) => ({ label: m.label, value: m.value, tooltip: m.caption }));
  }, [metrics]);

  const metricsColumns = useMemo(() => {
    if (!Array.isArray(metrics)) return { base: 1 };
    return { base: 1, md: metrics.length };
  }, [metrics]);

  return (
    <Box
      position="relative"
      borderRadius={{ base: borderRadius.lg, md: borderRadius["2xl"] }}
      overflow="hidden"
      border="1px solid rgba(255,255,255,0.08)"
      bg={`linear-gradient(145deg, rgba(6,8,15,0.92), rgba(5,5,5,0.6)), ${gradients.midnightMesh}`}
      px={{ base: spacing.xl, md: spacing["2xl"] }}
      py={{ base: spacing.lg, md: spacing["2xl"] }}
      boxShadow="0 35px 80px rgba(3,4,8,0.55)"
      _before={{
        content: '""',
        position: "absolute",
        inset: "-30%",
        background: gradients.aurora,
        opacity: 0.35,
        filter: "blur(70px)",
        pointerEvents: "none",
      }}
      _after={{
        content: '""',
        position: "absolute",
        inset: 0,
        backgroundImage: "linear-gradient(120deg, rgba(255,255,255,0.05) 0%, transparent 45%)",
        opacity: 0.4,
        pointerEvents: "none",
      }}
      {...rest}
    >
      <Flex direction="column" gap={6} position="relative" zIndex={1}>
        <Flex
          align={{ base: "flex-start", md: "center" }}
          justify="space-between"
          gap={6}
          flexWrap="wrap"
        >
          <Box maxW="720px">
            {eyebrow && (
              <Text
                fontSize="xs"
                letterSpacing="0.28em"
                textTransform="uppercase"
                color={colors.text.tertiary}
                mb={2}
              >
                {eyebrow}
              </Text>
            )}
            <Title variant="medium" fontSize={{ base: "28px", md: "36px" }} lineHeight="1.1">
              {title}
            </Title>
            {subtitle && (
              <Body variant="large" color={colors.text.tertiary} mt={2}>
                {subtitle}
              </Body>
            )}
            {description && (
              <Body variant="medium" color={colors.text.secondary} mt={3} maxW="640px">
                {description}
              </Body>
            )}
          </Box>
          {(actions || right) && <HStack spacing={3}>{actions || right}</HStack>}
        </Flex>

        {summaryItems && (
          <Box
            borderRadius={borderRadius.xl}
            border="1px solid rgba(255,255,255,0.08)"
            p={{ base: spacing.md, md: spacing.lg }}
            bg="rgba(5,5,10,0.65)"
            backdropFilter="blur(18px)"
          >
            <SummaryPanel items={summaryItems} columns={metricsColumns} size="compact" />
          </Box>
        )}
      </Flex>
    </Box>
  );
});

export default PageHeader;
