import client from '@API/client';
import { login, registerUser, logoutLocal } from '@API/auth';
import { createChatThread, sendChatMessage, getChatModels } from '@API/chat';

jest.mock('@API/client', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
    get: jest.fn(),
    delete: jest.fn(),
    patch: jest.fn(),
    interceptors: { response: { use: jest.fn() } },
  },
}));

describe('API adapters', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('login returns response data and calls transport with endpoint', async () => {
    client.post.mockResolvedValue({ data: { token: 't' } });
    const payload = { email: 'a@a.com', password: 'p' };

    await expect(login(payload)).resolves.toEqual({ token: 't' });
    expect(client.post).toHaveBeenCalledWith('/api/auth/v1/login', payload);
  });

  it('registerUser delegates payload to transport layer', async () => {
    const payload = { email: 'user@test.dev', password: 'pass' };
    client.post.mockResolvedValue({ data: { user_id: 'u1' } });

    await expect(registerUser(payload)).resolves.toEqual({ user_id: 'u1' });
    expect(client.post).toHaveBeenCalledWith('/api/auth/v1/register', payload);
  });

  it('createChatThread sends optional user id', async () => {
    client.post.mockResolvedValue({ data: { thread_id: 'th_1' } });

    await createChatThread('user-1');

    expect(client.post).toHaveBeenCalledWith('/api/chats/', { user_id: 'user-1' });
  });

  it('sendChatMessage maps options to transport payload', async () => {
    client.post.mockResolvedValue({ data: { reply: 'ok' } });

    await sendChatMessage('th_1', ' hello ', 'user-1', 'gpt', 'text', {
      webSearch: true,
      deepResearch: true,
      fileContext: 'context',
      fileIds: ['f1'],
      routeOverride: 'analysis',
    });

    expect(client.post).toHaveBeenCalledWith('/api/chats/th_1/message', {
      text: 'hello',
      user_id: 'user-1',
      model: 'gpt',
      input_type: 'text',
      web_search: true,
      deep_research: true,
      file_context: 'context',
      file_ids: ['f1'],
      route_override: 'analysis',
    });
  });

  it('getChatModels returns empty array fallback', async () => {
    client.get.mockResolvedValue({ data: null });
    await expect(getChatModels()).resolves.toEqual([]);
  });

  it('logoutLocal clears auth cookie', () => {
    logoutLocal();
    expect(document.cookie).toContain('auth_token=;');
  });
});
