import path from "node:path";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const outDir = path.resolve(__dirname, "../backend/app/static/mobile");

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 5174,
    proxy: {
      "/api": { target: "http://127.0.0.1:5000", changeOrigin: true },
      "/uploads": { target: "http://127.0.0.1:5000", changeOrigin: true },
    },
  },
  build: {
    outDir,
    emptyOutDir: true,
  },
});
