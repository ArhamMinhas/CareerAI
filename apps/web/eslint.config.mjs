import { FlatCompat } from "@eslint/eslintrc";
import { defineConfig, globalIgnores } from "eslint/config";

// `eslint-config-next@15.5.x` still ships only the legacy (.eslintrc-shaped, CJS `extends`)
// config format — flat-config-native exports (a plain array from
// `eslint-config-next/core-web-vitals`) only landed later, in the 16.x line. Bridging via
// `FlatCompat` is the standard, documented way to use a legacy-shaped shareable config under
// ESLint 9's flat config; drop this once `eslint-config-next` is upgraded back past 16.x.
const compat = new FlatCompat({ baseDirectory: import.meta.dirname });

const eslintConfig = defineConfig([
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
