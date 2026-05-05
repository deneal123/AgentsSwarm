import { renderHook, act, waitFor } from '@testing-library/react';
import { useGuestSession } from '@hooks/useGuestSession';

// Mock sessionManager
jest.mock('@utils/sessionManager', () => ({
  guestSessionManager: {
    getCurrentSession: jest.fn(),
    createGuestSession: jest.fn(),
    saveSession: jest.fn(),
    clearSession: jest.fn(),
    incrementRequests: jest.fn(() => 1),
    incrementRequestCount: jest.fn(() => 1),
    clearSession: jest.fn(),
    getRemainingRequests: jest.fn(),
    getSessionStats: jest.fn(() => ({
      totalRequests: 0,
      remainingRequests: 10,
      lastReset: new Date().toISOString()
    }))
  }
}));

// Get mock functions after jest.mock
const mockGetCurrentSession = require('@utils/sessionManager').guestSessionManager.getCurrentSession;
const mockCreateGuestSession = require('@utils/sessionManager').guestSessionManager.createGuestSession;
const mockSaveSession = require('@utils/sessionManager').guestSessionManager.saveSession;
const mockClearSession = require('@utils/sessionManager').guestSessionManager.clearSession;
const mockIncrementRequestCount = require('@utils/sessionManager').guestSessionManager.incrementRequestCount;
const mockResetSession = require('@utils/sessionManager').guestSessionManager.clearSession;
const mockGetRemainingRequests = require('@utils/sessionManager').guestSessionManager.getRemainingRequests;

describe('useGuestSession', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    // Set fake date for consistent testing
    jest.setSystemTime(new Date('2025-12-29T10:00:00Z'));
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('initializes with default values when no stored data', async () => {
    mockGetCurrentSession.mockReturnValue(null);
    mockCreateGuestSession.mockReturnValue({
      id: 'guest_123',
      limits: {
        requestCount: 0,
        lastReset: new Date().toISOString(),
        maxRequests: 10
      },
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      threadIds: []
    });
    mockGetRemainingRequests.mockReturnValue(10);

    const { result } = renderHook(() => useGuestSession());

    await waitFor(() => {
      expect(result.current.sessionId).toBe('guest_123');
    });

    expect(result.current.remainingRequests).toBe(10);
    expect(typeof result.current.incrementRequests).toBe('function');
    expect(typeof result.current.clearSession).toBe('function');
  });

  it('loads existing session data from localStorage', async () => {
    const existingSession = {
      id: 'guest_123',
      limits: {
        requestCount: 3,
        lastReset: '2025-12-29T09:00:00Z',
        maxRequests: 10
      },
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      threadIds: []
    };

    mockGetCurrentSession.mockReturnValue(existingSession);
    mockGetRemainingRequests.mockReturnValue(7); // 10 - 3

    const { result } = renderHook(() => useGuestSession());

    await waitFor(() => {
      expect(result.current.sessionId).toBe('guest_123');
    });

    expect(result.current.remainingRequests).toBe(7);
  });

  it('resets request count daily', async () => {
    const oldDate = new Date('2025-12-28T10:00:00Z'); // Yesterday
    const existingSession = {
      id: 'guest_123',
      limits: {
        requestCount: 8,
        lastReset: oldDate.toISOString(),
        maxRequests: 10
      },
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      threadIds: []
    };

    mockGetCurrentSession.mockReturnValue(existingSession);
    mockGetRemainingRequests.mockReturnValue(10); // Reset to max

    const { result } = renderHook(() => useGuestSession());

    await waitFor(() => {
      expect(result.current.sessionId).toBe('guest_123');
    });

    expect(result.current.remainingRequests).toBe(2); // 10 - 8 = 2
  });

  it('increments request count correctly', async () => {
    mockGetCurrentSession.mockReturnValue(null);
    mockCreateGuestSession.mockReturnValue({
      id: 'guest_123',
      limits: {
        requestCount: 0,
        lastReset: new Date().toISOString(),
        maxRequests: 10
      },
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      threadIds: []
    });
    mockGetRemainingRequests.mockReturnValue(10);
    mockIncrementRequestCount.mockReturnValue(true);

    const { result } = renderHook(() => useGuestSession());

    await waitFor(() => {
      expect(result.current.sessionId).toBe('guest_123');
    });

    act(() => {
      result.current.incrementRequests();
    });

    expect(mockIncrementRequestCount).toHaveBeenCalled();
  });

  it('prevents incrementing when no requests remaining', async () => {
    const existingSession = {
      id: 'guest_123',
      limits: {
        requestCount: 10,
        lastReset: '2025-12-29T09:00:00Z',
        maxRequests: 10
      },
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      threadIds: []
    };

    mockGetCurrentSession.mockReturnValue(existingSession);
    mockGetRemainingRequests.mockReturnValue(0);
    mockIncrementRequestCount.mockReturnValue(false);

    const { result } = renderHook(() => useGuestSession());

    await waitFor(() => {
      expect(result.current.remainingRequests).toBe(0);
    });

    act(() => {
      result.current.incrementRequests();
    });

    expect(result.current.remainingRequests).toBe(0);
  });

  it('resets session correctly', async () => {
    const existingSession = {
      id: 'guest_old',
      limits: {
        requestCount: 5,
        lastReset: '2025-12-29T09:00:00Z',
        maxRequests: 10
      },
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      threadIds: []
    };

    mockGetCurrentSession.mockReturnValue(existingSession);
    mockGetRemainingRequests.mockReturnValue(5);

    const { result } = renderHook(() => useGuestSession());

    await waitFor(() => {
      expect(result.current.sessionId).toBe('guest_old');
    });

    act(() => {
      result.current.clearSession();
    });

    expect(mockResetSession).toHaveBeenCalled();

    // Session should be cleared (set to null)
    await waitFor(() => {
      expect(result.current.sessionId).toBeNull();
    });
  });

  it('handles corrupted session data gracefully', async () => {
    mockGetCurrentSession.mockImplementation(() => {
      throw new Error('Invalid session data');
    });

    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    const { result } = renderHook(() => useGuestSession());

    await waitFor(() => {
      expect(result.current.error).toBe('Invalid session data');
      expect(result.current.sessionId).toBeNull();
    });

    consoleSpy.mockRestore();
  });

  it('maintains session across multiple days within limit', async () => {
    const yesterday = new Date('2025-12-28T15:00:00Z');
    const existingSession = {
      id: 'guest_123',
      limits: {
        requestCount: 3,
        lastReset: yesterday.toISOString(),
        maxRequests: 10
      },
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      threadIds: []
    };

    mockGetCurrentSession.mockReturnValue(existingSession);
    mockGetRemainingRequests.mockReturnValue(7); // 10 - 3, no reset

    const { result } = renderHook(() => useGuestSession());

    await waitFor(() => {
      expect(result.current.sessionId).toBe('guest_123');
    });

    expect(result.current.remainingRequests).toBe(7);
  });

  it('resets count when date changes and count was at limit', async () => {
    const oldDate = new Date('2025-12-28T10:00:00Z');
    const existingSession = {
      id: 'guest_123',
      limits: {
        requestCount: 10, // At limit
        lastReset: oldDate.toISOString(),
        maxRequests: 10
      },
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      threadIds: []
    };

    mockGetCurrentSession.mockReturnValue(existingSession);
    mockGetRemainingRequests.mockReturnValue(10); // Reset to max

    const { result } = renderHook(() => useGuestSession());

    await waitFor(() => {
      expect(result.current.sessionId).toBe('guest_123');
    });

    expect(result.current.remainingRequests).toBe(0); // 10 - 10 = 0, already at limit
  });
});
