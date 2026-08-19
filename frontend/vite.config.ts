import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

/** Swallow expected WS proxy errors when SocketIO backend is not running. */
function quietWsProxy() {
  return {
    configure: (proxy: {
      on: (event: string, handler: (...args: unknown[]) => void) => void;
    }) => {
      proxy.on("error", (err: unknown, _req: unknown, res: { writeHead?: (code: number) => void; headersSent?: boolean; end?: () => void }) => {
        const code = (err as NodeJS.ErrnoException)?.code;
        if (code === "ECONNRESET" || code === "ECONNABORTED" || code === "EPIPE") {
          if (res?.writeHead && !res.headersSent) {
            res.writeHead?.(502);
            res.end?.();
          }
          return;
        }
        console.warn("[vite] proxy error:", err);
      });
      proxy.on("proxyReqWs", (_proxyReq: unknown, _req: unknown, socket: { on?: (event: string, handler: () => void) => void }) => {
        socket.on?.("error", () => {
          /* backend WS unavailable — client will reconnect after capabilities probe */
        });
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backend = env.VITE_BACKEND_URL || "http://127.0.0.1:5000";
  const socketioTarget =
    env.VITE_SOCKETIO_TARGET ||
    (env.VITE_WS_GATEWAY_MODE === "1" ? "http://127.0.0.1:5001" : backend);
  const wsGatewayTarget = env.VITE_WS_GATEWAY_URL || "http://127.0.0.1:9091";

  return {
    plugins: [react()],
    base: "/app/",
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: backend,
          changeOrigin: true,
        },
        "/login": {
          target: backend,
          changeOrigin: true,
        },
        "/socket.io": {
          target: socketioTarget,
          changeOrigin: true,
          ws: true,
          ...quietWsProxy(),
        },
        "/ws": {
          target: wsGatewayTarget,
          changeOrigin: true,
          ws: true,
          ...quietWsProxy(),
        },
      },
    },
    build: {
      outDir: "dist",
      emptyOutDir: true,
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ["react", "react-dom", "react-router-dom"],
            charts: ["lightweight-charts", "echarts", "recharts"],
            i18n: ["i18next", "react-i18next"],
            swr: ["swr"],
            socketio: ["socket.io-client"],
          },
        },
      },
    },
  };
});
