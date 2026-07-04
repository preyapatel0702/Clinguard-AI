import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import svgr from "vite-plugin-svgr";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  // The FastAPI backend mounts every route at the root (e.g. `/health`,
  // `/audit/{id}`, `/metrics/overview`, `/analyze`) - there is no `/api`
  // prefix on the server side. VITE_API_BASE_URL defaults to "/api" so
  // the browser calls a same-origin path (avoiding CORS in dev); this
  // proxy strips that prefix and forwards to the real backend origin,
  // configurable via VITE_BACKEND_ORIGIN (defaults to localhost:8000).
  const backendOrigin = env.VITE_BACKEND_ORIGIN ?? "http://localhost:8000";

  return {
    plugins: [
      react(),
      svgr({
        svgrOptions: {
          icon: true,
          // This will transform your SVG to a React component
          exportType: "named",
          namedExport: "ReactComponent",
        },
      }),
    ],
    server: {
      proxy: {
        "/api": {
          target: backendOrigin,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
      },
    },
  };
});
