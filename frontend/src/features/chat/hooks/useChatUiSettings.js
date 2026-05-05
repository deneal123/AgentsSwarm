import { useEffect, useState } from 'react';
import {
  defaultChatUiSettings,
  loadChatUiSettings,
  saveChatUiSettings,
} from '../adapters/chatUiSettingsStorage';

export const useChatUiSettings = ({ initialWebSearch = false, initialDeepResearch = false } = {}) => {
  const [settings, setSettings] = useState(() => {
    const persisted = loadChatUiSettings();
    return {
      ...persisted,
      webSearchEnabled: initialWebSearch || persisted.webSearchEnabled,
      deepResearchEnabled: initialDeepResearch || persisted.deepResearchEnabled,
    };
  });

  useEffect(() => {
    saveChatUiSettings(settings);
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
