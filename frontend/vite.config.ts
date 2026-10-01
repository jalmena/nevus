import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "prompt",
      includeAssets: ["icons/icon.svg", "brand/wordmark-dark.svg", "fonts/*.woff2"],
      manifest: {
        name: "neVus",
        short_name: "neVus",
        description: "Self-hosted longitudinal tracking of moles and skin marks. Not a diagnostic tool.",
        lang: "en",
        start_url: "/",
        scope: "/",
        display: "standalone",
        background_color: "#17161A",
        theme_color: "#17161A",
        icons: [
          { src: "icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icons/icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,svg,png,woff2,webmanifest}"],
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//, /^\/healthz$/],
        // Patterns are matched against the full URL, so they test the path explicitly.
        runtimeCaching: [
          {
            // Small renditions, immutable by hash: kept for offline viewing, a bounded number of them.
            urlPattern: ({ url }) => /^\/api\/images\/[^/]+\/(thumb|preview)$/.test(url.pathname),
            handler: "CacheFirst",
            options: { cacheName: "photos", expiration: { maxEntries: 400, maxAgeSeconds: 30 * 24 * 3600 } },
          },
          {
            // Everything else the app reads, so a known page opens without a connection.
            // Never the originals, the full renditions or downloads.
            urlPattern: ({ url }) =>
              url.pathname.startsWith("/api/") &&
              !/\/(original|full)$/.test(url.pathname) &&
              !url.pathname.includes("/download") &&
              !url.pathname.startsWith("/api/reference-card"),
            handler: "NetworkFirst",
            options: { cacheName: "api", networkTimeoutSeconds: 4, expiration: { maxEntries: 500 } },
          },
        ],
      },
    }),
  ],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8080", "/healthz": "http://127.0.0.1:8080" } },
  build: { sourcemap: false, target: "es2022" },
});
