import { useCallback, useEffect, useRef, useState } from "react";
import type { AnalysisChunk } from "../types/mlflow";

export function useAnalysisStream(symbol: string, market: string) {
  const [steps, setSteps] = useState<AnalysisChunk[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sourceRef = useRef<EventSource | null>(null);

  const stop = useCallback(() => {
    sourceRef.current?.close();
    sourceRef.current = null;
    setLoading(false);
  }, []);

  const start = useCallback(() => {
    if (!symbol) return;
    stop();
    setSteps([]);
    setError(null);
    setLoading(true);

    const query = new URLSearchParams({ symbol, market });
    const es = new EventSource(`/api/v1/ai/analyze/stream?${query}`);
    sourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const chunk = JSON.parse(event.data) as AnalysisChunk;
        setSteps((prev) => [...prev, chunk]);
        if (chunk.event === "complete") {
          stop();
        }
      } catch {
        setError("解析 AI 流式响应失败");
        stop();
      }
    };

    es.onerror = () => {
      setError("AI 分析流中断或需要登录");
      stop();
    };
  }, [market, symbol, stop]);

  useEffect(() => () => stop(), [stop]);

  return { steps, loading, error, start, stop };
}
