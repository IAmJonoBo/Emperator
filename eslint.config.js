import js from "@eslint/js";
import eslintPluginImport from "eslint-plugin-import";
import globals from "globals";
import tseslint from "typescript-eslint";

const ignoredPaths = [
  "**/*.min.js",
  "dist/",
  "build/",
  "vendor/",
  "public/",
  "site/",
  "emperator_specs/site/",
  "site/js/bootstrap.bundle.min.js",
  ".venv/",
  ".pnpm-store/",
  "coverage/",
  "**/._*",
];

export default tseslint.config(
  {
    ignores: ignoredPaths,
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{js,jsx,ts,tsx}"],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    plugins: {
      import: eslintPluginImport,
    },
    rules: {
      "import/order": [
        "warn",
        {
          alphabetize: { order: "asc", caseInsensitive: true },
          "newlines-between": "always",
        },
      ],
      "import/newline-after-import": ["warn", { count: 1 }],
    },
  }
);
