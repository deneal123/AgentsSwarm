import { CHAT_UI_SETTINGS_STORAGE_KEY } from '../constants/localStorageKeys';

export const readChatUiSettings = () => {
  if (typeof window === 'undefined') {
    return { ok: false, settings: null };
  }

  try {
    const raw = window.localStorage.getItem(CHAT_UI_SETTINGS_STORAGE_KEY);
    return {
      ok: true,
      settings: raw ? JSON.parse(raw) : null,
    };
  } catch {
    return { ok: false, settings: null };
  }
};

export const writeChatUiSettings = (settings) => {
  if (typeof window === 'undefined') {
    return { ok: false };
  }

  try {
    window.localStorage.setItem(CHAT_UI_SETTINGS_STORAGE_KEY, JSON.stringify(settings));
    return { ok: true };
  } catch {
    return { ok: false };
  }
};
