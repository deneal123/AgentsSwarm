import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import VoiceRecorder from '@features/chat/components/VoiceRecorder';

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

describe('VoiceRecorder', () => {
  const mockOnRecordingComplete = jest.fn();

  it('renders record button initially', () => {
    render(
      <TestWrapper>
        <VoiceRecorder onRecordingComplete={mockOnRecordingComplete} />
      </TestWrapper>
    );

    // Should render some button (exact text may vary based on implementation)
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('accepts onRecordingComplete prop', () => {
    render(
      <TestWrapper>
        <VoiceRecorder onRecordingComplete={mockOnRecordingComplete} />
      </TestWrapper>
    );

    // Component renders without errors when prop is provided
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('renders with different maxDuration', () => {
    render(
      <TestWrapper>
        <VoiceRecorder onRecordingComplete={mockOnRecordingComplete} maxDuration={30} />
      </TestWrapper>
    );

    expect(screen.getByRole('button')).toBeInTheDocument();
  });
});