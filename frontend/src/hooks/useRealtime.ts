import { useEffect, useState } from "react";
import { io, type Socket } from "socket.io-client";

export type QuoteUpdate = {
  symbol?: string;
  price?: number;
  change_pct?: number;
  [key: string]: unknown;
};

export type AiAnalysisChunk = {
  symbol?: string;
  market?: string;
  chunk?: Record<string, unknown>;
  timestamp?: string;
};

export function useRealtime(enabled: boolean) {
  const [connected, setConnected] = useState(false);
  const [lastQuote, setLastQuote] = useState<QuoteUpdate | null>(null);
  const [lastAiChunk, setLastAiChunk] = useState<AiAnalysisChunk | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) {
      setConnected(false);
      return;
    }

    let socket: Socket | null = null;
    try {
      socket = io({
        path: "/socket.io",
        transports: ["websocket", "polling"],
        withCredentials: true,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Socket 初始化失败");
      return;
    }

    socket.on("connect", () => {
      setConnected(true);
      setError(null);
      socket?.emit("subscribe", { room: "alerts" });
      socket?.emit("subscribe", { room: "ai_analysis" });
    });

    socket.on("disconnect", () => {
      setConnected(false);
    });

    socket.on("connect_error", (err) => {
      setError(err.message);
      setConnected(false);
    });

    socket.on("quote_update", (payload: QuoteUpdate) => {
      setLastQuote(payload);
    });

    socket.on("ai_analysis_chunk", (payload: AiAnalysisChunk) => {
      setLastAiChunk(payload);
    });

    return () => {
      socket?.disconnect();
    };
  }, [enabled]);

  return { connected, lastQuote, lastAiChunk, error };
}
