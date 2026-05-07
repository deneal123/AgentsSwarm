import React from 'react';
import { VStack } from '@chakra-ui/react';
import { spacing } from '@theme/tokens';

export default function PanelStack({ children, spacingY = spacing.lg, ...rest }) {
  return (
    <VStack align="stretch" spacing={spacingY} {...rest}>
      {children}
    </VStack>
  );
}
