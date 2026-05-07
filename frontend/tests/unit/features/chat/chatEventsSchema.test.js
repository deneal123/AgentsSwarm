import { validateChatEvent } from '@features/chat/schema/chatEventsSchema';

describe('chatEventsSchema', () => {
  it('validates job_created contract', () => {
    const result = validateChatEvent({
      type: 'job_created',
      job_id: 'job-1',
      thread_id: 'thread-1',
      metadata: { source: 'ws' },
      data: { created_at: '2026-01-01T00:00:00Z' },
    });

    expect(result).toEqual({ isValid: true, error: null, eventType: 'job_created' });
  });

  it('validates stream_chunk contract', () => {
    const result = validateChatEvent({
      type: 'stream_chunk',
      job_id: 'job-1',
      thread_id: 'thread-1',
      metadata: {},
      data: 'hello',
    });

    expect(result.isValid).toBe(true);
  });

  it('rejects malformed error contract', () => {
    const result = validateChatEvent({
      type: 'error',
      job_id: 'job-1',
      thread_id: 'thread-1',
      data: { code: 'FAILED' },
    });

    expect(result.isValid).toBe(false);
    expect(result.error).toContain('data.message');
  });

  it('rejects malformed complete contract', () => {
    const result = validateChatEvent({
      type: 'complete',
      job_id: '',
      thread_id: 'thread-1',
      data: {},
    });

    expect(result.isValid).toBe(false);
    expect(result.error).toContain('job_id');
  });

  it('passes through unknown events without strict validation', () => {
    const result = validateChatEvent({ type: 'heartbeat' });

    expect(result).toEqual({ isValid: true, error: null, eventType: 'heartbeat' });
  });
});
