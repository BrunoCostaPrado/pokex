import path from "node:path"
import { fileURLToPath } from "node:url"
import process from "node:process"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import { visualizer } from "rollup-plugin-visualizer"

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const host = process.env.TAURI_DEV_HOST

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react(), tailwindcss(), mode === "analyze" && visualizer({ open: true, filename: "dist/stats.html" })].filter(Boolean),
  resolve: {
    alias: {
      "@pokex/ui": path.resolve(__dirname, "../../packages/ui/src"),
    },
  },

  // Vite options tailored for Tauri development and only applied in `tauri dev` or `tauri build`
  //
  // 1. prevent Vite from obscuring rust errors
  clearScreen: false,
  // 2. tauri expects a fixed port, fail if that port is not available
  server: {
    port: 1420,
    strictPort: true,
    host: host || false,
    hmr: host
      ? {
          protocol: "ws",
          host,
          port: 1421,
        }
      : undefined,
    watch: {
      // 3. tell Vite to ignore watching `src-tauri`
      ignored: ["**/src-tauri/**"],
    },
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
}))
