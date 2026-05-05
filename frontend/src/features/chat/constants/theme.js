export const CHAT_FONT_FAMILY = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";

export const CHAT_THEME = {
  pageBg: '#080808',
  pageGradient: 'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(239,68,68,0.07) 0%, transparent 60%), #080808',
  panelBg: 'rgba(14, 14, 14, 0.96)',
  sidebarBg: 'rgba(11, 11, 11, 0.98)',
  panelBorder: 'rgba(255, 255, 255, 0.08)',
  panelBorderStrong: 'rgba(255, 255, 255, 0.13)',
  panelHover: 'rgba(255, 255, 255, 0.06)',
  panelActive: 'rgba(255, 255, 255, 0.1)',
  userBubble: 'rgba(239, 68, 68, 0.15)',
  userBubbleBorder: 'rgba(239, 68, 68, 0.3)',
  agentBubble: 'transparent',
  agentBubbleBorder: 'transparent',
  inputBg: 'rgba(255, 255, 255, 0.05)',
  inputBorder: 'rgba(255, 255, 255, 0.12)',
  inputBorderFocus: 'rgba(239, 68, 68, 0.5)',
  inputStickyBg: 'rgba(8, 8, 8, 0.95)',
  headerBg: 'rgba(10, 10, 10, 0.95)',
  accent: '#ef4444',
  accentHover: '#dc2626',
  accentSoft: 'rgba(239, 68, 68, 0.18)',
  accentGlow: 'rgba(239, 68, 68, 0.12)',
  textPrimary: 'rgba(255, 255, 255, 0.93)',
  textSecondary: 'rgba(255, 255, 255, 0.55)',
  textTertiary: 'rgba(255, 255, 255, 0.35)',
};

export const CHAT_SCROLLBAR_SX = {
  scrollbarWidth: 'thin',
  scrollbarColor: 'rgba(255,255,255,0.12) transparent',
  '&::-webkit-scrollbar': { width: '5px' },
  '&::-webkit-scrollbar-track': { background: 'transparent' },
  '&::-webkit-scrollbar-thumb': {
    background: 'rgba(255,255,255,0.12)',
    borderRadius: '99px',
  },
  '&::-webkit-scrollbar-thumb:hover': { background: 'rgba(255,255,255,0.22)' },
};
