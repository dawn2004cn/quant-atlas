import { useEffect, useRef, useState, useCallback } from 'react';
import { io, type Socket } from 'socket.io-client';

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

export type GatewayStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

type GatewayMessage = {
  type: string;
  symbol?: string;
  payload?: Record<string, unknown>;
  ts?: number;
};

const GATEWAY_URL = "ws://localhost:9091/ws";
const RECONNECT_BASE_DELAY = 1000;
const RECONNECT_MAX_DELAY = 30000;

export function useRealtime(enabled: boolean) {
  const [connected, setConnected] = useState(false);
  const [gatewayStatus, setGatewayStatus] = useState<GatewayStatus>('disconnected');
  const [lastQuote, setLastQuote] = useState<QuoteUpdate | null>(null);
  const [lastAiChunk, setLastAiChunk] = useState<AiAnalysisChunk | null>(null);
  const [error, setError] = useState<string | null>(null);

  const subscribedSymbols = useRef<Set<string>>(new Set());
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connectGateway = useCallback(() => {
    if (!enabled) return;
    setGatewayStatus('connecting');

    let ws: WebSocket;
    try {
      ws = new WebSocket(GATEWAY_URL);
    } catch (err) {
      setGatewayStatus('error');
      const msg = err instanceof Error ? err.message : 'WS init failed';
      setError(msg);
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      setGatewayStatus('connected');
      setError(null);

      const symbols = Array.from(subscribedSymbols.current);
      if (symbols.length > 0) {
        ws.send(JSON.stringify({
          type: 'subscribe',
          payload: { symbols },
        }));
      }
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const msg: GatewayMessage = JSON.parse(event.data);
        if (msg.type === 'quote' && msg.symbol) {
          const quote: QuoteUpdate = {
            symbol: msg.symbol,
            ...(msg.payload as Record<string, unknown>),
          } as QuoteUpdate;
          if (msg.payload?.price !== undefined) quote.price = msg.payload.price as number;
          if (msg.payload?.change_pct !== undefined) quote.change_pct = msg.payload.change_pct as number;
          setLastQuote(quote);
        }
      } catch {
      }
    };

    ws.onclose = () => {
      setGatewayStatus('disconnected');
      wsRef.current = null;
      scheduleReconnect();
    };

    ws.onerror = () => {
      setGatewayStatus('error');
    };

    wsRef.current = ws;
  }, [enabled]);

  const scheduleReconnect = useCallback(() => {
    if (!enabled) return;
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    const delay = Math.min(
      RECONNECT_BASE_DELAY * Math.pow(2, Math.random() * 3),
      RECONNECT_MAX_DELAY
    );
    reconnectTimer.current = setTimeout(() => {
      connectGateway();
    }, delay);
  }, [enabled, connectGateway]);

  const subscribe = useCallback((symbols: string[]) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      for (const s of symbols) subscribedSymbols.current.add(s.toUpperCase());
      return;
    }
    for (const s of symbols) subscribedSymbols.current.add(s.toUpperCase());
    ws.send(JSON.stringify({
      type: 'subscribe',
      payload: { symbols: symbols.map((s) => s.toUpperCase()) },
    }));
  }, []);

  const unsubscribe = useCallback((symbols: string[]) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      for (const s of symbols) subscribedSymbols.current.delete(s.toUpperCase());
      return;
    }
    for (const s of symbols) subscribedSymbols.current.delete(s.toUpperCase());
    ws.send(JSON.stringify({
      type: 'unsubscribe',
      payload: { symbols: symbols.map((s) => s.toUpperCase()) },
    }));
  }, []);

  useEffect(() => {
    if (!enabled) {
      setConnected(false);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
      subscribedSymbols.current.clear();
      return;
    }

    let socket: Socket | null = null;
    try {
      socket = io({
        path: '/socket.io',
        transports: ['websocket', 'polling'],
        withCredentials: true,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Socket init failed');
      return;
    }

    socket.on('connect', () => {
      setConnected(true);
      setError(null);
      socket?.emit('subscribe', { room: 'alerts' });
      socket?.emit('subscribe', { room: 'ai_analysis' });
    });

    socket.on('disconnect', () => {
      setConnected(false);
    });

    socket.on('connect_error', (err) => {
      setError(err.message);
      setConnected(false);
    });

    socket.on('quote_update', (payload: QuoteUpdate) => {
      setLastQuote(payload);
    });

    socket.on('ai_analysis_chunk', (payload: AiAnalysisChunk) => {
      setLastAiChunk(payload);
    });

    connectGateway();

    return () => {
      socket?.disconnect();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
    };
  }, [enabled, connectGateway]);

  return {
    connected,
    gatewayStatus,
    lastQuote,
    lastAiChunk,
    error,
    subscribe,
    unsubscribe,
  };
}
