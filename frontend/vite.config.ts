import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// The Python tutor server (src/tutor/server.py) is the backend of record. Both the dev server and
// `vite preview` forward /api to it, so the browser talks to one origin and no CORS is needed.
// Point elsewhere with TUTOR_BACKEND=http://127.0.0.1:8001 npm run dev.
export default defineConfig(({ mode }) => {
  const backend = loadEnv(mode, ".", "").TUTOR_BACKEND || "http://127.0.0.1:8000";
  const proxy = { "/api": { target: backend, changeOrigin: true } };
  return {
    plugins: [react(), tailwindcss()],
    server: { port: 5173, proxy },
    preview: { port: 4173, proxy },
  };
});
