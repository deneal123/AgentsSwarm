import PropTypes from "prop-types";
import { Box } from "@chakra-ui/react";
import SectionDivider from "@ui/atoms/SectionDivider";

function HomeDivider({ variant }) {
  return (
    <Box w="100%" maxW="100%" overflow="hidden">
      <SectionDivider variant={variant} />
    </Box>
  );
}

HomeDivider.propTypes = {
  variant: PropTypes.string,
};

HomeDivider.defaultProps = {
  variant: "electric",
};

export default HomeDivider;
