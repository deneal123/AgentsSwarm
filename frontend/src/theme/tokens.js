/**
 * Design System Tokens
 * Centralized design constants for TeleRAG platform
 * Based on provided design specification
 */

export const colors = {
  // Text colors
  text: {
    primary: "#ffffff",
    primaryInverted: "#050505",
    secondary: "rgba(255, 255, 255, 0.75)",
    tertiary: "rgba(255, 255, 255, 0.5)",
    quaternary: "rgba(255, 255, 255, 0.25)",
  },

  // Background colors
  background: {
    darkPrimary: "#050505",
    darkPrimary75: "rgba(5, 5, 5, 0.75)",
    darkPrimary50: "rgba(5, 5, 5, 0.5)",
    darkPrimary25: "rgba(5, 5, 5, 0.25)",
    buttonActive: "#ffffff",
    buttonDisabled: "rgba(255, 255, 255, 0.5)",
    chineseBlack10: "rgba(16, 16, 16, 0.1)",
    chineseBlack50: "rgba(16, 16, 16, 0.5)",
    jet30: "rgba(53, 53, 53, 0.3)",
    jet40: "rgba(53, 53, 53, 0.4)",
    jet50: "rgba(53, 53, 53, 0.5)",
  },

  // Blur backgrounds
  blur: {
    dark: "rgba(21, 21, 21, 0.75)",
    mid: "rgba(53, 53, 53, 0.75)",
    medium: "rgba(30, 30, 30, 0.7)",
    light: "rgba(21, 21, 21, 0.5)",
    accent: "rgba(80, 80, 80, 0.75)",
  },

  // Border colors
  border: {
    default: "rgba(255, 255, 255, 0.05)",
    subtle: "rgba(255, 255, 255, 0.08)",
    medium: "rgba(255, 255, 255, 0.12)",
    light: "rgba(255, 255, 255, 0.15)",
  },

  // Brand accent colors
  brand: {
    primary: "#2f74ff",
    secondary: "#8b5cf6",
    tertiary: "#1dd1a1",
  },

  // Status colors
  success: "#10b981", // green
  error: "#ef4444", // red
  warning: "#f59e0b", // orange
};

colors.blur.medium = colors.blur.medium ?? colors.blur.mid;
colors.blur.mid = colors.blur.mid ?? colors.blur.medium;

export const typography = {
  fontFamily: {
    // Используем Montserrat как основной шрифт (загружается из Google Fonts в index.html)
    primary: "'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    fallback: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif",
  },

  // Title styles
  title: {
    large: {
      fontSize: "30px",
      lineHeight: "115%",
      fontWeight: 500,
    },
    medium: {
      fontSize: "24px",
      lineHeight: "125%",
      fontWeight: 500,
    },
    small: {
      fontSize: "22px",
      lineHeight: "115%",
      fontWeight: 500,
    },
  },

  // Subtitle styles
  subtitle: {
    large: {
      fontSize: "20px",
      lineHeight: "125%",
      fontWeight: 500,
    },
    medium: {
      fontSize: "16px",
      lineHeight: "125%",
      fontWeight: 500,
    },
  },

  // Body text styles
  body: {
    large: {
      fontSize: "18px",
      lineHeight: "150%",
      fontWeight: 500,
    },
    medium: {
      fontSize: "14px",
      lineHeight: "140%",
      fontWeight: 500,
    },
  },

  // Footnote styles
  footnote: {
    medium: {
      fontSize: "14px",
      lineHeight: "107%",
      fontWeight: 500,
    },
    small: {
      fontSize: "12px",
      lineHeight: "125%",
      fontWeight: 500,
    },
  },
};

const spacingScale = [
  "0px", // 0
  "2px", // 1
  "4px", // 2
  "6px", // 3
  "8px", // 4
  "12px", // 5
  "16px", // 6
  "20px", // 7
  "24px", // 8
  "28px", // 9
  "32px", // 10
  "36px", // 11
  "40px", // 12
  "48px", // 13
  "56px", // 14
  "64px", // 15
  "72px", // 16
  "80px", // 17
  "96px", // 18
  "112px", // 19
  "128px", // 20
  "160px", // 21
];

