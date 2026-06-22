import { useState, useCallback } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import type { HotSector, HotSectorMember, HotSectorSnapshot } from "../types/hotSector";

/* ── API ── */
function fetchSectors(kind: string, source: string, snapshotAt: string) {
  let url = `/hot-sectors?limit=60&kind=${encodeURIComponent(kind)}&source=${encodeURIComponent(source)}`;
  if (snapshotAt) url += `&snapshot_at=${encodeURIComponent(snapshotAt)}`;
  return apiFetchV1<{ data: { sectors: HotSector[]; warnings?: string[]; snapshot_at?: string; source_mode?: string; updated_at?: string } }>(url);
}

function fetchMembers(sectorCode: string, boardKind: string, name: string, provider: string, snapshotAt: string) {
  let url = `/hot-sectors/${encodeURIComponent(sectorCode)}/members?limit=80&source=auto&board_kind=${encodeURIComponent(boardKind)}&name=${encodeURIComponent(name)}&provider=${encodeURIComponent(provider)}`;
  if (snapshotAt) url += `&snapshot_at=${encodeURIComponent(snapshotAt)}`;
  return apiFetchV1<{ data: { items: HotSectorMember[] } }>(url);
}

function fetchSnapshots() {
  return apiFetchV1<{ items: HotSectorSnapshot[] }>("/hot-sectors/snapshots?limit=40");
}

function fetchQuotes(symbols: string[]) {
  const params = symbols.map((s) => `symbol=${encodeURIComponent(s)}`).join("&");
  return apiFetchV1<{ data?: Array<{ code?: string; price?: number; change_pct?: number; amount?: number; name?: string }> }>(`/markets/CN/quotes?${params}`);
}

/* ── Helpers ── */
function fmtPct(v?: number | null): string {
  if (v == null || Number.isNaN(v)) return "--";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}
