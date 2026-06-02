import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { existsSync } from "node:fs";
import path from "node:path";

const root = fileURLToPath(new URL(".", import.meta.url));

// Mirror tsconfig.json paths: "@/*" maps to BOTH ./src/* and ./*.
// Vite aliases only do string-substitution and can't try multiple roots,
// so we use a custom resolver plugin that probes both roots in order.
const dualRootAlias = {
  name: "vitest-dual-root-alias",
  enforce: "pre" as const,
  resolveId(source: string) {
    if (!source.startsWith("@/")) return null;
    const rest = source.slice(2);
    const candidates = [path.join(root, "src", rest), path.join(root, rest)];
    for (const base of candidates) {
      for (const ext of ["", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx"]) {
        const p = base + ext;
        if (existsSync(p)) return p;
      }
    }
    return null;
  },
};

export default defineConfig({
  plugins: [dualRootAlias, react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["**/*.test.{ts,tsx}"],
    exclude: ["node_modules", ".next", "dist"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "json-summary", "lcov"],
      reportsDirectory: "./coverage",
      include: [
        "components/**/*.{ts,tsx}",
        "src/**/*.{ts,tsx}",
        "app/**/*.{ts,tsx}",
        "lib/**/*.{ts,tsx}",
      ],
      exclude: [
        "**/__tests__/**",
        "**/*.test.{ts,tsx}",
        "**/*.d.ts",
        "node_modules/**",
        ".next/**",
        "dist/**",
        "src/constants/enums.ts",
        // Framework/structural files with no meaningful logic to unit-test.
        "app/**/layout.tsx",
        "app/**/loading.tsx",
        "app/**/not-found.tsx",
        "app/**/error.tsx",
        "**/*.config.*",
        // Pure type declaration modules (no runtime logic).
        "src/types/**",
      ],
    },
  },
  // import { fileURLToPath } from "node:url";
  // import { defineConfig } from "vitest/config";

  // export default defineConfig({
  //   resolve: {
  //     alias: {
  //       "@": fileURLToPath(new URL(".", import.meta.url)),
  //     },
  //   },
  //   test: {
  //     environment: "node",
  //   },
  // });
});
