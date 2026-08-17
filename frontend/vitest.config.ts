import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "."),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["**/*.test.{ts,tsx}"],
    exclude: ["node_modules", ".next"],
    // Nenhuma suíte ainda existe (chega na Fase 1 — single-flight do refresh).
    // Sem isto, `vitest run` falha com "no test files found" e quebra o portão de validação da Fase 0.
    passWithNoTests: true,
  },
});
