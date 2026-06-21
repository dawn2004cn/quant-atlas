import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import useSWR from "swr";
import { VirtualSignalTable } from "../components/virtual/VirtualSignalTable";
import { fetchSignalFlagPool, runSignalFlagScan } from "../lib/api";

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
    } catch (e: any) {
      setScanMsg("扫描失败: " + (e.message || ""));
    } finally {
      setScanning(false);
    }
  }, [date, mutate]);

  return (
    <div className="space-y-4">
      <section className="glass-card p-6">
        <div className="hero-caption">Signal Flag</div>
        <h1 className="text-2xl font-bold">信号旗</h1>
        <p className="text-sm text-slate-500 mt-1">
          全市场多策略信号扫描 — 最新 K 线上出现买/卖信号的策略均入池
        </p>
      </section>

      <section className="glass-card p-6 space-y-4">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="text-sm font-medium block mb-1">池日期</label>
            <input type="date" className="input input-bordered input-sm" value={date} onChange={(e) => { setDate(e.target.value); }} />
          </div>
          <button className="btn btn-primary btn-sm" onClick={() => mutate()}>加载该日股票池</button>
          <button className="btn btn-soft btn-sm" onClick={handleScan} disabled={scanning}>
            {scanning ? "扫描中…" : "运行该日扫描"}
          </button>
        </div>

        {scanMsg && <div className={"alert " + (scanMsg.includes("失败") ? "alert-error" : "alert-info") + " text-sm py-2"}>{scanMsg}</div>}
        {error && <div className="alert alert-error text-sm py-2">加载失败: {String(error)}</div>}

        {!items.length && !error && (
          <div className="text-sm text-slate-400 py-4 text-center">
            {data ? "该日无股票池数据，可先运行扫描" : "选择日期后点击「加载该日股票池」"}
          </div>
        )}

        {items.length > 0 && (
          <VirtualSignalTable
            items={items}
            total={items.length}
            onNavigate={(code) => navigate(`/stock/${encodeURIComponent(code)}`)}
            height={600}
          />
        )}
      </section>
    </div>
  );
}
