import { useState, useCallback } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import type { HotSector, HotSectorMember, HotSectorSnapshot, HotSectorResponse } from "../types/hotSector";

/* ── API Helpers ── */
function fetchSectors(kind: string, source: string, snapshotAt: string): Promise<{ data: HotSectorResponse }> {
  let url = `/hot-sectors?limit=60&kind=${encodeURIComponent(kind)}&source=${encodeURIComponent(source)}`;
  if (snapshotAt) url += `&snapshot_at=${encodeURIComponent(snapshotAt)}`;
  return apiFetchV1(url);
}

function fetchMembers(sectorCode: string, boardKind: string, name: string, provider: string, snapshotAt: string): Promise<{ data: { items: HotSectorMember[] } }> {
  let url = `/hot-sectors/${encodeURIComponent(sectorCode)}/members?limit=80&source=auto&board_kind=${encodeURIComponent(boardKind)}&name=${encodeURIComponent(name)}&provider=${encodeURIComponent(provider)}`;
  if (snapshotAt) url += `&snapshot_at=${encodeURIComponent(snapshotAt)}`;
  return apiFetchV1(url);
}

function fetchSnapshots(): Promise<{ items: HotSectorSnapshot[] }> {
  return apiFetchV1("/hot-sectors/snapshots?limit=40");
}

function fetchQuotes(symbols: string[]): Promise<{ data?: Array<{ code?: string; price?: number; change_pct?: number; amount?: number; name?: string }>; stocks?: Array<{ code?: string; price?: number; change_pct?: number; amount?: number; name?: string }> }> {
  const params = symbols.map((s) => `symbol=${encodeURIComponent(s)}`).join("&");
  return apiFetchV1(`/markets/CN/quotes?${params}`);
}

/* ── Format helpers ── */
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
  if (v == null) return "";
  return v > 0 ? "text-emerald-600" : v < 0 ? "text-rose-600" : "";
}

const KIND_OPTIONS = [
  { value: "all", label: "全部数据源" },
  { value: "em", label: "东方财富" },
  { value: "ths", label: "同花顺（四类）" },
  { value: "csrc", label: "证监会行业（同花顺）" },
  { value: "kpl", label: "开盘啦" },
  { value: "xgt", label: "选股通概念" },
  { value: "concept", label: "概念（东财+THS+开盘啦+选股通）" },
  { value: "region", label: "地区（同花顺+开盘啦）" },
  { value: "industry", label: "行业" },
];

const SOURCE_OPTIONS = [
  { value: "auto", label: "自动（优先 MySQL）" },
  { value: "mysql", label: "仅 MySQL" },
  { value: "live", label: "实时拉取" },
];

