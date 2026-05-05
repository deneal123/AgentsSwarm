import { CHAT_UI_SETTINGS_STORAGE_KEY } from '../constants/localStorageKeys';

export const defaultChatUiSettings = {
  showTracePanel: true,
  webSearchEnabled: false,
  deepResearchEnabled: false,
};

const toBoolean = (value, fallback) => (typeof value === 'boolean' ? value : fallback);

export const normalizeChatUiSettings = (raw) => {
  const source = raw && typeof raw === 'object' ? raw : {};
  return {
    showTracePanel: toBoolean(source.showTracePanel, defaultChatUiSettings.showTracePanel),
    webSearchEnabled: toBoolean(source.webSearchEnabled, defaultChatUiSettings.webSearchEnabled),
    deepResearchEnabled: toBoolean(source.deepResearchEnabled, defaultChatUiSettings.deepResearchEnabled),
  };
};

export const loadChatUiSettings = () => {
  if (typeof window === 'undefined') {
    return defaultChatUiSettings;
  }
  try {
    const raw = window.localStorage.getItem(CHAT_UI_SETTINGS_STORAGE_KEY);
    if (!raw) {
      return defaultChatUiSettings;
    }
    return normalizeChatUiSettings(JSON.parse(raw));
  } catch {
    return defaultChatUiSettings;
  }
};

export const saveChatUiSettings = (settings) => {
  if (typeof window === 'undefined') {
    return;
  }
  const normalized = normalizeChatUiSettings(settings);
  window.localStorage.setItem(CHAT_UI_SETTINGS_STORAGE_KEY, JSON.stringify(normalized));
};
