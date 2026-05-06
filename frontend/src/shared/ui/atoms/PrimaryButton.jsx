import React from "react";
import { Button as ChakraButton } from "@chakra-ui/react";
import { buttonSizeMap } from "./buttonSizeMap";

const PrimaryButton = React.forwardRef(function PrimaryButton(
  { children, size = "md", disabled, isDisabled, type = "button", ...rest },
  ref,
) {
  const sizeStyles = buttonSizeMap[size] || buttonSizeMap.md;
  const finalIsDisabled = isDisabled ?? disabled ?? rest.isDisabled;

  return (
    <ChakraButton
      ref={ref}
      variant="primary"
      type={type}
      isDisabled={finalIsDisabled}
      {...sizeStyles}
      {...rest}
    >
      {children}
    </ChakraButton>
  );
});

PrimaryButton.displayName = "PrimaryButton";

export default PrimaryButton;
