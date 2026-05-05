import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChakraProvider } from '@chakra-ui/react';
import { BrowserRouter } from 'react-router-dom';
import SearchInterface from '@features/home/components/SearchInterface';

// Mock minimal dependencies
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
  AnalyticsProvider: ({ children }) => <div data-testid="analytics-provider">{children}</div>,
  useAnalytics: () => ({
    trackEvent: jest.fn(),
  }),
}));

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
}));

// Import after mocking
import { AnalyticsProvider } from '@features/analytics/context/AnalyticsContext';

const TestWrapper = ({ children }) => (
  <BrowserRouter>
    <ChakraProvider>
      <AnalyticsProvider>
        {children}
      </AnalyticsProvider>
    </ChakraProvider>
  </BrowserRouter>
);

describe('SearchInterface', () => {
  it('renders search input and button', () => {
    render(
      <TestWrapper>
        <SearchInterface />
      </TestWrapper>
    );

    expect(screen.getByPlaceholderText(/Спросите/i)).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('shows remaining requests counter', () => {
    render(
      <TestWrapper>
        <SearchInterface />
      </TestWrapper>
    );

    expect(screen.getByText(/Осталось запросов/)).toBeInTheDocument();
  });

  it('updates input value when typing', async () => {
    render(
      <TestWrapper>
        <SearchInterface />
      </TestWrapper>
    );

    const input = screen.getByPlaceholderText(/Спросите/i);
    await userEvent.type(input, 'Test query');

    expect(input.value).toBe('Test query');
  });

  it('handles form submission', async () => {
    render(
      <TestWrapper>
        <SearchInterface />
      </TestWrapper>
    );

    const input = screen.getByPlaceholderText(/Спросите/i);
    const button = screen.getByRole('button');

    await userEvent.type(input, 'Test message');
    await userEvent.click(button);

    // Component should handle submission without errors
    expect(input.value).toBe('Test message');
  });
});