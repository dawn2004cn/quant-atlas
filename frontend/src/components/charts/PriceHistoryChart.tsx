import { useEffect, useRef, memo, useMemo } from "react";
import type { BarPoint } from "../../types/stock";

type ChartInstance = {
  remove(): void;
  addCandlestickSeries(options?: any): { setData(data: any[]): void };
  addHistogramSeries(options?: any): { setData(data: any[]): void };
  addLineSeries(options?: any): { setData(data: any[]): void };
  priceScale(id: string): { applyOptions(options: any): void };
  timeScale(): { fitContent(): void };
  applyOptions(options: any): void;
};

function createChart(container: HTMLElement, options: any): ChartInstance {
  const lib = (window as any).LightweightCharts;
  if (!lib) {
    container.innerHTML = '<p class="text-sm text-[var(--tone-danger)]">LightweightCharts 库未加载。</p>';
    return {
      remove() {},
      addCandlestickSeries() { return { setData() {} }; },
      addHistogramSeries() { return { setData() {} }; },
      addLineSeries() { return { setData() {} }; },
      priceScale() { return { applyOptions() {} }; },
      timeScale() { return { fitContent() {} }; },
      applyOptions() {},
    };
  }
  return lib.createChart(container, options);
}

function sma(closes: number[], period: number): Array<number | null> {
  const out: Array<number | null> = [];
  let sum = 0;
  for (let i = 0; i < closes.length; i++) {
    sum += closes[i];
    if (i >= period) sum -= closes[i - period];
    out.push(i >= period - 1 ? sum / period : null);
  }
  return out;
}

export type ChartOverlay = "ma5" | "ma20" | "volume";

type Props = {
  data: BarPoint[];
  overlays?: ChartOverlay[];
};

export const PriceHistoryChart = memo(function PriceHistoryChart({
  data,
  overlays = ["ma5", "ma20", "volume"],
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ChartInstance | null>(null);
  const overlayKey = useMemo(() => overlays.slice().sort().join(","), [overlays]);

  useEffect(() => {
    return () => {
      chartRef.current?.remove();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!containerRef.current || !data.length) return;

    chartRef.current?.remove();
    chartRef.current = null;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 320,
      layout: { background: { type: "solid", color: "transparent" }, textColor: "#94a3b8" },
      grid: { vertLines: { color: "#1e293b" }, horzLines: { color: "#1e293b" } },
      rightPriceScale: { borderColor: "#334155" },
      timeScale: { borderColor: "#334155", timeVisible: false },
    });
    chartRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderUpColor: "#22c55e",
      borderDownColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });
    candleSeries.setData(
      data.map((p) => ({
        time: p.date.slice(0, 10) as any,
        open: p.open,
        high: p.high,
        low: p.low,
        close: p.close,
      })),
    );

    const closes = data.map((p) => p.close);
    if (overlays.includes("ma5")) {
      const ma5 = sma(closes, 5);
      const line = chart.addLineSeries({ color: "#38bdf8", lineWidth: 2, title: "MA5" });
      line.setData(
        data
          .map((p, i) => (ma5[i] == null ? null : { time: p.date.slice(0, 10) as any, value: ma5[i] as number }))
          .filter(Boolean) as any[],
      );
    }
    if (overlays.includes("ma20")) {
      const ma20 = sma(closes, 20);
      const line = chart.addLineSeries({ color: "#fbbf24", lineWidth: 2, title: "MA20" });
      line.setData(
        data
          .map((p, i) => (ma20[i] == null ? null : { time: p.date.slice(0, 10) as any, value: ma20[i] as number }))
          .filter(Boolean) as any[],
      );
    }

    if (overlays.includes("volume")) {
      const volSeries = chart.addHistogramSeries({
        priceFormat: { type: "volume" },
        priceScaleId: "volume",
      });
      chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });
      volSeries.setData(
        data.map((p) => ({
          time: p.date.slice(0, 10) as any,
          value: p.volume,
          color: p.close >= p.open ? "#22c55e44" : "#ef444444",
        })),
      );
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      if (chartRef.current === chart) chartRef.current = null;
    };
  }, [data, overlayKey, overlays]);

  if (!data.length) {
    return <p className="text-sm text-[var(--quant-muted)]">暂无 K 线数据。</p>;
  }

  return <div ref={containerRef} className="h-80 w-full" />;
});
