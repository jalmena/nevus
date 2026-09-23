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
        runtimeCaching: [
          {
            urlPattern: /^\/api\//,
            handler: "NetworkFirst",
            options: { cacheName: "api", networkTimeoutSeconds: 4 },
          },
        ],
      },
    }),
  ],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8080", "/healthz": "http://127.0.0.1:8080" } },
  build: { sourcemap: false, target: "es2022" },
});
