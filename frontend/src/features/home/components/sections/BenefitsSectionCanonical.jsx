import React from "react";
import PropTypes from "prop-types";
import { Box } from "@chakra-ui/react";
import BenefitsSection from "@features/home/components/BenefitsSection";

function BenefitsSectionCanonical({ containerProps }) {
  return (
    <Box maxW={containerProps.maxW} mx="auto" px={containerProps.px}>
      <BenefitsSection />
    </Box>
  );
}

BenefitsSectionCanonical.propTypes = {
  containerProps: PropTypes.shape({
    maxW: PropTypes.oneOfType([PropTypes.string, PropTypes.object]),
    px: PropTypes.oneOfType([PropTypes.number, PropTypes.object]),
  }),
};

BenefitsSectionCanonical.defaultProps = {
  containerProps: {
    maxW: "1400px",
    px: { base: 4, md: 6, lg: 8 },
  },
};

export default BenefitsSectionCanonical;
