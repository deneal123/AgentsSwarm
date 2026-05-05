import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import { BrowserRouter } from 'react-router-dom';
import SearchInterface from '@features/home/components/SearchInterface';

// Mock analytics
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

describe('Analytics Integration', () => {
  it('renders components with analytics provider', () => {
    render(
      <TestWrapper>
        <SearchInterface />
      </TestWrapper>
    );

    expect(screen.getByPlaceholderText(/запрос/i)).toBeInTheDocument();
    expect(screen.getByText('Осталось запросов: 7')).toBeInTheDocument();
  });
});