import React from 'react';
import { render } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import ChatPageLayout from '@features/chat/page/ChatPageLayout';

describe('ChatPageLayout smoke', () => {
  it('renders layout snapshot', () => {
    const { asFragment } = render(
      <ChakraProvider>
        <ChatPageLayout>content</ChatPageLayout>
      </ChakraProvider>,
    );
    expect(asFragment()).toMatchSnapshot();
  });
});
