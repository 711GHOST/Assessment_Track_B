import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, /api requests are proxied to the local FastAPI server, so
// no VITE_API_URL is needed. In production set VITE_API_URL to the deployed
// backend origin (e.g. https://your-api.onrender.com).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