function fmtAmount(v?: number | null): string {
  const n = Number(v ?? 0);
  if (n >= 1e8) return `${(n / 1e8).toFixed(2)}亿`;
  if (n >= 1e4) return `${(n / 1e4).toFixed(2)}万`;
  return n.toFixed(0);
}
function fmtRiseRatio(v?: number | null): string {
  if (v == null || Number.isNaN(v)) return "--";
  return `${(v * 100).toFixed(0)}%`;
}
function pctClass(v?: number | null): string {
  if (v == null) return "text-zinc-400";
  return v > 0 ? "text-emerald-400" : v < 0 ? "text-rose-400" : "";
}

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 ${className}`}>{children}</div>;
}

const KIND_OPTIONS = [
  { value: "all", label: "全部数据源" },
  { value: "em", label: "东方财富" },
  { value: "ths", label: "同花顺（四类）" },
  { value: "csrc", label: "证监会行业" },
  { value: "kpl", label: "开盘啦" },
  { value: "xgt", label: "选股通概念" },
  { value: "concept", label: "概念" },
  { value: "region", label: "地区" },
  { value: "industry", label: "行业" },
];
const SOURCE_OPTIONS = [
  { value: "auto", label: "自动" },
  { value: "mysql", label: "MySQL" },
  { value: "live", label: "实时" },
];

export function HotSectorsPage() {
  const [kind, setKind] = useState("all");
  const [source, setSource] = useState("auto");
  const [snapshotAt, setSnapshotAt] = useState("");
  const [activeSector, setActiveSector] = useState<{ code: string; name: string; kind: string; provider: string } | null>(null);
  const [membersData, setMembersData] = useState<HotSectorMember[] | null>(null);
  const [membersLoading, setMembersLoading] = useState(false);

  const { data: sectorsResp, error, isLoading } = useSWR(
    ["hot-sectors", kind, source, snapshotAt],
    () => fetchSectors(kind, source, snapshotAt),
    { refreshInterval: 300_000 },
  );
  const { data: snapshotsResp } = useSWR("hot-sectors/snapshots", fetchSnapshots, { refreshInterval: 600_000 });

  const sectors = sectorsResp?.data?.sectors ?? [];
  const warnings = sectorsResp?.data?.warnings ?? [];
  const csAt = sectorsResp?.data?.snapshot_at ?? "";
  const sourceMode = sectorsResp?.data?.source_mode ?? source;
  const _ts = csAt || sectorsResp?.data?.updated_at || "";

  const loadMembers = useCallback(async (sector: { code: string; name: string; kind: string; provider: string }) => {
    setActiveSector(sector);
    setMembersLoading(true);
    setMembersData(null);
    try {
      const resp = await fetchMembers(sector.code, sector.kind, sector.name, sector.provider, csAt);
      const items = resp?.data?.items ?? [];
      if (!items.length) { setMembersData([]); setMembersLoading(false); return; }
      const symbols = items.slice(0, 60).map((x) => x.symbol || "").filter(Boolean);
      const qResp = await fetchQuotes(symbols);
      const stocks = qResp?.data ?? [];
      const quoteMap: Record<string, { price?: number; change_pct?: number; amount?: number; name?: string }> = {};
      for (const q of stocks) if (q.code) quoteMap[q.code] = q;
      setMembersData(items.map((item) => {
        const q = quoteMap[item.symbol ?? ""] || {};
        return { ...item, price: q.price ?? item.price, change_pct: q.change_pct ?? item.change_pct, amount: q.amount ?? item.amount, name: q.name ?? item.name };
      }));
    } catch { setMembersData([]); }
    finally { setMembersLoading(false); }
  }, [csAt]);

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      {/* Header */}
      <div>
        <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-zinc-500">Hot Sectors Monitor</div>
        <h1 className="mt-0.5 text-2xl font-bold tracking-tight text-zinc-100">热点板块</h1>
        <p className="mt-1 text-sm text-zinc-500">多源板块监控: 东方财富, 同花顺, 开盘啦, 选股通</p>
      </div>

      {/* Filter Bar */}
      <Panel className="flex flex-wrap items-center gap-3 p-4">
        <select className="rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-1.5 font-mono text-xs text-zinc-200" value={kind} onChange={(e) => setKind(e.target.value)}>
          {KIND_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select className="rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-1.5 font-mono text-xs text-zinc-200" value={source} onChange={(e) => setSource(e.target.value)}>
          {SOURCE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select className="rounded-lg border border-zinc-700/60 bg-zinc-800/60 px-3 py-1.5 font-mono text-xs text-zinc-200 flex-1 min-w-[160px]" value={snapshotAt} onChange={(e) => setSnapshotAt(e.target.value)}>
          <option value="">最新快照</option>
          {(snapshotsResp?.items ?? []).map((s) => (
            <option key={s.snapshot_at} value={s.snapshot_at}>{s.snapshot_at} · {s.sector_count} 板块</option>
          ))}
        </select>
        <span className="text-[10px] font-mono text-zinc-600">
          [{sourceMode}] {_ts || ""}
          {warnings.length ? ` ⚠ ${warnings.join("; ")}` : ""}
        </span>
      </Panel>

      {error && (
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-sm text-rose-400">
          加载失败: {error.message}
        </div>
      )}
      {isLoading && <PageSkeleton rows={3} />}

      {!isLoading && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Left: Sector List */}
          <Panel className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800/60 text-left text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">
                    <th className="px-4 py-3">#</th>
                    <th className="px-4 py-3">板块</th>
                    <th className="px-4 py-3 text-right">涨幅</th>
                    <th className="px-4 py-3 text-right">涨股比</th>
                    <th className="px-4 py-3">龙头</th>
                    <th className="px-4 py-3 text-right">龙头涨幅</th>
                    <th className="px-4 py-3">来源</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/30">
                  {sectors.map((s: HotSector, idx: number) => (
                    <tr
                      key={s.sector_code ?? idx}
                      onClick={() => loadMembers({ code: s.sector_code, name: s.name, kind: s.kind ?? "concept", provider: s.provider ?? "" })}
                      className={`cursor-pointer transition-colors ${
                        activeSector?.code === s.sector_code
                          ? "bg-emerald-500/8 ring-1 ring-inset ring-emerald-500/20"
                          : "hover:bg-zinc-800/30"
                      }`}
                    >
                      <td className="px-4 py-3 font-mono text-[10px] text-zinc-600">{idx + 1}</td>
                      <td className="px-4 py-3 font-semibold text-zinc-200">{s.name}</td>
                      <td className={`px-4 py-3 text-right font-mono tabular-nums font-semibold ${pctClass(s.change_pct)}`}>{fmtPct(s.change_pct)}</td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-300">{fmtRiseRatio(s.rise_ratio)}</td>
                      <td className="px-4 py-3 font-mono text-xs text-zinc-400">{s.leader_name ?? "--"}</td>
                      <td className={`px-4 py-3 text-right font-mono tabular-nums ${pctClass(s.leader_change_pct)}`}>{fmtPct(s.leader_change_pct)}</td>
                      <td className="px-4 py-3"><span className="rounded bg-zinc-800/60 px-1.5 py-0.5 font-mono text-[10px] text-zinc-500">{s.source ?? ""}</span></td>
                    </tr>
                  ))}
                  {!sectors.length && (
                    <tr><td colSpan={7} className="px-4 py-12 text-center text-sm text-zinc-600">暂无板块数据</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Panel>

          {/* Right: Members */}
          <Panel className="overflow-hidden">
            <div className="overflow-x-auto">
              {!activeSector && (
                <div className="flex h-40 items-center justify-center text-sm text-zinc-600">
                  请选择左侧板块查看成分股
                </div>
              )}
              {membersLoading && (
                <div className="flex h-40 items-center justify-center text-sm text-zinc-600">
                  加载成分股行情中...
                </div>
              )}
              {!membersLoading && membersData && (
                <>
                  <div className="border-b border-zinc-800/60 px-4 py-3">
                    <h3 className="text-sm font-semibold text-zinc-200">
                      成分股 · {activeSector?.name ?? ""}
                    </h3>
                    <p className="text-[10px] font-mono text-zinc-500">共 {membersData.length} 只</p>
                  </div>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-zinc-800/60 text-left text-[10px] font-mono uppercase tracking-[0.12em] text-zinc-500">
                        <th className="px-4 py-3">代码</th>
                        <th className="px-4 py-3">名称</th>
                        <th className="px-4 py-3 text-right">价格</th>
                        <th className="px-4 py-3 text-right">涨跌幅</th>
                        <th className="px-4 py-3 text-right">成交额</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-800/30">
                      {membersData.slice(0, 80).map((m) => (
                        <tr key={m.symbol} className="transition-colors hover:bg-zinc-800/30">
                          <td className="px-4 py-3 font-mono text-xs text-zinc-400">{m.symbol}</td>
                          <td className="px-4 py-3 font-medium text-zinc-200">{m.name}{m.is_leader ? " ★" : ""}</td>
                          <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-300">{m.price != null ? `¥${m.price.toFixed(2)}` : "--"}</td>
                          <td className={`px-4 py-3 text-right font-mono tabular-nums font-semibold ${pctClass(m.change_pct)}`}>{fmtPct(m.change_pct)}</td>
                          <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-400">{fmtAmount(m.amount)}</td>
                        </tr>
                      ))}
                      {!membersData.length && (
                        <tr><td colSpan={5} className="px-4 py-8 text-center text-sm text-zinc-600">暂无成分股</td></tr>
                      )}
                    </tbody>
                  </table>
                </>
              )}
            </div>
          </Panel>
        </div>
      )}
    </div>
  );
}