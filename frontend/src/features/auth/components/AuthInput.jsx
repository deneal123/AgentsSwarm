import React, { useState } from "react";
import { Box, FormControl, FormErrorMessage, FormLabel, Input, Icon } from "@chakra-ui/react";
import { motion } from "framer-motion";
import { tokens } from "@theme/tokens";

const AUTH_ACCENT = "#ef4444";

const MotionBox = motion(Box);

/**
 * AuthInput - стилизованное поле ввода для форм авторизации
 * С иконкой, glow эффектом при фокусе, анимациями
 */
const AuthInput = ({
  id,
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  icon,
  isRequired = false,
  isInvalid = false,
  errorMessage,
  helperText,
  autoComplete,
  ...rest
}) => {
  const [isFocused, setIsFocused] = useState(false);

  return (
    <FormControl id={id} isRequired={isRequired} isInvalid={isInvalid}>
      <FormLabel
        fontSize={tokens.typography.footnote.medium}
        color={tokens.colors.text.secondary}
        mb={2}
      >
        {label}
      </FormLabel>

      <MotionBox
        position="relative"
        animate={{ scale: isFocused ? 1.01 : 1 }}
        transition={{ duration: 0.2 }}
      >
        {icon && (
          <Box
            position="absolute"
            left="14px"
            top="50%"
            transform="translateY(-50%)"
            zIndex={2}
            pointerEvents="none"
          >
            <Icon
              as={icon}
              color={isFocused ? AUTH_ACCENT : tokens.colors.text.tertiary}
              w={5}
              h={5}
              transition="color 0.2s"
            />
          </Box>
        )}

        <Input
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          autoComplete={autoComplete}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          pl={icon ? "44px" : "14px"}
          pr="14px"
          h="50px"
          fontSize={tokens.typography.body.small}
          bg="rgba(8, 8, 8, 0.86)"
          border="1px solid"
          borderColor={
            isInvalid
              ? tokens.colors.error
              : isFocused
                ? AUTH_ACCENT
                : tokens.colors.border.light
          }
          borderRadius={tokens.borderRadius.md}
          color={tokens.colors.text.primary}
          _placeholder={{ color: tokens.colors.text.tertiary }}
          _hover={{
            borderColor: isInvalid ? tokens.colors.error : tokens.colors.border.medium,
          }}
          _focus={{
            borderColor: isInvalid ? tokens.colors.error : AUTH_ACCENT,
            boxShadow: isInvalid
              ? `0 0 0 1px ${tokens.colors.error}, 0 0 20px rgba(239, 68, 68, 0.2)`
              : `0 0 0 1px ${AUTH_ACCENT}, 0 0 0 4px rgba(239, 68, 68, 0.15)`,
            outline: "none",
          }}
          transition="all 0.2s"
          {...rest}
        />
      </MotionBox>

      {isInvalid && errorMessage && (
        <FormErrorMessage fontSize={tokens.typography.footnote.small} mt={1}>
          {errorMessage}
        </FormErrorMessage>
      )}

      {!isInvalid && helperText && (
        <Box fontSize={tokens.typography.footnote.small} color={tokens.colors.text.tertiary} mt={1}>
          {helperText}
        </Box>
      )}
    </FormControl>
  );
};

export default AuthInput;
