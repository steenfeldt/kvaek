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
        // Palette roles per the brand sheet: sage = primary actions,
        // terracotta (clay) = secondary/badges, fjord = links/data/info.
        colors: {
          primary: "sage",
          secondary: "clay",
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
