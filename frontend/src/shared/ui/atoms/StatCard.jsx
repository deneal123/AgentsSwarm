import React, { memo, useMemo } from "react";
import {
  Box,
  HStack,
  VStack,
  Stat,
  StatLabel,
  StatNumber,
  Icon,
  Tooltip,
  Badge,
} from "@chakra-ui/react";
import { MotionBox } from "@shared/ui/lib/motionPrimitives";
import { colors, spacing } from "@theme/tokens";

/**
 * StatCard - small reusable stat card used by SummaryPanel
 * props:
 *  - label: string
 *  - value: node
 *  - icon: React component
 *  - color: color token for value/icon
 *  - badge: { label, colorScheme }
 *  - tooltip: string
 */
const StatCard = memo(function StatCard({
  label,
  value,
  icon: IconComp,
  color,
  badge,
  tooltip,
  size = "normal",
}) {
  const isCompact = size === "compact";

  const iconBox = useMemo(
    () =>
      IconComp ? (
        <Box aria-hidden>
          <Icon as={IconComp} boxSize={isCompact ? 4 : 6} color={color || colors.brand.primary} />
        </Box>
      ) : null,
    [IconComp, isCompact, color],
  );

  const content = useMemo(
    () => (
      <HStack spacing={isCompact ? 3 : 4} align="center">
        {iconBox}

        <VStack align="stretch" spacing={isCompact ? 0 : 0} flex={1}>
          <Stat>
            <StatLabel fontSize={isCompact ? "xs" : "sm"} color={colors.text.tertiary}>
              {label}
            </StatLabel>
            <StatNumber
              fontSize={isCompact ? { base: "16px", md: "18px" } : { base: "20px", md: "24px" }}
              color={color || colors.brand.primary}
            >
              {value}
            </StatNumber>
          </Stat>
        </VStack>

        {badge && (
          <Badge
            colorScheme={badge.colorScheme || "green"}
            fontSize={isCompact ? "10px" : undefined}
            px={isCompact ? 2 : undefined}
            py={isCompact ? 0.5 : undefined}
          >
            {badge.label}
          </Badge>
        )}
      </HStack>
    ),
    [iconBox, isCompact, label, value, color, badge],
  );

  return (
    <MotionBox
      whileHover={isCompact ? undefined : { y: -6 }}
      transition={{ duration: 0.2 }}
      position="relative"
    >
      <Box
        bg={colors.blur.medium}
        border="1px solid"
        borderColor={colors.border.default}
        borderRadius={isCompact ? "8px" : "12px"}
        p={isCompact ? { base: spacing.xs, md: spacing.sm } : { base: spacing.md, md: spacing.lg }}
      >
        {tooltip ? <Tooltip label={tooltip}>{content}</Tooltip> : content}
      </Box>
    </MotionBox>
  );
});

export default StatCard;
