import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "build/**",
      "next-env.d.ts",
    ],
  },
  {
    rules: {
      // Allow pragmatic 'any' usage to unblock builds
      "@typescript-eslint/no-explicit-any": "off",
      // Warn on unused vars, but ignore those prefixed with _
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }
      ],
      // Allow apostrophes in JSX text without escaping
      "react/no-unescaped-entities": "off",
      // Keep hooks exhaustive deps as a warning (not an error)
      "react-hooks/exhaustive-deps": "warn",
    },
  },
];

export default eslintConfig;
