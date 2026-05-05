import React, { memo } from "react";
import { Center, Spinner, Text, VStack } from "@chakra-ui/react";

const LoadingState = memo(function LoadingState({ label = "Loading..." }) {
  return (
    <Center py={10} w="full">
      <VStack spacing={3}>
        <Spinner size="lg" />
        <Text color="text.muted">{label}</Text>
      </VStack>
    </Center>
  );
});

export default LoadingState;
