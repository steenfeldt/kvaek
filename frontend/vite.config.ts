import ui from "@nuxt/ui/vite";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";
import { PLATFORMS } from "./src/lib/platforms";

const backend = process.env.VITE_BACKEND_URL || "http://localhost:8000";

export default defineConfig({
  plugins: [
    vue(),
    ui({
      // Light-only for now: without this, Nuxt UI syncs a `dark` class with
      // the system scheme and our light-only design breaks.
      colorMode: false,
      // Bundle icons from the installed @iconify-json collections (lucide +
      // simple-icons) instead of fetching them at runtime. The scan only picks
      // up `i-*` names in templates, so the platform icons are listed explicitly.
      icon: { clientBundle: { scan: true, icons: [...PLATFORMS.map((p) => p.icon), "simple-icons:google"] } },
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
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "Kvæk",
        short_name: "Kvæk",
        description:
          "Swipe-baseret markedsplads, hvor danske virksomheder og nano/mikro-creators finder hinanden.",
        lang: "da",
        start_url: "/",
        display: "standalone",
        background_color: "#efe7d8",
        theme_color: "#efe7d8",
        icons: [
          { src: "/favicon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/logo.png", sizes: "512x512", type: "image/png" },
          { src: "/logo.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        // Never let the SPA fallback or cache swallow server routes.
        navigateFallbackDenylist: [/^\/api/, /^\/_allauth/, /^\/admin/, /^\/staff/, /^\/media/, /^\/static/],
        globPatterns: ["**/*.{js,css,html,png,svg,woff2}"],
      },
    }),
  ],
  server: {
    proxy: {
      "/api": backend,
      // Host header preserved so allauth builds OAuth redirect URIs on localhost:5173.
      "/_allauth": { target: backend, changeOrigin: false },
      "/accounts": { target: backend, changeOrigin: false },
      "/media": backend,
    },
  },
});
