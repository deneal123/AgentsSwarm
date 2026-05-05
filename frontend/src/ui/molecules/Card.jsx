import React, { memo } from "react";
import { Box } from "@chakra-ui/react";

const Card = memo(function Card({ children, p = 6, ...rest }) {
  return (
    <Box
      bg="surface"
      border="1px solid"
      borderColor="borderSubtle"
      borderRadius="card"
      boxShadow="subtle"
      p={p}
      {...rest}
    >
      {children}
    </Box>
  );
});

export default Card;
