import ui from "@nuxt/ui/vite";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

const backend = process.env.VITE_BACKEND_URL || "http://localhost:8000";

export default defineConfig({
  plugins: [
    vue(),
    ui({
      // Light-only for now: without this, Nuxt UI syncs a `dark` class with
      // the system scheme and our light-only design breaks.
      colorMode: false,
      ui: {
        colors: {
          primary: "clay",
          secondary: "fjord",
          success: "sage",
          info: "fjord",
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
