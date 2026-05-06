import { useEffect, useState } from 'react';
import { readChatUiSettings, writeChatUiSettings } from '../adapters/chatUiSettingsStorage';
import { defaultChatUiSettings } from '../constants/chatUiSettings';
import { normalizeChatUiSettings } from '../schema/chatUiSettingsSchema';

export const useChatUiSettings = ({ initialWebSearch = false, initialDeepResearch = false } = {}) => {
  const [isStorageWriteFailed, setIsStorageWriteFailed] = useState(false);
  const [settings, setSettings] = useState(() => {
    const { settings: storedSettings } = readChatUiSettings();
    const persisted = normalizeChatUiSettings(storedSettings);

    return {
      ...persisted,
      webSearchEnabled: initialWebSearch || persisted.webSearchEnabled,
      deepResearchEnabled: initialDeepResearch || persisted.deepResearchEnabled,
    };
  });

  useEffect(() => {
    const { ok } = writeChatUiSettings(settings);
    setIsStorageWriteFailed(!ok);
  }, [settings]);

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
