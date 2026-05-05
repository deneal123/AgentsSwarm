import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import { BrowserRouter } from 'react-router-dom';
import SearchInterface from '@features/home/components/SearchInterface';

// Simple mocks
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

describe('Chat Flow Integration', () => {
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
});