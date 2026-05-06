const eslintPluginReact = require("eslint-plugin-react");
const eslintPluginReactHooks = require("eslint-plugin-react-hooks");
const eslintPluginJsxA11y = require("eslint-plugin-jsx-a11y");
const eslintPluginImport = require("eslint-plugin-import");
const eslintPluginTestingLibrary = require("eslint-plugin-testing-library");
const eslintPluginJestDom = require("eslint-plugin-jest-dom");
const globals = require("globals");

module.exports = [
  {
    ignores: ["build/**", "node_modules/**", "src/features/chat/components/ChatMessages.jsx"],
  },
  {
    files: ["src/**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.node,
        __DEV__: true,
      },
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    plugins: {
      react: eslintPluginReact,
      "react-hooks": eslintPluginReactHooks,
      "jsx-a11y": eslintPluginJsxA11y,
      import: eslintPluginImport,
      "testing-library": eslintPluginTestingLibrary,
      "jest-dom": eslintPluginJestDom,
    },
    settings: {
      react: {
        version: "detect",
      },
      "import/resolver": {
        node: {
          extensions: [".js", ".jsx"],
        },
      },
    },
    rules: {
      "react/jsx-uses-react": "off",
      "react/react-in-jsx-scope": "off",
      "react/prop-types": "off",
      "react-hooks/rules-of-hooks": "warn",
      "react-hooks/exhaustive-deps": "warn",
      "jsx-a11y/anchor-is-valid": "off",
      "import/no-unresolved": "off",
      "testing-library/no-unnecessary-act": "off",
    },
  },
  {
    files: ["src/pages/**/*.{js,jsx}"],
    rules: {
      "max-lines": ["error", { max: 320, skipBlankLines: true, skipComments: true }],
      "max-lines-per-function": ["error", { max: 260, skipBlankLines: true, skipComments: true }],
      "no-restricted-syntax": [
        "warn",
        "IfStatement",
        "SwitchStatement",
        "ForStatement",
        "ForOfStatement",
        "ForInStatement",
        "WhileStatement",
        "DoWhileStatement",
        "TryStatement",
      ],
      "no-restricted-imports": [
        "error",
        {
          patterns: ["**/API/**", "**/services/**", "**/hooks/**"],
        },
      ],
    },
  },

  {
    files: ["src/features/auth/**/*.{js,jsx}"],
    rules: {
      "no-restricted-imports": ["error", { patterns: ["@features/chat/*", "@features/home/*"] }],
    },
  },
  {
    files: ["src/features/chat/**/*.{js,jsx}"],
    rules: {
      "no-restricted-imports": ["error", { patterns: ["@features/auth/*", "@features/home/*"] }],
    },
  },
  {
    files: ["src/features/home/**/*.{js,jsx}"],
    rules: {
      "no-restricted-imports": ["error", { patterns: ["@features/auth/*", "@features/chat/*"] }],
    },
  },
];
