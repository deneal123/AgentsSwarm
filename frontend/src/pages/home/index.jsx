import React from "react";
import { Box } from "@chakra-ui/react";
import { useLayoutControls } from "@context/LayoutContext";
import { HomeWorkspaceCanonicalSection } from "@features/home/components/sections";

function HomePage() {
  const { setVariant } = useLayoutControls();

  React.useEffect(() => {
    setVariant("full");
    return () => setVariant("container");
  }, [setVariant]);

  return (
    <Box w="100%" minH="100vh" position="relative">
      <HomeWorkspaceCanonicalSection />
    </Box>
  );
}

export default HomePage;
