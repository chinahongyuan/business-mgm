import path from "node:path";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Build output is served by Flask at /system-management/ (see backend/app/__init__.py)
const outDir = path.resolve(__dirname, "../backend/app/static/admin");

export default defineConfig({
  base: "/system-management/",
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      // ckeditor5 package.json 未导出 dist/*.css，需显式映射
      "ckeditor5/ckeditor5.css": path.resolve(__dirname, "node_modules/ckeditor5/dist/ckeditor5.css"),
      "ckeditor5/ckeditor5-content.css": path.resolve(__dirname, "node_modules/ckeditor5/dist/ckeditor5-content.css"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:5000", changeOrigin: true },
      "/uploads": { target: "http://127.0.0.1:5000", changeOrigin: true },
    },
  },
  build: {
    outDir,
    emptyOutDir: true,
    // echarts 单独分包；Vue + Element Plus 必须同包，否则会出现
    // element-plus <-> vue-vendor 循环依赖，运行时报 Cannot access before initialization
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return;
          if (id.includes("echarts") || id.includes("vue-echarts") || id.includes("zrender")) {
            return "echarts";
          }
          if (
            id.includes("vue") ||
            id.includes("vue-router") ||
            id.includes("pinia") ||
            id.includes("@vue") ||
            id.includes("element-plus") ||
            id.includes("@element-plus")
          ) {
            return "vue-vendor";
          }
        },
      },
    },
  },
});
