import { useEffect, useState } from 'react';
import { readChatUiSettings, writeChatUiSettings } from '../adapters/chatUiSettingsStorage';
import { defaultChatUiSettings } from '../constants/chatUiSettings';
import { normalizeChatUiSettings } from '../schema/chatUiSettingsSchema';

export const useChatUiSettings = ({ initialWebSearch = false, initialDeepResearch = false } = {}) => {
  const [settings, setSettings] = useState(() => {
    const persisted = normalizeChatUiSettings(readChatUiSettings());
    return {
      ...persisted,
      webSearchEnabled: initialWebSearch || persisted.webSearchEnabled,
      deepResearchEnabled: initialDeepResearch || persisted.deepResearchEnabled,
    };
  });

  useEffect(() => {
    writeChatUiSettings(settings);
  }, [settings]);

  const resetUiSettings = () => {
    setSettings(defaultChatUiSettings);
  };

  return {
    settings,
    setSettings,
    resetUiSettings,
  };
};
