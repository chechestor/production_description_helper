import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// В dev-режиме /api проксируется на локальный backend; в контейнере это делает nginx.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": process.env.VITE_BACKEND_URL || "http://localhost:8000" },
  },
});
