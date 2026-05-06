import { CHAT_UI_SETTINGS_STORAGE_KEY } from '../constants/localStorageKeys';

export const readChatUiSettings = () => {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(CHAT_UI_SETTINGS_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

export const writeChatUiSettings = (settings) => {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(CHAT_UI_SETTINGS_STORAGE_KEY, JSON.stringify(settings));
};
