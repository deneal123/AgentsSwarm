import React from "react";
import PropTypes from "prop-types";
import HeroSectionCanonical from "@features/home/components/sections/HeroSectionCanonical";

function HeroSection({ isAuthenticated }) {
  return <HeroSectionCanonical variant="platform" isAuthenticated={isAuthenticated} />;
}

HeroSection.propTypes = {
  isAuthenticated: PropTypes.bool,
};

HeroSection.defaultProps = {
  isAuthenticated: false,
};

export default HeroSection;
