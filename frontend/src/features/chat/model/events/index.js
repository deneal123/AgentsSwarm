export const CHAT_EVENTS = Object.freeze({
  SEND_MESSAGE: 'send_message',
  RECEIVE_CHUNK: 'receive_chunk',
  RECONNECT: 'reconnect',
  JOB_PROGRESS: 'job_progress',
});

export const createSendMessageEvent = ({ threadId, message, metadata = {} }) => ({ type: CHAT_EVENTS.SEND_MESSAGE, payload: { threadId, message, metadata } });
export const createReceiveChunkEvent = ({ messageId, chunk, metadata = {} }) => ({ type: CHAT_EVENTS.RECEIVE_CHUNK, payload: { messageId, chunk, metadata } });
export const createReconnectEvent = ({ attempt = 1, reason = '' } = {}) => ({ type: CHAT_EVENTS.RECONNECT, payload: { attempt, reason } });
export const createJobProgressEvent = ({ jobId, progress = 0, status = 'running' }) => ({ type: CHAT_EVENTS.JOB_PROGRESS, payload: { jobId, progress, status } });
