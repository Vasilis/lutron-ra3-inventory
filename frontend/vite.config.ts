import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Base must be relative so the bundled assets work when served from
// FastAPI's static mount under arbitrary ports.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  base: "./",
  server: {
    port: 5173,
    // Proxy API calls in dev so the frontend can hit the backend on its
    // random port via VITE_BACKEND_URL.
    proxy: {
      "/health": "http://127.0.0.1:8000",
      "/version": "http://127.0.0.1:8000",
      "/profiles": "http://127.0.0.1:8000",
      "/pair": "http://127.0.0.1:8000",
      "/extract": "http://127.0.0.1:8000",
      "/inventory": "http://127.0.0.1:8000",
      "/snapshots": "http://127.0.0.1:8000",
      "/export": "http://127.0.0.1:8000",
    },
  },
});
