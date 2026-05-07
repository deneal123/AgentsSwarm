import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChakraProvider } from '@chakra-ui/react';
import { BrowserRouter } from 'react-router-dom';
import SearchInterface from '@features/home/components/SearchInterface';
import { useChatTransport } from '@features/chat/hooks/useChatTransport';

jest.mock('@features/chat/model/useWebSocketChat', () => ({
  useWebSocketChat: jest.fn(),
}));

const { useWebSocketChat } = require('@features/chat/model/useWebSocketChat');

jest.mock('@features/chat/context/ChatContext', () => ({
  useChat: () => ({
    sendMessage: jest.fn(),
    isConnected: true,
  }),
}));

jest.mock('@hooks/useGuestSession', () => ({
  useGuestSession: () => ({
    remainingRequests: 7,
    shouldShowLimitWarning: jest.fn(() => false),
    incrementRequests: jest.fn(),
  }),
}));

jest.mock('@features/analytics/context/AnalyticsContext', () => ({
  AnalyticsProvider: ({ children }) => <div>{children}</div>,
  useAnalytics: () => ({
    trackEvent: jest.fn(),
  }),
}));

const TestWrapper = ({ children }) => (
  <BrowserRouter>
    <ChakraProvider>
      {children}
    </ChakraProvider>
  </BrowserRouter>
);

function TransportProbe({ onSnapshot }) {
  const transport = useChatTransport({ threadId: 'integration-thread', callbacks: {}, isAuthenticated: true });
  React.useEffect(() => {
    onSnapshot(transport);
  }, [transport, onSnapshot]);
  return <div data-testid="transport-state">{transport.connectionState}</div>;
}

describe('Chat Flow Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders search interface with counter', () => {
    render(
      <TestWrapper>
        <SearchInterface />
      </TestWrapper>
    );

    expect(screen.getByPlaceholderText(/Спросите/i)).toBeInTheDocument();
    expect(screen.getByText(/Осталось запросов/)).toBeInTheDocument();
  });

  it('allows typing in search input', async () => {
    render(
      <TestWrapper>
        <SearchInterface />
      </TestWrapper>
    );

    const input = screen.getByPlaceholderText(/Спросите/i);
    await userEvent.type(input, 'Test message');

    expect(input.value).toBe('Test message');
  });

  it('shows send button', () => {
    render(
      <TestWrapper>
        <SearchInterface />
      </TestWrapper>
    );

    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('supports reconnect then partial stream then backend error sequence', async () => {
    const sendMessage = jest.fn();
    const cancelJob = jest.fn();
    const snapshots = [];

    useWebSocketChat
      .mockReturnValueOnce({
        isConnected: false,
        connectionState: 'reconnecting',
        currentJob: { id: 'job-1', partial: 'Hel' },
        agentStatus: 'reconnecting',
        sendMessage,
        cancelJob,
      })
      .mockReturnValueOnce({
        isConnected: true,
        connectionState: 'connected',
        currentJob: { id: 'job-1', partial: 'Hello, wor' },
        agentStatus: 'streaming',
        sendMessage,
        cancelJob,
      })
      .mockReturnValueOnce({
        isConnected: false,
        connectionState: 'error',
        currentJob: null,
        agentStatus: 'failed',
        sendMessage,
        cancelJob,
      });

    const onSnapshot = (snapshot) => snapshots.push(snapshot);
    const { rerender } = render(<TransportProbe onSnapshot={onSnapshot} />);

    rerender(<TransportProbe onSnapshot={onSnapshot} />);
    rerender(<TransportProbe onSnapshot={onSnapshot} />);

    await waitFor(() => {
      expect(snapshots.length).toBeGreaterThanOrEqual(3);
    });

    expect(snapshots[0].connectionState).toBe('reconnecting');
    expect(snapshots[0].useWebSocket).toBe(false);

    expect(snapshots[1].connectionState).toBe('connected');
    expect(snapshots[1].currentJob.partial).toBe('Hello, wor');
    expect(snapshots[1].useWebSocket).toBe(true);

    expect(snapshots[2].connectionState).toBe('error');
    expect(snapshots[2].currentJob).toBeNull();
    expect(snapshots[2].useWebSocket).toBe(false);
  });
});
