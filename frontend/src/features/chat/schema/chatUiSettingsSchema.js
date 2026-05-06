import { defaultChatUiSettings } from '../constants/chatUiSettings';

const toBoolean = (value, fallback) => (typeof value === 'boolean' ? value : fallback);

export const normalizeChatUiSettings = (raw) => {
  const source = raw && typeof raw === 'object' ? raw : {};
  return {
    showTracePanel: toBoolean(source.showTracePanel, defaultChatUiSettings.showTracePanel),
    webSearchEnabled: toBoolean(source.webSearchEnabled, defaultChatUiSettings.webSearchEnabled),
    deepResearchEnabled: toBoolean(source.deepResearchEnabled, defaultChatUiSettings.deepResearchEnabled),
  };
};
