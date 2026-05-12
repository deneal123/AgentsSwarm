import React from "react";
import { Box } from "@chakra-ui/react";
import { Global } from "@emotion/react";
import { AUTH_FONT_FAMILY, AUTH_THEME } from "../constants";

function AuthPageShell({ children, topGradient, bottomGradient, containerProps = {} }) {
  return (
    <>
      <Global
        styles={{
          "html, body": {
            scrollbarColor: "rgba(239, 68, 68, 0.62) rgba(255, 255, 255, 0.08)",
            scrollbarWidth: "thin",
          },
          "html::-webkit-scrollbar, body::-webkit-scrollbar": { width: "10px" },
          "html::-webkit-scrollbar-track, body::-webkit-scrollbar-track": { background: "rgba(255, 255, 255, 0.08)" },
          "html::-webkit-scrollbar-thumb, body::-webkit-scrollbar-thumb": {
            background: "linear-gradient(180deg, rgba(239, 68, 68, 0.72) 0%, rgba(220, 38, 38, 0.9) 100%)",
            borderRadius: "999px",
            border: "2px solid rgba(6, 6, 6, 0.9)",
          },
        }}
      />

      <Box
        position="relative"
        minH="100vh"
        bg={AUTH_THEME.pageBg}
        display="flex"
        alignItems="center"
        justifyContent="center"
        fontFamily={AUTH_FONT_FAMILY}
        overflow="hidden"
        {...containerProps}
      >
        <Box position="absolute" inset={0} pointerEvents="none" zIndex={0}>
          <Box position="absolute" filter="blur(60px)" {...topGradient} />
          <Box position="absolute" filter="blur(60px)" {...bottomGradient} />
          <Box
            position="absolute"
            inset={0}
            backgroundImage="linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)"
            backgroundSize="42px 42px"
            opacity={0.2}
          />
        </Box>
        {children}
      </Box>
    </>
  );
}

export default AuthPageShell;
