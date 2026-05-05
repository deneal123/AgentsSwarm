// Jest / jsdom setup: polyfills for window.matchMedia used by Chakra UI and framer-motion
// Provide a safe stub so tests that use responsive hooks or prefers-reduced-motion don't throw.
/* eslint-disable no-undef */
import "@testing-library/jest-dom";

// Always override matchMedia with a jest mock implementation so tests are deterministic.
const createMatchMedia = () =>
  jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // for older browsers / libs
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(() => false),
  }));

const mockMatchMedia = createMatchMedia();

Object.defineProperty(globalThis, "matchMedia", {
  writable: true,
  configurable: true,
  value: mockMatchMedia,
});

if (typeof window !== "undefined") {
  window.matchMedia = mockMatchMedia;
}

if (typeof document !== "undefined" && document.defaultView) {
  document.defaultView.matchMedia = mockMatchMedia;
}

// Ensure a stable global helper node for Chakra exists in document.body so the
// provider doesn't create it inside the test render container. This prevents
// tests that assert an empty container from failing due to an injected node.
try {
  if (typeof document !== "undefined" && !document.getElementById("__chakra_env")) {
    const __chakra_env = document.createElement("span");
    __chakra_env.id = "__chakra_env";
    __chakra_env.hidden = true;
    document.body.appendChild(__chakra_env);
  }
} catch (e) {
  // ignore in environments where document isn't available yet
}

// Provide a minimal global for ResizeObserver if some components rely on it in tests
if (typeof window !== "undefined" && typeof window.ResizeObserver === "undefined") {
  class ResizeObserver {
    constructor(cb) {
      this._cb = cb;
    }
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  window.ResizeObserver = ResizeObserver;
}

// Mock axios globally to avoid Jest transform issues with ESM modules in node_modules
jest.mock("axios", () => {
  const mAxios = {
    create: () => mAxios,
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    request: jest.fn(),
    interceptors: {
      response: { use: jest.fn() },
      request: { use: jest.fn() },
    },
  };
  return mAxios;
});

// Defensive mocks for Chakra UI / framer-motion hooks that rely on matchMedia
// This prevents occasional timing issues where the library reads matchMedia
// before our global mock is effective.
try {
  jest.mock("@chakra-ui/media-query", () => ({
    useMediaQuery: jest.fn(() => [false]),
  }));
} catch (e) {
  // noop — if jest.mock can't be called here, ignore
}

try {
  // Provide a lightweight mock for framer-motion to avoid its runtime init
  // which calls window.matchMedia and can fail in jsdom. We only need a
  // minimal subset for tests: `motion` primitives and `useReducedMotion`.
  jest.mock("framer-motion", () => {
    const React = require("react");
    // Filter out motion-specific props so they don't get forwarded to DOM nodes
    const motionPropNames = new Set([
      "initial",
      "animate",
      "exit",
      "variants",
      "whileHover",
      "whileTap",
      "whileFocus",
      "whileInView",
      "onUpdate",
      "onAnimationComplete",
      "onAnimationStart",
      "transition",
      "layout",
      "layoutId",
      "drag",
      "dragConstraints",
      "dragElastic",
      "dragPropagation",
      "dragMomentum",
      "viewport",
      "style",
    ]);

    const mockMotionFactory = (Comp) => {
      // Return a forwardRef component that filters out motion-specific props
      return React.forwardRef(({ children, ...props }, ref) => {
        const filtered = Object.keys(props).reduce((acc, k) => {
          if (!motionPropNames.has(k)) acc[k] = props[k];
          return acc;
        }, {});
        // If Comp is a string tag, create a DOM element, otherwise render the component
        return typeof Comp === "string"
          ? React.createElement(Comp, { ref, ...filtered }, children)
          : React.createElement(Comp, { ref, ...filtered }, children);
      });
    };

    // motion should be callable (motion(Component)) and also support
    // property access (motion.div). We implement a callable function and
    // wrap it with a Proxy to handle property access. Ensure that when
    // motion is called with a React component we still filter motion props.
    const motionCallable = (Comp) => mockMotionFactory(Comp);

    const motionProxy = new Proxy(motionCallable, {
      get: (_, tag) => mockMotionFactory(tag),
    });

    return {
      motion: motionProxy,
      AnimatePresence: ({ children }) => React.createElement(React.Fragment, null, children),
      useReducedMotion: () => false,
    };
  });
} catch (e) {
  // noop
}

// Some Chakra internals mount a helper node (#__chakra_env) into the document
// during provider setup. Tests that assert an empty container can fail if that
// node is present. Remove it after each test to keep test containers clean.
// no-op cleanup: we keep a stable __chakra_env in document.body to avoid
// races between Chakra internals and rtl cleanup.
afterEach(() => {});

// Ensure Chakra's prefers-reduced-motion hook is stable for tests while keeping
// the real Chakra exports available. We also make ChakraProvider a passthrough
// to avoid injecting environment DOM nodes into test containers
// (such as #__chakra_env) which can break assertions that expect an
// empty container.
try {
  // Use the real Chakra exports but override prefers-reduced-motion hook so
  // tests are deterministic. We avoid replacing ChakraProvider with a
  // Fragment because the styled-system utilities (like parseGradient)
  // expect a theme provided by Chakra's context; removing the provider
  // caused runtime errors in tests.
  jest.mock("@chakra-ui/react", () => {
    const actual = jest.requireActual("@chakra-ui/react");
    return {
      ...actual,
      // keep the real ChakraProvider so theme/context are available
      ChakraProvider: actual.ChakraProvider,
      // deterministically disable reduced motion for tests
      usePrefersReducedMotion: () => false,
    };
  });
} catch (e) {
  // noop
}
