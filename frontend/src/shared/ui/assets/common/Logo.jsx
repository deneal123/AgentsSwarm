import { Image } from "@chakra-ui/react";
import logo from "./logo.svg";
import { PROJECT_NAME } from "../../../../constants";

const VARIANT_SOURCES = {
  solid: logo,
};

function Logo({ boxSize = 6, priority = false, ...rest }) {
  const src = VARIANT_SOURCES.solid;
  return (
    <Image
      src={src}
      alt={`${PROJECT_NAME} logo`}
      title={PROJECT_NAME}
      boxSize={boxSize}
      loading={priority ? "eager" : "lazy"}
      fetchpriority={priority ? "high" : "auto"}
      {...rest}
    />
  );
}

export default Logo;
