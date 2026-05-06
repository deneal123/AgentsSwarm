import React from "react";
import { Button as ChakraButton } from "@chakra-ui/react";
import { dimensions } from "@theme/tokens";

const sizeMap = {
  sm: { h: "40px", px: 4, fontSize: "14px" },
  md: { h: dimensions.button.heightMobile, px: 6, fontSize: "14px" },
  lg: {
    h: { base: dimensions.button.heightMobile, md: dimensions.button.heightDesktop },
    px: 8,
    fontSize: { base: "14px", md: "18px" },
  },
};

const SecondaryButton = React.forwardRef(function SecondaryButton(
  { children, size = "md", disabled, isDisabled, type = "button", ...rest },
  ref,
) {
  const sizeStyles = sizeMap[size] || sizeMap.md;
  const finalIsDisabled = isDisabled ?? disabled ?? rest.isDisabled;

  return (
    <ChakraButton
      ref={ref}
      variant="secondary"
      type={type}
      isDisabled={finalIsDisabled}
      {...sizeStyles}
      {...rest}
    >
      {children}
    </ChakraButton>
  );
});

SecondaryButton.displayName = "SecondaryButton";

export default SecondaryButton;
