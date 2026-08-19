import type { Plugin, ProxyOptions } from "vite";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

const QUIET_WS_ERROR_CODES = new Set(["ECONNRESET", "ECONNABORTED", "EPIPE", "ECONNREFUSED"]);

/** Vite logs ws proxy failures internally; filter expected dev noise when SocketIO is off. */
function suppressViteWsProxyNoise(): Plugin {
  return {
    name: "suppress-vite-ws-proxy-noise",
    configureServer() {
      const origError = console.error.bind(console);
      console.error = (...args: unknown[]) => {
        const first = args[0];
        if (typeof first === "string" && first.includes("[vite] ws proxy socket error")) {
          const err = args[1] as NodeJS.ErrnoException | undefined;
          if (!err?.code || QUIET_WS_ERROR_CODES.has(err.code)) {
            return;
          }
        }
        origError(...args);
      };
    },
  };
}

function quietWsProxy(): Pick<ProxyOptions, "configure"> {
  return {
    configure: (proxy) => {
      proxy.on("error", (err, _req, res) => {
        const code = (err as NodeJS.ErrnoException)?.code;
        if (code && QUIET_WS_ERROR_CODES.has(code)) {
          const response = res as { writeHead?: (status: number) => void; headersSent?: boolean; end?: () => void };
          if (response?.writeHead && !response.headersSent) {
            response.writeHead(502);
            response.end?.();
          }
          return;
        }
        console.warn("[vite] proxy error:", err);
      });
      proxy.on("proxyReqWs", (_proxyReq, _req, socket) => {
        socket.on("error", () => {
          /* expected when optional realtime backend is down */
        });
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backend = env.VITE_BACKEND_URL || "http://127.0.0.1:5000";
  const socketIoProxyEnabled =
    env.VITE_ENABLE_SOCKETIO === "true" || env.VITE_WS_GATEWAY_MODE === "1";
  const socketioTarget =
    env.VITE_SOCKETIO_TARGET ||
    (env.VITE_WS_GATEWAY_MODE === "1" ? "http://127.0.0.1:5001" : backend);
  const wsGatewayTarget = env.VITE_WS_GATEWAY_URL || "http://127.0.0.1:9091";

  const proxy: Record<string, ProxyOptions> = {
    "/api": {
      target: backend,
      changeOrigin: true,
    },
    "/login": {
      target: backend,
      changeOrigin: true,
    },
  };

  if (socketIoProxyEnabled) {
    proxy["/socket.io"] = {
      target: socketioTarget,
      changeOrigin: true,
      ws: true,
      ...quietWsProxy(),
    };
  }

  if (env.VITE_ENABLE_WS_GATEWAY === "true") {
    proxy["/ws"] = {
      target: wsGatewayTarget,
      changeOrigin: true,
      ws: true,
      ...quietWsProxy(),
    };
  }

  return {
    plugins: [react(), suppressViteWsProxyNoise()],
    base: "/app/",
    server: {
      port: 5173,
      proxy,
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
