import { login, registerUser, logoutLocal } from '@/shared/api/auth';
import { createChatThread, sendChatMessage, getChatModels } from '@/shared/api/chat';
import { mapApiError } from '@/shared/api/dtoMappers';
import { request } from '@/shared/api/request';

jest.mock('@/shared/api/request', () => ({
  request: jest.fn(),
}));

describe('API adapters', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('login delegates to unified request client', async () => {
    request.mockResolvedValue({ token: 't' });
    const payload = { email: 'a@a.com', password: 'p' };

    await expect(login(payload)).resolves.toEqual({ token: 't' });
    expect(request).toHaveBeenCalledWith({ method: 'post', url: '/api/auth/v1/login', data: payload });
  });

  it('registerUser delegates payload to unified request client', async () => {
    const payload = { email: 'user@test.dev', password: 'pass' };
    request.mockResolvedValue({ user_id: 'u1' });

    await expect(registerUser(payload)).resolves.toEqual({ user_id: 'u1' });
    expect(request).toHaveBeenCalledWith({ method: 'post', url: '/api/auth/v1/register', data: payload });
  });

  it('createChatThread sends optional user id', async () => {
    request.mockResolvedValue({ thread_id: 'th_1' });

    await createChatThread('user-1');

    expect(request).toHaveBeenCalledWith({ method: 'post', url: '/api/chats/', data: { user_id: 'user-1' } });
  });

  it('sendChatMessage maps options to transport payload', async () => {
    request.mockResolvedValue({ reply: 'ok' });

    await sendChatMessage('th_1', ' hello ', 'user-1', 'gpt', 'text', {
      webSearch: true,
      deepResearch: true,
      fileContext: 'context',
      fileIds: ['f1'],
      routeOverride: 'analysis',
    });

    expect(request).toHaveBeenCalledWith({
      method: 'post',
      url: '/api/chats/th_1/message',
      data: {
        text: 'hello',
        user_id: 'user-1',
        model: 'gpt',
        input_type: 'text',
        web_search: true,
        deep_research: true,
        file_context: 'context',
        file_ids: ['f1'],
        route_override: 'analysis',
      },
    });
  });

  it('getChatModels returns empty array fallback', async () => {
    request.mockResolvedValue([]);
    await expect(getChatModels()).resolves.toEqual([]);
  });

  it('mapApiError returns typed domain error', () => {
    const error = { response: { status: 401, data: { code: 'UNAUTHORIZED', detail: 'invalid credentials' } } };
    expect(mapApiError(error)).toMatchObject({
      type: 'DomainError',
      status: 401,
      code: 'UNAUTHORIZED',
      isRetryable: false,
      isCanceled: false,
    });
  });

  it('logoutLocal clears auth cookie', () => {
    logoutLocal();
    expect(document.cookie).toContain('auth_token=;');
  });
});
