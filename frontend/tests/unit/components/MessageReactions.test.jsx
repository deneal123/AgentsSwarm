import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import MessageReactions from '@features/chat/components/MessageReactions';

// Mock analytics only
jest.mock('@features/analytics/context/AnalyticsContext', () => ({
  useAnalytics: () => ({
    trackEvent: jest.fn(),
  }),
}));

const TestWrapper = ({ children }) => (
  <ChakraProvider>
    {children}
  </ChakraProvider>
);

describe('MessageReactions', () => {
  const mockOnAddReaction = jest.fn();
  const mockOnRemoveReaction = jest.fn();

  const defaultProps = {
    messageId: 'msg_123',
    reactions: [],
    onAddReaction: mockOnAddReaction,
    onRemoveReaction: mockOnRemoveReaction,
    currentUserId: 'user_456',
  };

  it('renders add reaction button when no reactions exist', () => {
    render(
      <TestWrapper>
        <MessageReactions {...defaultProps} />
      </TestWrapper>
    );

    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('renders with reactions data', () => {
    const reactionsWithData = [
      { id: '1', emoji: '👍', userId: 'user_456', messageId: 'msg_123' },
      { id: '2', emoji: '❤️', userId: 'user_789', messageId: 'msg_123' },
    ];

    render(
      <TestWrapper>
        <MessageReactions
          {...defaultProps}
          reactions={reactionsWithData}
        />
      </TestWrapper>
    );

    // Should render buttons for reactions
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('accepts required props', () => {
    render(
      <TestWrapper>
        <MessageReactions {...defaultProps} />
      </TestWrapper>
    );

    // Component renders with all required props
    expect(screen.getByRole('button')).toBeInTheDocument();
  });
});