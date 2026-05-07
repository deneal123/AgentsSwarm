import { createContext, useContext, useMemo } from "react";

const noop = () => {};

const LayoutStateContext = createContext({
  variant: "container",
  isFooterVisible: true,
});

const LayoutActionsContext = createContext({
  setVariant: noop,
  setFooterVisible: noop,
});

export function useLayoutState() {
  return useContext(LayoutStateContext);
}

export function useLayoutActions() {
  return useContext(LayoutActionsContext);
}

export function useLayoutControls() {
  const state = useLayoutState();
  const actions = useLayoutActions();
  return useMemo(() => ({ ...state, ...actions }), [actions, state]);
}

export function LayoutProvider({ state, actions, children }) {
  return (
    <LayoutStateContext.Provider value={state}>
      <LayoutActionsContext.Provider value={actions}>{children}</LayoutActionsContext.Provider>
    </LayoutStateContext.Provider>
  );
}
