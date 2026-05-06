import { dimensions } from "@theme/tokens";

export const buttonSizeMap = {
  sm: { h: "40px", px: 4, fontSize: "14px" },
  md: { h: dimensions.button.heightMobile, px: 6, fontSize: "14px" },
  lg: {
    h: { base: dimensions.button.heightMobile, md: dimensions.button.heightDesktop },
    px: 8,
    fontSize: { base: "14px", md: "18px" },
  },
};
