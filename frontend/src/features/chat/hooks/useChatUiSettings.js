import { useEffect, useState } from 'react';
import { readChatUiSettings, writeChatUiSettings } from '../adapters/chatUiSettingsStorage';
import { defaultChatUiSettings } from '../constants/chatUiSettings';
import { CHAT_UI_SETTINGS_STORAGE_KEY } from '../constants/localStorageKeys';
import { normalizeChatUiSettings } from '../schema/chatUiSettingsSchema';

const getNormalizedSettings = () => {
  const { settings: storedSettings } = readChatUiSettings();
  return normalizeChatUiSettings(storedSettings);
};

const applyInitialSettingsPriority = (settings, { initialWebSearch, initialDeepResearch }) => ({
  ...settings,
  webSearchEnabled: initialWebSearch || settings.webSearchEnabled,
  deepResearchEnabled: initialDeepResearch || settings.deepResearchEnabled,
});

export const useChatUiSettings = ({ initialWebSearch = false, initialDeepResearch = false } = {}) => {
  const [isStorageWriteFailed, setIsStorageWriteFailed] = useState(false);
  const [settings, setSettings] = useState(() =>
    applyInitialSettingsPriority(getNormalizedSettings(), { initialWebSearch, initialDeepResearch }),
  );

  useEffect(() => {
    const { ok } = writeChatUiSettings(settings);
    setIsStorageWriteFailed(!ok);
  }, [settings]);

  useEffect(() => {
    const handleStorage = (event) => {
      if (event.key !== CHAT_UI_SETTINGS_STORAGE_KEY) {
        return;
      }

      setSettings(getNormalizedSettings());
    };

    window.addEventListener('storage', handleStorage);

    return () => {
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  const resetUiSettings = () => {
    setSettings(defaultChatUiSettings);
  };

  return {
    settings,
    setSettings,
    resetUiSettings,
    isStorageWriteFailed,
  };
};
