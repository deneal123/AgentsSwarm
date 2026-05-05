import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { colors } from '@theme/tokens';

// Chat Theme Context для управления темами оформления
const ChatThemeContext = createContext(null);

// Предустановленные темы
const PRESET_THEMES = {
  default: {
    name: 'По умолчанию',
    colors: {
      primary: colors.brand.primary,
      secondary: colors.brand.secondary,
      background: 'rgba(5,5,5,0.95)',
      surface: 'rgba(255,255,255,0.05)',
      border: 'rgba(255,255,255,0.1)',
      text: {
        primary: colors.text.primary,
        secondary: colors.text.secondary,
        tertiary: colors.text.tertiary
      }
    },
    borderRadius: '12px',
    fontFamily: '"Inter", sans-serif'
  },

  ocean: {
    name: 'Океан',
    colors: {
      primary: '#00D4FF',
      secondary: '#0099CC',
      background: 'linear-gradient(135deg, #0c4a6e 0%, #082f49 100%)',
      surface: 'rgba(0, 212, 255, 0.1)',
      border: 'rgba(0, 212, 255, 0.3)',
      text: {
        primary: '#ffffff',
        secondary: '#e0f2fe',
        tertiary: '#bae6fd'
      }
    },
    borderRadius: '16px',
    fontFamily: '"Inter", sans-serif'
  },

  sunset: {
    name: 'Закат',
    colors: {
      primary: '#FF6B35',
      secondary: '#F7931E',
      background: 'linear-gradient(135deg, #7c2d12 0%, #9a3412 100%)',
      surface: 'rgba(255, 107, 53, 0.1)',
      border: 'rgba(255, 107, 53, 0.3)',
      text: {
        primary: '#ffffff',
        secondary: '#fed7aa',
        tertiary: '#fdba74'
      }
    },
    borderRadius: '8px',
    fontFamily: '"Inter", sans-serif'
  },

  forest: {
    name: 'Лес',
    colors: {
      primary: '#22C55E',
      secondary: '#16A34A',
      background: 'linear-gradient(135deg, #14532d 0%, #166534 100%)',
      surface: 'rgba(34, 197, 94, 0.1)',
      border: 'rgba(34, 197, 94, 0.3)',
      text: {
        primary: '#ffffff',
        secondary: '#d1fae5',
        tertiary: '#a7f3d0'
      }
    },
    borderRadius: '20px',
    fontFamily: '"Inter", sans-serif'
  },

  purple: {
    name: 'Фиолетовый',
    colors: {
      primary: '#A855F7',
      secondary: '#9333EA',
      background: 'linear-gradient(135deg, #581c87 0%, #7c3aed 100%)',
      surface: 'rgba(168, 85, 247, 0.1)',
      border: 'rgba(168, 85, 247, 0.3)',
      text: {
        primary: '#ffffff',
        secondary: '#e9d5ff',
        tertiary: '#d8b4fe'
      }
    },
    borderRadius: '12px',
    fontFamily: '"Roboto", sans-serif'
  }
};

