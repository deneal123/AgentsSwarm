import React from "react";
import PropTypes from "prop-types";
import { Badge } from "@chakra-ui/react";
import { colors, borderRadius, gradients } from "@theme/tokens";

function FeatureBadge({ children, ...props }) {
  return (
    <Badge
      bg="rgba(139, 92, 246, 0.1)"
      color={colors.text.primary}
      borderRadius={borderRadius.full}
      px={5}
      py={2}
      mb={3}
      fontSize="12px"
      fontWeight={500}
      textTransform="uppercase"
      letterSpacing="wider"
      border="1px solid rgba(139, 92, 246, 0.3)"
      position="relative"
      overflow="hidden"
      boxShadow={`0 0 20px rgba(139, 92, 246, 0.15), inset 0 0 20px rgba(139, 92, 246, 0.05)`}
      _before={{
        content: '""',
        position: "absolute",
        inset: 0,
        background: gradients.aurora,
        opacity: 0.3,
        filter: "blur(8px)",
      }}
      {...props}
    >
      {children}
    </Badge>
  );
}

FeatureBadge.propTypes = {
  children: PropTypes.node.isRequired,
};

export default FeatureBadge;
