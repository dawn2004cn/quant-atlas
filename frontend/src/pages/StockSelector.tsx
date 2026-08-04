import { useRef, useState } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { CoreWorkflowStrip, PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { apiFetchV1 } from "../lib/api";

type StockRow = {
  code: string;
  name: string;
  price?: number;
  change_pct?: number;
  volume?: number;
  amount?: number;
  pe?: number;
  pb?: number;
  industry?: string;
  market_cap?: number;
  score?: number;
};

type SelectorResult = {
  results?: StockRow[];
  candidates?: StockRow[];
};

function fmtAmt(v?: number | null): string {
  const n = Number(v ?? 0);
  if (n >= 1e8) return `${(n / 1e8).toFixed(2)}亿`;
  if (n >= 1e4) return `${(n / 1e4).toFixed(2)}万`;
  return n.toFixed(0);
}

function pctClass(v?: number | null): string {
  if (v == null) return "";
  return v >= 0 ? "text-emerald-600" : "text-rose-600";
}

export function StockSelectorPage() {
  const [type, setType] = useState("long");
  const [topN, setTopN] = useState(20);
  const [horizon, setHorizon] = useState(20);
  const [dataSource, setDataSource] = useState("legacy");
  const [ran, setRan] = useState(false);
  const [running, setRunning] = useState(false);
  const inFlightRef = useRef(false);

  const { data, error, isLoading, mutate } = useSWR(
    ran ? ["selector-run", type, topN, dataSource, horizon] : null,
    async () => {
      if (inFlightRef.current) return undefined as unknown as SelectorResult;
      inFlightRef.current = true;
      setRunning(true);
      try {
        return await apiFetchV1<SelectorResult>("/selector/run", {
          method: "POST",
          body: JSON.stringify({ type, top_n: topN, data_source: dataSource, horizon_days: horizon, market: "CN" }),
        });
      } finally {
        inFlightRef.current = false;
        setRunning(false);
      }
    },
  );

  const items = data?.results ?? data?.candidates ?? [];

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.stockSelector} />
      <CoreWorkflowStrip />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">智能选股中心</h1>
          <p className="text-sm text-slate-500">短 / 中 / 长线多维度筛选</p>
        </div>
      </div>

      <div className="glass-card flex flex-wrap items-end gap-4 p-4">
        <div>
          <label className="text-xs font-semibold text-slate-500">周期</label>
          <select className="select select-bordered select-sm w-full" value={type} onChange={(e) => setType(e.target.value)}>
            <option value="short">短线</option>
            <option value="mid">中线</option>
            <option value="long">长线</option>
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-500">数量</label>
          <select className="select select-bordered select-sm w-full" value={topN} onChange={(e) => setTopN(Number(e.target.value))}>
            {[10, 20, 30, 50, 100].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-500">数据源</label>
          <select className="select select-bordered select-sm w-full" value={dataSource} onChange={(e) => setDataSource(e.target.value)}>
            <option value="legacy">传统</option>
            <option value="qlib">Qlib</option>
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-500">滚动期</label>
          <select className="select select-bordered select-sm w-full" value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
            <option value={5}>5天</option>
            <option value={10}>10天</option>
            <option value={20}>20天</option>
            <option value={60}>60天</option>
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-500">&nbsp;</label>
          <button type="button" className="btn btn-primary btn-sm w-full" disabled={running || isLoading || inFlightRef.current} onClick={() => { if (running || inFlightRef.current) return; setRan(true); void mutate(); }}>{running || isLoading ? "选股中…" : "开始选股"}</button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error.message}</div>}
      {isLoading && <PageSkeleton rows={3} />}

      {items.length > 0 && (
        <section className="glass-card overflow-x-auto p-4">
          <table className="table w-full">
            <thead>
              <tr><th>#</th><th>代码</th><th>名称</th><th>价格</th><th>涨跌幅</th><th>成交额</th><th>PE</th><th>行业</th></tr>
            </thead>
            <tbody>
              {items.map((r: StockRow, i: number) => (
                <tr key={r.code}>
                  <td className="text-slate-400">{i + 1}</td>
                  <td><code>{r.code}</code></td>
                  <td className="font-medium">{r.name}</td>
                  <td>{r.price != null ? `¥${r.price.toFixed(2)}` : "--"}</td>
                  <td className={pctClass(r.change_pct)}>{r.change_pct != null ? `${r.change_pct >= 0 ? "+" : ""}${r.change_pct.toFixed(2)}%` : "--"}</td>
                  <td className="text-xs">{fmtAmt(r.amount)}</td>
                  <td>{r.pe?.toFixed(2) ?? "--"}</td>
                  <td className="text-xs text-slate-500">{r.industry ?? "--"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}