// Chat Theme Provider компонент
export function ChatThemeProvider({ children, initialTheme = 'default' }) {
  const [currentTheme, setCurrentTheme] = useState(initialTheme);
  const [customThemes, setCustomThemes] = useState({});
  const [themeSettings, setThemeSettings] = useState({
    messageSpacing: 'comfortable', // compact, comfortable, spacious
    fontSize: 'medium', // small, medium, large
    animations: true,
    soundEnabled: false
  });

  // Загрузка темы из localStorage
  useEffect(() => {
    const savedTheme = localStorage.getItem('chat_theme');
    const savedCustomThemes = localStorage.getItem('chat_custom_themes');
    const savedSettings = localStorage.getItem('chat_theme_settings');

    if (savedTheme && PRESET_THEMES[savedTheme]) {
      setCurrentTheme(savedTheme);
    }

    if (savedCustomThemes) {
      try {
        setCustomThemes(JSON.parse(savedCustomThemes));
      } catch (error) {
        console.error('Failed to load custom themes:', error);
      }
    }

    if (savedSettings) {
      try {
        setThemeSettings(JSON.parse(savedSettings));
      } catch (error) {
        console.error('Failed to load theme settings:', error);
      }
    }
  }, []);

  // Сохранение темы в localStorage
  const saveTheme = useCallback((themeName) => {
    localStorage.setItem('chat_theme', themeName);
    setCurrentTheme(themeName);
  }, []);

  // Получение текущей темы
  const getCurrentTheme = useCallback(() => {
    return customThemes[currentTheme] || PRESET_THEMES[currentTheme] || PRESET_THEMES.default;
  }, [currentTheme, customThemes]);

  // Создание кастомной темы
  const createCustomTheme = useCallback((themeName, themeData) => {
    const newThemes = {
      ...customThemes,
      [themeName]: {
        ...themeData,
        isCustom: true,
        createdAt: new Date().toISOString()
      }
    };
    setCustomThemes(newThemes);
    localStorage.setItem('chat_custom_themes', JSON.stringify(newThemes));
    return themeName;
  }, [customThemes]);

  // Удаление кастомной темы
  const deleteCustomTheme = useCallback((themeName) => {
    if (!customThemes[themeName]) return;

    const newThemes = { ...customThemes };
    delete newThemes[themeName];
    setCustomThemes(newThemes);
    localStorage.setItem('chat_custom_themes', JSON.stringify(newThemes));

    // Если удалена текущая тема, переключаемся на default
    if (currentTheme === themeName) {
      saveTheme('default');
    }
  }, [customThemes, currentTheme, saveTheme]);

  // Обновление настроек темы
  const updateThemeSettings = useCallback((settings) => {
    const newSettings = { ...themeSettings, ...settings };
    setThemeSettings(newSettings);
    localStorage.setItem('chat_theme_settings', JSON.stringify(newSettings));
  }, [themeSettings]);

  // CSS переменные для текущей темы
  const getThemeCSSVariables = useCallback(() => {
    const theme = getCurrentTheme();
    const spacing = {
      compact: '8px',
      comfortable: '12px',
      spacious: '16px'
    }[themeSettings.messageSpacing];

    const fontSizes = {
      small: '14px',
      medium: '16px',
      large: '18px'
    }[themeSettings.fontSize];

    return {
      '--chat-primary-color': theme.colors.primary,
      '--chat-secondary-color': theme.colors.secondary,
      '--chat-background': theme.colors.background,
      '--chat-surface': theme.colors.surface,
      '--chat-border': theme.colors.border,
      '--chat-text-primary': theme.colors.text.primary,
      '--chat-text-secondary': theme.colors.text.secondary,
      '--chat-text-tertiary': theme.colors.text.tertiary,
      '--chat-border-radius': theme.borderRadius,
      '--chat-font-family': theme.fontFamily,
      '--chat-message-spacing': spacing,
      '--chat-font-size': fontSizes,
      '--chat-animations-enabled': themeSettings.animations ? '1' : '0'
    };
  }, [getCurrentTheme, themeSettings]);

  // Применение CSS переменных
  useEffect(() => {
    const variables = getThemeCSSVariables();
    const root = document.documentElement;

    Object.entries(variables).forEach(([property, value]) => {
      root.style.setProperty(property, value);
    });
  }, [getThemeCSSVariables]);

  // Context value
  const contextValue = {
    // Current theme
    currentTheme,
    theme: getCurrentTheme(),
    themeSettings,

    // Available themes
    presetThemes: PRESET_THEMES,
    customThemes,

    // Methods
    setTheme: saveTheme,
    createCustomTheme,
    deleteCustomTheme,
    updateThemeSettings,
    getThemeCSSVariables,

    // Utilities
    isCustomTheme: (themeName) => !!customThemes[themeName],
    getAllThemes: () => ({
      ...PRESET_THEMES,
      ...customThemes
    })
  };

  return (
    <ChatThemeContext.Provider value={contextValue}>
      {children}
    </ChatThemeContext.Provider>
  );
}

// Hook для использования Chat Theme Context
export function useChatTheme() {
  const context = useContext(ChatThemeContext);
  if (!context) {
    throw new Error('useChatTheme must be used within a ChatThemeProvider');
  }
  return context;
}

// Hook для применения темы к компоненту
export function useThemeStyles() {
  const { theme, themeSettings } = useChatTheme();

  return {
    // Colors
    primaryColor: 'var(--chat-primary-color)',
    secondaryColor: 'var(--chat-secondary-color)',
    background: 'var(--chat-background)',
    surface: 'var(--chat-surface)',
    border: 'var(--chat-border)',
    textPrimary: 'var(--chat-text-primary)',
    textSecondary: 'var(--chat-text-secondary)',
    textTertiary: 'var(--chat-text-tertiary)',

    // Layout
    borderRadius: 'var(--chat-border-radius)',
    fontFamily: 'var(--chat-font-family)',
    messageSpacing: 'var(--chat-message-spacing)',
    fontSize: 'var(--chat-font-size)',

    // Settings
    animationsEnabled: themeSettings.animations,
    messageSpacing: themeSettings.messageSpacing,
    fontSize: themeSettings.fontSize,

    // Full theme object
    theme,
    settings: themeSettings
  };
}

export default ChatThemeContext;
