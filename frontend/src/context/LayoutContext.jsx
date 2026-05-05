import { createContext, useContext } from "react";

const noop = () => {};

const LayoutContext = createContext({
  variant: "container",
  setVariant: noop,
  isFooterVisible: true,
  setFooterVisible: noop,
});

export function useLayoutControls() {
  return useContext(LayoutContext);
}

export default LayoutContext;
