import { chat, colors, gradients } from "@theme/tokens";

export const HOME_SIDEBAR_COLLAPSE_STORAGE_KEY = "gpthub.home.sidebar.collapsed";

export const HOME_AUTH_THEME = {
  accent: colors.error,
  accentHover: "#dc2626",
  outlineButton: {
    variant: "outline",
    borderColor: colors.border.light,
    color: colors.text.secondary,
    bg: colors.background.darkPrimary25,
    _hover: {
      color: colors.text.primary,
      bg: colors.border.default,
      borderColor: chat.modelSelector.triggerBorderActive,
    },
  },
};

export const HOME_THEME = {
  pageBg: colors.background.darkPrimary,
  panelBg: colors.background.darkPrimary25,
  panelBorder: colors.border.default,
  panelBorderStrong: colors.border.light,
  panelBorderSubtle: colors.border.subtle,
  panelHover: colors.border.default,
  panelHoverStrong: "rgba(255,255,255,0.09)",
  selectedBg: chat.modelSelector.itemSelectedBg,
  selectedBorder: chat.modelSelector.triggerBorderActive,
  formControlBg: colors.border.default,
  formControlBorder: colors.border.light,
  nativeOption: { color: "#111", background: "#fff" },
};

export const SEARCH_THEME = {
  cardBg: colors.border.subtle,
  cardBorder: colors.border.medium,
  controlBg: colors.border.medium,
  controlBorder: colors.border.light,
  nativeOption: { color: "#111", background: "#fff" },
  inputBg: colors.border.subtle,
  inputBgHover: colors.border.default,
  inputBgFocus: colors.border.medium,
  focusMask: "linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0)",
  actionGradient: gradients.prism,
  actionGradientSoft: `linear-gradient(135deg, ${colors.brand.primary}30, ${colors.brand.secondary}30)`,
  actionGradientMuted: `linear-gradient(135deg, ${colors.brand.primary}20, ${colors.brand.secondary}20)`,
};
