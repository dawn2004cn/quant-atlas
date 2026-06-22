import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import useSWR from "swr";
import { VirtualSignalTable } from "../components/virtual/VirtualSignalTable";
import { fetchSignalFlagPool, runSignalFlagScan } from "../lib/api";

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 ${className}`}>{children}</div>;
}

export function SignalFlagPage() {
  const navigate = useNavigate();
  const today = new Date().toISOString().split("T")[0];
  const [date, setDate] = useState(today);
  const [scanning, setScanning] = useState(false);
  const [scanMsg, setScanMsg] = useState("");

  const { data, error, mutate } = useSWR(
    ["signal-flag", date],
    () => fetchSignalFlagPool(date),
    { revalidateOnFocus: false },
  );

  const items = data?.items ?? [];

  const handleScan = useCallback(async () => {
    setScanning(true);
    setScanMsg("扫描进行中…");
    try {
      const res = await runSignalFlagScan(date);
      setScanMsg(res.message || (res.mode === "async" ? "任务已提交，请到消息中心查看" : "扫描完成"));
      if (res.mode !== "async") mutate();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setScanMsg("扫描失败: " + msg);
    } finally {
      setScanning(false);
    }
  }, [date, mutate]);

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      {/* Header */}
      <div>
        <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-zinc-500">Signal Flag</div>
        <h1 className="mt-0.5 text-2xl font-bold tracking-tight text-zinc-100">信号旗</h1>
        <p className="mt-1 text-sm text-zinc-500">全市场多策略信号扫描 — 最新 K 线上出现买/卖信号的策略均入池</p>
      </div>

      {/* Controls */}
      <Panel className="p-5">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">池日期</label>
            <input type="date" className="rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-1.5 font-mono text-xs text-zinc-200 focus:border-emerald-500/40 focus:outline-none focus:ring-1 focus:ring-emerald-500/20" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <button className="rounded-lg bg-emerald-500/15 px-4 py-1.5 text-xs font-semibold text-emerald-400 ring-1 ring-emerald-500/30 transition-colors hover:bg-emerald-500/20" onClick={() => mutate()}>加载该日股票池</button>
          <button className="rounded-lg bg-zinc-800/60 px-4 py-1.5 text-xs font-medium text-zinc-400 ring-1 ring-zinc-700/40 transition-colors hover:bg-zinc-800 hover:text-zinc-200 disabled:opacity-50" onClick={handleScan} disabled={scanning}>
            {scanning ? "扫描中…" : "运行该日扫描"}
          </button>
        </div>

        {scanMsg && (
          <div className={`mt-3 rounded-xl border px-3 py-2 text-xs ${
            scanMsg.includes("失败")
              ? "border-rose-500/20 bg-rose-500/5 text-rose-400"
              : "border-sky-500/20 bg-sky-500/5 text-sky-400"
          }`}>{scanMsg}</div>
        )}
        {error && (
          <div className="mt-3 rounded-xl border border-rose-500/20 bg-rose-500/5 px-3 py-2 text-xs text-rose-400">
            加载失败: {String(error)}
          </div>
        )}

        {!items.length && !error && (
          <div className="py-8 text-center text-sm text-zinc-600">
            {data ? "该日无股票池数据，可先运行扫描" : "选择日期后点击「加载该日股票池」"}
          </div>
        )}

        {items.length > 0 && (
          <div className="mt-4">
            <VirtualSignalTable
              items={items}
              total={items.length}
              onNavigate={(code) => navigate(`/stock/${encodeURIComponent(code)}`)}
              height={600}
            />
          </div>
        )}
      </Panel>
    </div>
  );
}