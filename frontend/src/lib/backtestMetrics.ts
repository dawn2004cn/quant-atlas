import type { EquityPoint, TradeMarker } from "../types/backtest";

function normalizeDate(raw: unknown): string {
  const s = String(raw ?? "").trim();
  if (!s) return "";
  return s.length >= 10 ? s.slice(0, 10) : s;
}

function normalizeSide(raw: unknown): "buy" | "sell" | null {
  const s = String(raw ?? "").trim().toLowerCase();
  if (s === "buy" || s === "b") return "buy";
  if (s === "sell" || s === "s") return "sell";
  return null;
}

export function extractEquityCurve(result: Record<string, unknown>): EquityPoint[] {
  const metrics = result.metrics as Record<string, unknown> | undefined;
  const raw =
    result.equity_curve ??
    result.equity ??
    metrics?.equity_curve ??
    metrics?.equity;

  if (!Array.isArray(raw)) return [];

  return raw
    .map((point, index) => {
      if (!point || typeof point !== "object") return null;
      const row = point as Record<string, unknown>;
      const date = String(row.date ?? row.dt ?? row.time ?? index);
      const value = Number(row.value ?? row.equity ?? row.nav ?? row.close);
      if (!date || Number.isNaN(value)) return null;
      return { date: normalizeDate(date), value };
    })
    .filter((p): p is EquityPoint => p !== null);
}

export function extractTrades(result: Record<string, unknown>): TradeMarker[] {
  const metrics = result.metrics as Record<string, unknown> | undefined;
  const raw = result.trades ?? metrics?.trades;
  if (!Array.isArray(raw)) return [];

  return raw
    .map((row): TradeMarker | null => {
      if (!row || typeof row !== "object") return null;
      const item = row as Record<string, unknown>;
      const side = normalizeSide(item.action ?? item.type ?? item.side);
      const price = Number(item.price);
      const date = normalizeDate(item.date ?? item.trade_date);
      if (!side || !date || Number.isNaN(price)) return null;
      const quantityRaw = Number(item.quantity ?? item.qty ?? item.shares);
      const pnlRaw = item.profit ?? item.pnl;
      const marker: TradeMarker = {
        date,
        price,
        side,
      };
      if (!Number.isNaN(quantityRaw)) marker.quantity = quantityRaw;
      if (pnlRaw != null && pnlRaw !== "") {
        const pnl = Number(pnlRaw);
        if (!Number.isNaN(pnl)) marker.pnl = pnl;
      }
      return marker;
    })
    .filter((t): t is TradeMarker => t !== null);
}

export function formatPercentMetric(value: unknown): string | null {
  if (value == null || value === "") return null;
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  const pct = Math.abs(n) <= 1 ? n * 100 : n;
  return `${pct.toFixed(2)}%`;
}

export function formatDrawdownMetric(value: unknown, alt?: unknown): string | null {
  const raw = value ?? alt;
  if (raw == null || raw === "") return null;
  const n = Number(raw);
  if (Number.isNaN(n)) return String(raw);
  if (n <= 0) {
    const pct = Math.abs(n) <= 1 ? Math.abs(n) * 100 : Math.abs(n);
    return `-${pct.toFixed(2)}%`;
  }
  return `-${n.toFixed(2)}%`;
}

export function extractMetricCards(result: Record<string, unknown>) {
  const metrics = (result.metrics as Record<string, unknown> | undefined) ?? {};
  const pick = (key: string, alt?: string) => {
    const v = result[key] ?? metrics[key] ?? (alt ? metrics[alt] : undefined);
    return v == null || v === "" ? null : v;
  };
  const totalReturn = pick("total_return", "total_return_pct");
  const maxDd = pick("max_drawdown_pct") ?? pick("max_drawdown", "max_drawdown_pct");
  const formatNum = (value: unknown) => {
    if (value == null || value === "") return null;
    const n = Number(value);
    return Number.isNaN(n) ? String(value) : n.toFixed(2);
  };
  return [
    { label: "总收益", value: formatPercentMetric(totalReturn) ?? totalReturn },
    { label: "夏普", value: pick("sharpe", "sharpe_ratio") },
    { label: "索提诺", value: formatNum(pick("sortino")) },
    { label: "卡玛", value: formatNum(pick("calmar")) },
    { label: "Omega", value: formatNum(pick("omega_ratio", "omega")) },
    { label: "CVaR 95", value: formatPercentMetric(pick("cvar_95")) },
    { label: "最大回撤", value: formatDrawdownMetric(maxDd) ?? maxDd },
    { label: "胜率", value: formatPercentMetric(pick("win_rate", "winrate")) ?? pick("win_rate", "winrate") },
  ].filter((row) => row.value != null);
}
