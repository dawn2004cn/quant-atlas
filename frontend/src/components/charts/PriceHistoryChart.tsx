import { useEffect, useRef, memo } from "react";
import type { BarPoint } from "../../types/stock";

type ChartInstance = {
  remove(): void;
  addCandlestickSeries(options?: any): { setData(data: any[]): void };
  addHistogramSeries(options?: any): { setData(data: any[]): void };
  priceScale(id: string): { applyOptions(options: any): void };
  timeScale(): { fitContent(): void };
  applyOptions(options: any): void;
};

function createChart(container: HTMLElement, options: any): ChartInstance {
  const lib = (window as any).LightweightCharts;
  if (!lib) {
    container.innerHTML = '<p class="text-sm text-red-500">LightweightCharts 库未加载。</p>';
    return { remove() {}, addCandlestickSeries() { return { setData() {} }; }, addHistogramSeries() { return { setData() {} }; }, priceScale() { return { applyOptions() {} }; }, timeScale() { return { fitContent() {} }; }, applyOptions() {} };
  }
  return lib.createChart(container, options);
}

type Props = {
  data: BarPoint[];
};

export const PriceHistoryChart = memo(function PriceHistoryChart({ data }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ChartInstance | null>(null);

  useEffect(() => {
    return () => {
      chartRef.current?.remove();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!containerRef.current || !data.length) return;

    const chart = chartRef.current ?? createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 320,
      layout: { background: { type: "solid", color: "transparent" }, textColor: "#94a3b8" },
      grid: { vertLines: { color: "#1e293b" }, horzLines: { color: "#1e293b" } },
      rightPriceScale: { borderColor: "#334155" },
      timeScale: { borderColor: "#334155", timeVisible: false },
    });
    chartRef.current = chart;

    // Candlestick series (K-line)
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
      }))
    );

    // Volume histogram (bottom pane)
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
      }))
    );

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [data]);

  if (!data.length) {
    return <p className="text-sm text-slate-500">暂无 K 线数据。</p>;
  }

  return <div ref={containerRef} className="h-80 w-full" />;
});