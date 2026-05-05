import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import TraceEventRow from '../../../src/features/chat/components/trace/TraceEventRow';

describe('TraceEventRow props contract', () => {
  it('renders title and detail for event prop', () => {
    render(
      <ChakraProvider>
        <TraceEventRow event={{ id: 'e1', title: 'Step title', detail: 'Step detail', kind: 'info', timestamp: '2026-04-22T10:00:00Z' }} eventIndex={1} />
      </ChakraProvider>
    );

    expect(screen.getByText('Step title')).toBeInTheDocument();
    expect(screen.getByText('Step detail')).toBeInTheDocument();
  });
});
