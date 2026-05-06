import React from "react";
import { Button as ChakraButton } from "@chakra-ui/react";
import { buttonSizeMap } from "./buttonSizeMap";

const SecondaryButton = React.forwardRef(function SecondaryButton(
  { children, size = "md", disabled, isDisabled, type = "button", ...rest },
  ref,
) {
  const sizeStyles = buttonSizeMap[size] || buttonSizeMap.md;
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
