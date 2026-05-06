import React from "react";
import { Text as ChakraText } from "@chakra-ui/react";
import { colors, typography } from "@theme/tokens";

/**
 * Typography components based on design system
 */

export function Title({ variant = "large", children, color, ...rest }) {
  const style = typography.title[variant] || typography.title.large;
  return (
    <ChakraText
      as="h1"
      fontSize={style.fontSize}
      lineHeight={style.lineHeight}
      fontWeight={style.fontWeight}
      color={color || colors.text.primary}
      {...rest}
    >
      {children}
    </ChakraText>
  );
}

export function Subtitle({ variant = "large", children, color, ...rest }) {
  const style = typography.subtitle[variant] || typography.subtitle.large;
  return (
    <ChakraText
      as="h2"
      fontSize={style.fontSize}
      lineHeight={style.lineHeight}
      fontWeight={style.fontWeight}
      color={color || colors.text.primary}
      {...rest}
    >
      {children}
    </ChakraText>
  );
}

export function Body({ variant = "large", children, color, ...rest }) {
  const style = typography.body[variant] || typography.body.large;
  return (
    <ChakraText
      fontSize={style.fontSize}
      lineHeight={style.lineHeight}
      fontWeight={style.fontWeight}
      color={color || colors.text.secondary}
      {...rest}
    >
      {children}
    </ChakraText>
  );
}

export function Footnote({ variant = "medium", children, color, ...rest }) {
  const style = typography.footnote[variant] || typography.footnote.medium;
  return (
    <ChakraText
      fontSize={style.fontSize}
      lineHeight={style.lineHeight}
      fontWeight={style.fontWeight}
      color={color || colors.text.tertiary}
      {...rest}
    >
      {children}
    </ChakraText>
  );
}
