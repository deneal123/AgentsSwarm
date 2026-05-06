import { colors } from "@theme/tokens";

export const AUTH_PRIMARY_BUTTON_SX = {
  h: "50px",
  borderRadius: "12px",
  bg: colors.error,
  color: "white",
  fontWeight: "500",
  _hover: { bg: "#dc2626" },
  _active: { bg: "#dc2626" },
  _disabled: { bg: "rgba(239, 68, 68, 0.35)", color: colors.text.quaternary },
};
