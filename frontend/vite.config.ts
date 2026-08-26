import ui from "@nuxt/ui/vite";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

const backend = process.env.VITE_BACKEND_URL || "http://localhost:8000";

export default defineConfig({
  plugins: [
    vue(),
    ui({
      ui: {
        colors: {
          primary: "clay",
          neutral: "stone",
        },
      },
    }),
  ],
  server: {
    proxy: {
      "/api": backend,
      "/_allauth": backend,
      "/media": backend,
    },
  },
});