const spacingAliases = {
  none: spacingScale[0],
  "3xs": spacingScale[1],
  "2xs": spacingScale[2],
  xs: spacingScale[3],
  sm: spacingScale[4],
  md: spacingScale[6],
  lg: spacingScale[8],
  xl: spacingScale[10],
  "2xl": spacingScale[12],
  "3xl": spacingScale[13],
  "4xl": spacingScale[14],
  "5xl": spacingScale[15],
  "6xl": spacingScale[16],
  "7xl": spacingScale[17],
  "8xl": spacingScale[18],
  "9xl": spacingScale[19],
  "10xl": spacingScale[20],
  "11xl": spacingScale[21],
};

export const spacing = Object.assign([...spacingScale], {
  scale: spacingScale,
  ...spacingAliases,
});

export const borderRadius = {
  sm: "10px",
  md: "15px",
  lg: "20px",
  xl: "25px",
  "2xl": "30px",
  full: "9999px",
};

export const borderWidth = {
  default: "1px",
  medium: "2px",
  thick: "3px",
};

export const blur = {
  strength: {
    default: "25px",
    light: "15px",
    heavy: "40px",
  },
};

export const shadows = {
  subtle: "0 1px 4px rgba(0, 0, 0, 0.12)",
  elevated: "0 12px 32px rgba(0, 0, 0, 0.32)",
  glow: "0 0 28px rgba(139, 92, 246, 0.65)",
  glowSubtle: "0 0 18px rgba(47, 116, 255, 0.25)",
};

export const transitions = {
  default: "0.2s ease",
  smooth: "0.3s ease-in-out",
  slow: "0.5s ease",
};

export const gradients = {
  aurora:
    "linear-gradient(135deg, rgba(47, 116, 255, 0.9) 0%, rgba(12, 67, 53, 0.85) 45%, rgba(38, 13, 97, 0.95) 100%)",
  prism: "linear-gradient(120deg, #2f74ff 0%, #8b5cf6 55%, #158f6eff 100%)",
  dusk: "linear-gradient(160deg, rgba(47, 116, 255, 0.15) 0%, rgba(139, 92, 246, 0.25) 65%, rgba(29, 209, 161, 0.15) 100%)",
  midnightMesh:
    "radial-gradient(circle at 20% 20%, rgba(47, 116, 255, 0.25), transparent 35%), radial-gradient(circle at 80% 30%, rgba(139, 92, 246, 0.25), transparent 35%), radial-gradient(circle at 50% 80%, rgba(29, 209, 161, 0.3), transparent 40%)",
  horizon: "linear-gradient(180deg, rgba(5,5,5,0) 0%, rgba(5,5,5,0.85) 80%)",
};

export const breakpoints = {
  mobile: "320px",
  tablet: "768px",
  desktop: "1024px",
  wide: "1280px",
};

export const dimensions = {
  iconButton: {
    width: "40px",
    height: "40px",
  },
  button: {
    heightMobile: "45px",
    heightDesktop: "50px",
  },
};

// Default export as unified tokens object
export const tokens = {
  colors,
  typography,
  spacing,
  borderRadius,
  borderWidth,
  blur,
  shadows,
  transitions,
  breakpoints,
  dimensions,
  gradients,
};


export const chat = {
  modelSelector: {
    triggerBg: "rgba(255, 255, 255, 0.04)",
    triggerBgHover: "rgba(255, 255, 255, 0.08)",
    triggerBorder: "rgba(255, 255, 255, 0.14)",
    triggerBorderActive: "rgba(239, 68, 68, 0.46)",
    triggerText: "rgba(255, 255, 255, 0.94)",
    activeText: "#fecaca",
    activeBg: "rgba(239, 68, 68, 0.16)",
    activeBgHover: "rgba(239, 68, 68, 0.22)",
    menuBg: "rgba(9, 9, 9, 0.96)",
    menuBorder: "rgba(255, 255, 255, 0.14)",
    itemHover: "rgba(255, 255, 255, 0.06)",
    itemSelectedBg: "rgba(239, 68, 68, 0.16)",
  },
};
