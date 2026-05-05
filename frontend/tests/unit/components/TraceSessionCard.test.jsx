import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChakraProvider } from '@chakra-ui/react';
import TraceSessionCard from '../../../src/features/chat/components/trace/TraceSessionCard';

describe('TraceSessionCard props contract', () => {
  it('calls onToggleExpanded when accordion is toggled', async () => {
    const onToggleExpanded = jest.fn();
    render(
      <ChakraProvider>
        <TraceSessionCard
          session={{ id: 's1', title: 'Query', status: 'running', events: [] }}
          isCompactTrace={false}
          isExpanded={true}
          onToggleExpanded={onToggleExpanded}
        />
      </ChakraProvider>
    );

    await userEvent.click(screen.getByText('Подготовка ответа'));
    expect(onToggleExpanded).toHaveBeenCalled();
  });
});
