import PropTypes from "prop-types";
import { Box } from "@chakra-ui/react";
import FeatureSlider from "@features/home/components/FeatureSlider";

function HomeFeatureSliderSection({ containerProps }) {
  return (
    <Box
      maxW={containerProps?.maxW || "1400px"}
      mx="auto"
      px={containerProps?.px || { base: 4, md: 6, lg: 8 }}
    >
      <FeatureSlider />
    </Box>
  );
}

HomeFeatureSliderSection.propTypes = {
  containerProps: PropTypes.object,
};

HomeFeatureSliderSection.defaultProps = {
  containerProps: {},
};

export default HomeFeatureSliderSection;
