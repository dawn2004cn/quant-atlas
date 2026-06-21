import { useEffect, useRef, memo } from "react";
import type { EquityPoint, TradeMarker } from "../../types/backtest";

type ChartInstance = {
  remove(): void;
  addAreaSeries(options?: any): { setData(data: any[]): void };
  timeScale(): { fitContent(): void };
  applyOptions(options: any): void;
};

function createChart(container: HTMLElement, options: any): ChartInstance {
  const lib = (window as any).LightweightCharts;
  if (!lib) {
    container.innerHTML = '<p class="text-sm text-red-500">LightweightCharts 库未加载。</p>';
    return { remove() {}, addAreaSeries() { return { setData() {} }; }, timeScale() { return { fitContent() {} }; }, applyOptions() {} };
  }
  return lib.createChart(container, options);
}

type Props = {
  data: EquityPoint[];
  trades?: TradeMarker[];
};

export const EquityCurveChart = memo(function EquityCurveChart({ data, trades = [] }: Props) {
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
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: "#334155" },
      timeScale: { borderColor: "#334155", timeVisible: false },
    });
    chartRef.current = chart;

    const series = chart.addAreaSeries({
      lineColor: "#7c3aed",
      topColor: "rgba(124, 58, 237, 0.3)",
      bottomColor: "rgba(124, 58, 237, 0.01)",
      lineWidth: 2,
    });

    series.setData(
      data.map((p) => ({
        time: p.date.slice(0, 10) as any,
        value: p.value,
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
    return <p className="text-sm text-slate-500">暂无权益曲线数据。</p>;
  }

  return (
    <div>
      <div ref={containerRef} className="h-80 w-full" />
      {trades.length ? (
        <p className="mt-2 text-xs text-slate-500">
          <span className="mr-3 text-emerald-600">▲ 买入 {trades.filter((t) => t.side === "buy").length}</span>
          <span className="text-rose-600">▼ 卖出 {trades.filter((t) => t.side === "sell").length}</span>
        </p>
      ) : null}
    </div>
  );
});
