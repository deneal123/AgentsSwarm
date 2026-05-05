import React, { memo } from "react";
import { Text, VStack } from "@chakra-ui/react";

const DEFAULT_TITLE = "Здесь пока пусто";
const DEFAULT_DESCRIPTION = "Попробуйте изменить фильтры или загрузить данные.";

const EmptyState = memo(function EmptyState({
  title = DEFAULT_TITLE,
  description = DEFAULT_DESCRIPTION,
}) {
  return (
    <VStack
      spacing={2}
      py={10}
      px={4}
      borderWidth="1px"
      borderRadius="lg"
      borderStyle="dashed"
      borderColor="borderSubtle"
    >
      <Text fontWeight="semibold" fontSize="lg">
        {title}
      </Text>
      {description && (
        <Text color="text.muted" textAlign="center">
          {description}
        </Text>
      )}
    </VStack>
  );
});

export default EmptyState;