export function HotSectorsPage() {
  const [kind, setKind] = useState("all");
  const [source, setSource] = useState("auto");
  const [snapshotAt, setSnapshotAt] = useState("");
  const [activeSector, setActiveSector] = useState<{ code: string; name: string; kind: string; provider: string } | null>(null);
  const [membersData, setMembersData] = useState<HotSectorMember[] | null>(null);
  const [membersLoading, setMembersLoading] = useState(false);

  /* ── SWR ── */
  const { data: sectorsResp, error, isLoading } = useSWR(
    ["hot-sectors", kind, source, snapshotAt],
    () => fetchSectors(kind, source, snapshotAt),
    { refreshInterval: 300_000 },
  );

  const { data: snapshotsResp } = useSWR(
    "hot-sectors/snapshots",
    () => fetchSnapshots(),
    { refreshInterval: 600_000 },
  );

  const sectors = sectorsResp?.data?.sectors ?? [];
  const warnings = sectorsResp?.data?.warnings ?? [];
  const csAt = sectorsResp?.data?.snapshot_at ?? "";
  const sourceMode = sectorsResp?.data?.source_mode ?? source;
  const _ts = csAt || sectorsResp?.data?.updated_at || "";

  /* ── Load members on sector click ── */
  const loadMembers = useCallback(async (sector: { code: string; name: string; kind: string; provider: string }) => {
    setActiveSector(sector);
    setMembersLoading(true);
    setMembersData(null);
    try {
      const resp = await fetchMembers(sector.code, sector.kind, sector.name, sector.provider, csAt);
      const items = resp?.data?.items ?? [];
      if (!items.length) {
        setMembersData([]);
        setMembersLoading(false);
        return;
      }
      // Fetch quotes for enriched price display
      const symbols = items.slice(0, 60).map((x: HotSectorMember) => x.symbol || "").filter(Boolean);
      const qResp = await fetchQuotes(symbols);
      const stocks = qResp?.data || qResp?.stocks || [];
      const quoteMap: Record<string, { price?: number; change_pct?: number; amount?: number; name?: string }> = {};
      for (const q of stocks) {
        if (q.code) quoteMap[q.code] = q;
      }
      const enriched = items.map((item: HotSectorMember) => {
        const q = quoteMap[item.symbol ?? ""] || {};
        return { ...item, price: q.price ?? item.price, change_pct: q.change_pct ?? item.change_pct, amount: q.amount ?? item.amount, name: q.name ?? item.name };
      });
      setMembersData(enriched);
    } catch {
      setMembersData([]);
    } finally {
      setMembersLoading(false);
    }
  }, [csAt]);

  return (
    <div className="space-y-5">
      {/* ── Header ── */}
      <div>
        <h1 className="text-2xl font-bold">热点板块</h1>
        <p className="text-sm text-slate-500">多源板块监控：东方财富、同花顺、开盘啦、选股通</p>
      </div>

      {/* ── Filter Bar ── */}
      <div className="glass-card flex flex-wrap items-center gap-3 p-4">
        <select className="select select-bordered select-sm" value={kind} onChange={(e) => setKind(e.target.value)}>
          {KIND_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select className="select select-bordered select-sm" value={source} onChange={(e) => setSource(e.target.value)}>
          {SOURCE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select className="select select-bordered select-sm flex-1 min-w-[160px]" value={snapshotAt} onChange={(e) => setSnapshotAt(e.target.value)}>
          <option value="">最新快照</option>
          {(snapshotsResp?.items ?? []).map((s: HotSectorSnapshot) => (
            <option key={s.snapshot_at} value={s.snapshot_at}>{s.snapshot_at} · {s.sector_count} 板块</option>
          ))}
        </select>
        <span className="text-xs text-slate-400">
          [{sourceMode}] {_ts || ""}
          {warnings.length ? ` · ⚠ ${warnings.join("; ")}` : ""}
        </span>
      </div>

      {/* ── Error ── */}
      {error && <div className="alert alert-error">加载失败：{error.message}</div>}

      {/* ── Loading ── */}
      {isLoading && <PageSkeleton rows={3} />}

      {/* ── Content ── */}
      {!isLoading && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Left: Sector List */}
          <section className="glass-card overflow-x-auto p-4">
            <table className="table w-full">
              <thead>
                <tr><th>#</th><th>板块</th><th>涨幅</th><th>涨股比</th><th>龙头</th><th>龙头涨幅</th><th>来源</th></tr>
              </thead>
              <tbody>
                {sectors.map((s: HotSector, idx: number) => (
                  <tr
                    key={s.sector_code ?? idx}
                    className={`cursor-pointer ${activeSector?.code === s.sector_code ? "bg-base-200" : ""} hover:bg-base-200`}
                    onClick={() => loadMembers({ code: s.sector_code, name: s.name, kind: s.kind ?? "concept", provider: s.provider ?? "" })}
                  >
                    <td className="text-slate-400">{idx + 1}</td>
                    <td className="font-semibold">{s.name}</td>
                    <td className={pctClass(s.change_pct)}>{fmtPct(s.change_pct)}</td>
                    <td>{fmtRiseRatio(s.rise_ratio)}</td>
                    <td>{s.leader_name ?? "--"}</td>
                    <td className={pctClass(s.leader_change_pct)}>{fmtPct(s.leader_change_pct)}</td>
                    <td><span className="badge badge-ghost text-xs">{s.source ?? ""}</span></td>
                  </tr>
                ))}
                {!sectors.length && (
                  <tr><td colSpan={7} className="py-12 text-center text-slate-500">暂无板块数据</td></tr>
                )}
              </tbody>
            </table>
          </section>

          {/* Right: Members */}
          <section className="glass-card overflow-x-auto p-4">
            {!activeSector && (
              <div className="flex h-40 items-center justify-center text-sm text-slate-500">请选择左侧板块查看成分股</div>
            )}
            {membersLoading && (
              <div className="flex h-40 items-center justify-center text-sm text-slate-500">加载成分股行情中...</div>
            )}
            {!membersLoading && membersData && (
              <>
                <div className="mb-3">
                  <h3 className="text-sm font-bold">成分股 · {activeSector?.name ?? ""}</h3>
                  <p className="text-xs text-slate-500">共 {membersData.length} 只</p>
                </div>
                <table className="table w-full">
                  <thead>
                    <tr><th>代码</th><th>名称</th><th>价格</th><th>涨跌幅</th><th>成交额</th></tr>
                  </thead>
                  <tbody>
                    {membersData.slice(0, 80).map((m: HotSectorMember) => (
                      <tr key={m.symbol}>
                        <td><code>{m.symbol}</code></td>
                        <td className="font-medium">{m.name}{m.is_leader ? " ★" : ""}</td>
                        <td>{m.price != null ? `¥${m.price.toFixed(2)}` : "--"}</td>
                        <td className={pctClass(m.change_pct)}>{fmtPct(m.change_pct)}</td>
                        <td>{fmtAmount(m.amount)}</td>
                      </tr>
                    ))}
                    {!membersData.length && (
                      <tr><td colSpan={5} className="py-8 text-center text-slate-500">暂无成分股</td></tr>
                    )}
                  </tbody>
                </table>
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}