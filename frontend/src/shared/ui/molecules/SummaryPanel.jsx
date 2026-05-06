import React from "react";
import { SimpleGrid } from "@chakra-ui/react";
import { StatCard } from "@shared/ui/atoms";

/**
 * SummaryPanel - lightweight panel to show several stat cards in a responsive grid
 * props:
 *  - items: [{ key?, label, value, icon, color, badge, tooltip }]
 *  - columns: responsive columns prop for SimpleGrid (default { base: 1, md: 2, lg: 4 })
 */
export default function SummaryPanel({
  items = [],
  columns = { base: 1, md: 2, lg: 4 },
  size = "normal",
}) {
  if (!items || items.length === 0) return null;

  return (
    <SimpleGrid
      columns={columns}
      spacing={size === "compact" ? { base: 2, md: 3 } : { base: 4, md: 6 }}
      w="full"
    >
      {items.map((it, i) => (
        <StatCard
          key={it.key ?? `${i}-${it.label}`}
          label={it.label}
          value={it.value}
          icon={it.icon}
          color={it.color}
          badge={it.badge}
          tooltip={it.tooltip}
          size={size}
        />
      ))}
    </SimpleGrid>
  );
}
