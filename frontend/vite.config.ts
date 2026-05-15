import path from "node:path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// Base must be relative so the bundled assets work when served from
// FastAPI's static mount under arbitrary ports.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendUrl = env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    base: "./",
    server: {
      port: 5173,
      // Override the dev backend target with VITE_BACKEND_URL when the local
      // API server is not bound to the default port.
      proxy: {
        "/health": backendUrl,
        "/version": backendUrl,
        "/profiles": backendUrl,
        "/pair": backendUrl,
        "/extract": backendUrl,
        "/inventory": backendUrl,
        "/snapshots": backendUrl,
        "/export": backendUrl,
      },
    },
  };
});
