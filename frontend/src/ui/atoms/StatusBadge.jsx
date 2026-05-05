import React from "react";
import { Badge } from "@chakra-ui/react";

const LABELS = {
  healthy: "работает стабильно",
  unhealthy: "обнаружена ошибка",
  unknown: "статус неизвестен",
};

export default function StatusBadge({ ok, title, ...rest }) {
  if (ok == null)
    return (
      <Badge colorScheme="gray" title={title ?? LABELS.unknown} {...rest}>
        {LABELS.unknown}
      </Badge>
    );

  const label = ok ? LABELS.healthy : LABELS.unhealthy;
  const colorScheme = ok ? "green" : "red";

  return (
    <Badge colorScheme={colorScheme} title={title ?? label} {...rest} padding={8}>
      {label}
    </Badge>
  );
}
