import React from "react";
import PropTypes from "prop-types";
import BenefitsSectionCanonical from "@features/home/components/sections/BenefitsSectionCanonical";

function HomeBenefitsSection({ containerProps }) {
  return <BenefitsSectionCanonical containerProps={containerProps} />;
}

HomeBenefitsSection.propTypes = {
  containerProps: PropTypes.object,
};

HomeBenefitsSection.defaultProps = {
  containerProps: {},
};

export default HomeBenefitsSection;
