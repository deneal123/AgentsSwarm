import { extendTheme } from "@chakra-ui/react";
import {
  colors,
  typography,
  borderRadius,
  shadows,
  spacing,
  transitions,
  gradients,
} from "./theme/tokens";

const brandPalette = {
  50: "#eef6ff",
  100: "#d9eaff",
  200: "#b6d4ff",
  300: "#8fbcff",
  400: "#5f99ff",
  500: colors.brand.primary,
  600: "#1f5de6",
  700: "#184ab8",
  800: "#153e96",
  900: "#122f70",
};

const legacyColors = {
  menu_gray: "#CCC3C2",
  main_dark: "#333",
  light_dark: "#666",
  main_yellow: "#FFBF00",
  main_red: "#FF0F00",
  menu_white: "#F8F8F8",
  date_gray: "#A9A9A9",
};

const chakraSpace = spacing.scale.reduce((acc, value, index) => {
  acc[index] = value;
  return acc;
}, {});

const theme = extendTheme({
  config: {
    initialColorMode: "dark",
    useSystemColorMode: false,
  },
  space: chakraSpace,
  fonts: {
    body: typography.fontFamily.primary,
    heading: typography.fontFamily.primary,
  },
  radii: {
    none: 0,
    sm: borderRadius.sm,
    md: borderRadius.md,
    lg: borderRadius.lg,
    xl: borderRadius.xl,
    "2xl": borderRadius["2xl"],
    card: borderRadius.md,
  },
  sizes: {
    container: {
      md: "48rem",
      lg: "62rem",
      xl: "75rem",
      "2xl": "88rem",
    },
  },
  shadows: {
    elevated: shadows.elevated,
    subtle: shadows.subtle,
    glow: shadows.glow,
    glowSubtle: shadows.glowSubtle,
  },
  styles: {
    global: () => ({
      body: {
        bg: colors.background.darkPrimary,
        color: colors.text.primary,
        fontFamily: typography.fontFamily.primary,
      },
      "*, *::before, *::after": {
        borderColor: colors.border.default,
      },
      "::selection": {
        backgroundColor: `${colors.brand.primary}55`,
        color: colors.text.primaryInverted,
      },
      "@keyframes gradientOrbit": {
        "0%": { transform: "rotate(0deg)" },
        "100%": { transform: "rotate(360deg)" },
      },
      "@keyframes glowPulse": {
        "0%": { opacity: 0.4 },
        "50%": { opacity: 0.9 },
        "100%": { opacity: 0.4 },
      },
      "@keyframes shimmerTrail": {
        "0%": { transform: "translateX(-20%)" },
        "100%": { transform: "translateX(120%)" },
      },
    }),
  },
  components: {
    Tooltip: {
      baseStyle: {
        background: colors.blur.dark,
        color: colors.text.primary,
        borderRadius: borderRadius.sm,
        px: spacing.sm,
        py: spacing[4],
        fontSize: "12px",
      },
    },
    Button: {
      baseStyle: {
        fontWeight: 500,
        borderRadius: borderRadius.sm,
        transition: transitions.smooth,
        position: "relative",
        overflow: "hidden",
        letterSpacing: "0.02em",
      },
      variants: {
        primary: {
          bgGradient: gradients.prism,
          color: colors.text.primary,
          boxShadow: "0 18px 45px rgba(47, 116, 255, 0.35)",
          border: "1px solid",
          borderColor: "rgba(255,255,255,0.08)",
          _before: {
            content: '""',
            position: "absolute",
            inset: 0,
            background: gradients.midnightMesh,
            opacity: 0.35,
            transition: "opacity 0.3s ease",
            pointerEvents: "none",
          },
          _after: {
            content: '""',
            position: "absolute",
            inset: "-150%",
            background:
              "conic-gradient(from 0deg, transparent 0%, rgba(255,255,255,0.8) 15%, transparent 30%)",
            animation: "gradientOrbit 18s linear infinite",
            opacity: 0.25,
            pointerEvents: "none",
          },
          _hover: {
            transform: "translateY(-1px) scale(1.01)",
            boxShadow: "0 25px 60px rgba(139, 92, 246, 0.45)",
            _before: { opacity: 0.6 },
          },
          _active: { transform: "scale(0.99)", boxShadow: "0 10px 25px rgba(47, 116, 255, 0.4)" },
          _disabled: {
            bg: colors.background.buttonDisabled,
            color: colors.text.quaternary,
            boxShadow: "none",
            opacity: 0.6,
          },
        },
        secondary: {
          color: colors.text.primary,
          border: "1px solid",
          borderColor: colors.border.medium,
          background: "rgba(5,5,5,0.35)",
          _before: {
            content: '""',
            position: "absolute",
            inset: "1px",
            borderRadius: borderRadius.sm,
            background: gradients.dusk,
            opacity: 0.6,
            transition: "opacity 0.3s ease",
            pointerEvents: "none",
          },
          _hover: {
            borderColor: "rgba(255,255,255,0.35)",
            boxShadow: shadows.glowSubtle,
            _before: { opacity: 0.9 },
          },
          _active: {
            boxShadow: "0 8px 20px rgba(0,0,0,0.45)",
            borderColor: "rgba(255,255,255,0.25)",
          },
          _disabled: {
            color: colors.text.quaternary,
            borderColor: colors.border.light,
            opacity: 0.5,
          },
        },
      },
    },
    Link: {
      baseStyle: {
        color: colors.text.secondary,
        transition: transitions.default,
        _hover: { color: colors.text.primary },
      },
    },
    Menu: {
      baseStyle: {
        list: {
          bg: colors.background.darkPrimary,
          border: "1px solid",
          borderColor: "rgba(255, 255, 255, 0.1)",
          boxShadow: "0 20px 40px rgba(0, 0, 0, 0.5), 0 0 30px rgba(47, 116, 255, 0.15)",
          py: 0,
          borderRadius: borderRadius.lg,
          overflow: "hidden",
        },
        item: {
          bg: "transparent",
          color: colors.text.primary,
          _hover: {
            bg: "rgba(47, 116, 255, 0.1)",
          },
          _focus: {
            bg: "rgba(47, 116, 255, 0.1)",
          },
        },
        divider: {
          borderColor: "rgba(255, 255, 255, 0.06)",
        },
      },
    },
  },
  colors: {
    ...legacyColors,
    brand: brandPalette,
    text: colors.text,
    background: colors.background,
    blur: colors.blur,
    border: colors.border,
    success: colors.success,
    error: colors.error,
    warning: colors.warning,
  },
  semanticTokens: {
    colors: {
      // Updated with design system tokens
      canvas: { default: "#f7f7f7", _dark: colors.background.darkPrimary },
      surface: { default: "white", _dark: colors.blur.dark },
      surfaceElevated: { default: "white", _dark: colors.blur.mid },
      borderSubtle: { default: "rgba(0,0,0,0.08)", _dark: colors.border.default },
      text: {
        primary: { default: "gray.800", _dark: colors.text.primary },
        muted: { default: "gray.600", _dark: colors.text.secondary },
        tertiary: { default: "gray.500", _dark: colors.text.tertiary },
      },
      accent: { default: "blue.600", _dark: colors.brand.primary },
    },
  },
});

export default theme;
