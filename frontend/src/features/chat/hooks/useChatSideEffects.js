import { useCallback, useEffect, useMemo } from 'react';
import { uploadChatFile } from '@API/chat';
import { useChatWebSocketModel } from '../model/useChatWebSocketModel';

export const useChatSideEffects = ({ threadId, sessionState, messagesState, uiState }) => {
  const wsCallbacks = useMemo(() => ({
    onMessage: messagesState.actions.addMessage,
    onJobUpdate: (jobData) => {
      if (jobData.type === 'job_created') {
        messagesState.actions.setCurrentJob({
          id: jobData.job_id,
          celeryTaskId: jobData.celery_task_id,
          status: 'processing',
          progress: 0,
          type: 'unknown',
        });
      }
    },
    onComplete: () => messagesState.actions.setCurrentJob(null),
    onError: (error) => uiState.actions.setError(error?.message || 'WebSocket error'),
    onConnect: () => uiState.actions.setConnectionState('connected'),
    onDisconnect: () => uiState.actions.setConnectionState('disconnected'),
  }), [messagesState.actions, uiState.actions]);

  const { isConnected, sendMessage: wsSendMessage } = useChatWebSocketModel({ threadId, callbacks: wsCallbacks, isAuthenticated: false });

  useEffect(() => {
    uiState.actions.setConnectionState(isConnected ? 'connected' : 'disconnected');
  }, [isConnected, uiState.actions]);

  const sendMessage = useCallback(async (content, attachments = []) => {
    if (!content.trim() && attachments.length === 0) return;
    uiState.actions.setLoading(true);
    uiState.actions.clearError();
    const optimisticMessage = { id: `temp_${Date.now()}`, type: 'user', content: content.trim(), timestamp: new Date().toISOString(), attachments, status: 'sending' };
    try {
      messagesState.actions.addMessage(optimisticMessage);
      sessionState.actions.clearAttachments();
      wsSendMessage(content);
      messagesState.actions.updateMessage(optimisticMessage.id, { status: 'sent' });
    } catch (error) {
      messagesState.actions.updateMessage(optimisticMessage.id, { status: 'failed', error: error.message });
      uiState.actions.setError(error.message);
    } finally {
      uiState.actions.setLoading(false);
    }
  }, [messagesState.actions, sessionState.actions, uiState.actions, wsSendMessage]);

  const uploadFile = useCallback(async (file) => {
    uiState.actions.setLoading(true);
    try {
      const result = await uploadChatFile(threadId, file);
      sessionState.actions.addAttachment({ id: result.file_id, name: file.name, type: file.type, size: file.size, url: result.download_url, uploaded: true });
    } catch {
      uiState.actions.setError('Failed to upload file');
    } finally {
      uiState.actions.setLoading(false);
    }
  }, [threadId, sessionState.actions, uiState.actions]);

  return { sendMessage, uploadFile };
};
