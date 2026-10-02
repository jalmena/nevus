import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  test: {
    environment: "jsdom",
    // Some tests wait for a polling interval (reports being made); slow CI runners need the room.
    testTimeout: 20_000,
    globals: true,
    setupFiles: ["tests/setup.ts"],
    // The first test of a file pays for compiling the app; on a loaded machine that passes five seconds.
    include: ["tests/**/*.test.{ts,tsx}", "src/**/*.test.ts"],
  },
});
