import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import { DEMO_TDX_BLOCKS, DEMO_TDX_MEMBERS } from "../lib/demoCatalog";

type TdxBlock = {
  block_code?: string;
  block_name?: string;
  name?: string;
  sector_code?: string;
  kind?: string;
  block_kind?: string;
  change_pct?: number;
  rise_ratio?: number;
  leader_name?: string;
  leader_change_pct?: number;
  stock_count?: number;
  member_count?: number;
  total_amount?: number;
};

type TdxBlockMember = {
  symbol: string;
  name?: string;
  price?: number;
  change_pct?: number;
};

const KIND_OPTIONS = [
  { value: "gn", label: "概念 (gn)" },
  { value: "fg", label: "风格/行业 (fg)" },
  { value: "zs", label: "指数 (zs)" },
] as const;

function fmtPct(v?: number | null): string {
  if (v == null || Number.isNaN(v)) return "--";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function pctClass(v?: number | null): string {
  if (v == null) return "";
  return v > 0 ? "text-emerald-600" : v < 0 ? "text-rose-600" : "";
}

function blockKey(b: TdxBlock): string {
  return b.sector_code || b.block_code || `${b.block_kind || b.kind || ""}:${b.block_name || b.name || ""}`;
}

function blockLabel(b: TdxBlock): string {
  return b.block_name || b.name || blockKey(b);
}

function unwrapItems<T>(payload: unknown): T[] {
  if (!payload || typeof payload !== "object") return [];
  const p = payload as Record<string, unknown>;
  if (Array.isArray(p.items)) return p.items as T[];
  if (Array.isArray(p.data)) return p.data as T[];
  const nested = p.data;
  if (nested && typeof nested === "object" && Array.isArray((nested as { items?: unknown }).items)) {
    return (nested as { items: T[] }).items;
  }
  return [];
}

export function TdxBlocksPage() {
  const [blockKind, setBlockKind] = useState<(typeof KIND_OPTIONS)[number]["value"]>("gn");
  const [activeBlock, setActiveBlock] = useState<{ kind: string; name: string; key: string } | null>(null);

  const { data: blocksData, error, isLoading } = useSWR(
    ["tdx-block-summaries", blockKind],
    () => apiFetchV1(`/tdx/blocks/summaries?kind=${encodeURIComponent(blockKind)}&limit=100`),
    { refreshInterval: 300_000, shouldRetryOnError: false },
  );

  const { data: membersData, isLoading: membersLoading } = useSWR(
    activeBlock ? ["tdx-members", activeBlock.kind, activeBlock.name] : null,
    () =>
      apiFetchV1(
        `/tdx/blocks/${encodeURIComponent(activeBlock!.kind)}/${encodeURIComponent(activeBlock!.name)}/members?with_quotes=1&limit=60`,
      ),
    { shouldRetryOnError: false },
  );

  const liveBlocks = unwrapItems<TdxBlock>(blocksData);
  const isDemo = Boolean(error) || (!isLoading && !liveBlocks.length);
  const blocks = isDemo ? DEMO_TDX_BLOCKS : liveBlocks;
  const liveMembers = unwrapItems<TdxBlockMember>(membersData);
  const members =
    !membersLoading && activeBlock && !liveMembers.length && isDemo ? DEMO_TDX_MEMBERS : liveMembers;

  useEffect(() => {
    if (!activeBlock && blocks.length) {
      const first = blocks[0];
      const kind = first.block_kind || first.kind || blockKind;
      const name = first.block_name || first.name || "";
      if (name) setActiveBlock({ kind, name, key: blockKey(first) });
    }
  }, [blocks, activeBlock, blockKind]);

  useEffect(() => {
    setActiveBlock(null);
  }, [blockKind]);

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.tdxBlocks} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">通达信板块</h1>
          <p className="text-sm text-slate-500">板块 ↔ 成分股双向浏览（对齐后端 kind=zs/gn/fg）</p>
          <DemoBanner show={isDemo} />
        </div>
        <select
          className="select select-bordered select-sm"
          value={blockKind}
          onChange={(e) => setBlockKind(e.target.value as typeof blockKind)}
        >
          {KIND_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="alert alert-error">{error.message}</div>}
      {isLoading && <PageSkeleton rows={3} />}

      {!isLoading && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <section className="glass-card overflow-x-auto p-4">
            <table className="table w-full">
              <thead>
                <tr>
                  <th>#</th>
                  <th>板块名称</th>
                  <th>涨幅</th>
                  <th>涨股比</th>
                  <th>龙头</th>
                  <th>龙头涨幅</th>
                  <th>个股数</th>
                </tr>
              </thead>
              <tbody>
                {blocks.map((b: TdxBlock, i: number) => {
                  const kind = b.block_kind || b.kind || blockKind;
                  const name = b.block_name || b.name || "";
                  const key = blockKey(b);
                  return (
                    <tr
                      key={key}
                      className={`cursor-pointer ${activeBlock?.key === key ? "bg-base-200" : ""} hover:bg-base-200`}
                      onClick={() => name && setActiveBlock({ kind, name, key })}
                    >
                      <td className="text-slate-400">{i + 1}</td>
                      <td className="font-semibold">{blockLabel(b)}</td>
                      <td className={pctClass(b.change_pct)}>{fmtPct(b.change_pct)}</td>
                      <td>{b.rise_ratio != null ? `${(b.rise_ratio * 100).toFixed(0)}%` : "--"}</td>
                      <td>{b.leader_name ?? "--"}</td>
                      <td className={pctClass(b.leader_change_pct)}>{fmtPct(b.leader_change_pct)}</td>
                      <td>{b.member_count ?? b.stock_count ?? "--"}</td>
                    </tr>
                  );
                })}
                {!blocks.length && (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500">
                      暂无板块数据
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </section>

          <section className="glass-card overflow-x-auto p-4">
            {!activeBlock && (
              <div className="flex h-40 items-center justify-center text-sm text-slate-500">请选择左侧板块</div>
            )}
            {membersLoading && (
              <div className="flex h-40 items-center justify-center text-sm text-slate-500">加载成分…</div>
            )}
            {activeBlock && !membersLoading && (
              <>
                <div className="mb-2 text-sm font-semibold text-zinc-200">
                  {activeBlock.name}
                  <span className="ml-2 font-mono text-[11px] text-zinc-500">{activeBlock.kind}</span>
                </div>
                <table className="table w-full">
                  <thead>
                    <tr>
                      <th>代码</th>
                      <th>名称</th>
                      <th>现价</th>
                      <th>涨跌</th>
                    </tr>
                  </thead>
                  <tbody>
                    {members.map((m) => (
                      <tr key={m.symbol}>
                        <td>
                          <Link className="font-mono text-emerald-500" to={`/stock/${encodeURIComponent(m.symbol)}?m=CN`}>
                            {m.symbol}
                          </Link>
                        </td>
                        <td>{m.name ?? "--"}</td>
                        <td className="font-mono">{m.price ?? "--"}</td>
                        <td className={pctClass(m.change_pct)}>{fmtPct(m.change_pct)}</td>
                      </tr>
                    ))}
                    {!members.length && (
                      <tr>
                        <td colSpan={4} className="py-6 text-center text-slate-500">
                          暂无成分股
                        </td>
                      </tr>
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
