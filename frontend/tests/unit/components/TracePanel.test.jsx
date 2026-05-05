import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import TracePanel from '../../../src/features/chat/components/trace/TracePanel';

describe('TracePanel props contract', () => {
  it('renders all provided sessions', () => {
    render(
      <ChakraProvider>
        <TracePanel
          sessions={[
            { id: 's1', title: 'A', status: 'running', events: [] },
            { id: 's2', title: 'B', status: 'done', events: [] },
          ]}
          expandedMap={{}}
          isCompactTrace={false}
          onToggleExpanded={() => {}}
        />
      </ChakraProvider>
    );

    expect(screen.getAllByText('Подготовка ответа')).toHaveLength(2);
  });
});
