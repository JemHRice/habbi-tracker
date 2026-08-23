import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
// Imported from vitest rather than vite so the `test` block below is typed.
import { defineConfig } from "vitest/config";

// The app shell is precached so Habbi-Tracker opens offline showing the
// last-known board. Mutations still need a connection — there is deliberately
// no offline queue this phase.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.ico", "apple-touch-icon-180x180.png"],
      manifest: {
        name: "Habbi-Tracker",
        short_name: "Habbi",
        description: "A calm, non-punitive habit tracker.",
        theme_color: "#CA758A",
        background_color: "#FAF6EE",
        display: "standalone",
        orientation: "portrait",
        start_url: "/",
        scope: "/",
        icons: [
          { src: "pwa-64x64.png", sizes: "64x64", type: "image/png" },
          { src: "pwa-192x192.png", sizes: "192x192", type: "image/png" },
          { src: "pwa-512x512.png", sizes: "512x512", type: "image/png" },
          {
            src: "maskable-icon-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
        // API responses are never precached: the board must not be served from
        // a stale service-worker cache. Offline viewing comes from the
        // persisted React Query cache instead, which knows how old it is.
        navigateFallbackDenylist: [/^\/api/],
      },
      devOptions: { enabled: false },
    }),
  ],
  server: {
    port: 5173,
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: true,
  },
});
