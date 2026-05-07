import React from 'react';
import { Box } from '@chakra-ui/react';
import { spacing } from '@theme/tokens';

export default function SectionContainer({ children, py = spacing['3xl'], px = spacing.lg, ...rest }) {
  return (
    <Box as="section" py={py} px={px} {...rest}>
      {children}
    </Box>
  );
}
