import path from "node:path"
import { fileURLToPath } from "node:url"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react-swc"
import { defineConfig } from "vitest/config"

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig(_mode => ({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@pokex/ui": path.resolve(__dirname, "../../packages/ui/src"),
    },
  },
  server: {
    port: 3000,
    host: true,
  },
  build: {
    minify: "esbuild" as const,
    cssCodeSplit: true,
    modulePreload: { polyfill: false },
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom"],
          query: ["@tanstack/react-query"],
          ui: ["@pokex/ui"],
        },
      },
    },
  },
  test: {
    coverage: {
      provider: "istanbul",
      reporter: ["text", "json", "html"],
    },
  },
}))
