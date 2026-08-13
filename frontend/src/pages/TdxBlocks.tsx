import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import { DEMO_TDX_BLOCKS, DEMO_TDX_MEMBERS } from "../lib/demoCatalog";

type TdxBlock = {
  block_code: string;
  block_name: string;
  change_pct?: number;
  rise_ratio?: number;
  leader_name?: string;
  leader_change_pct?: number;
  stock_count?: number;
  total_amount?: number;
};

type TdxBlockMember = {
  symbol: string;
  name?: string;
  price?: number;
  change_pct?: number;
};

function fmtPct(v?: number | null): string {
  if (v == null || Number.isNaN(v)) return "--";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function pctClass(v?: number | null): string {
  if (v == null) return "";
  return v > 0 ? "text-emerald-600" : v < 0 ? "text-rose-600" : "";
}

export function TdxBlocksPage() {
  const [blockType, setBlockType] = useState("concept");
  const [activeBlock, setActiveBlock] = useState<{ code: string; name: string } | null>(null);

  const { data: blocksData, error, isLoading } = useSWR(
    ["tdx-blocks", blockType],
    () => apiFetchV1<{ data: { items: TdxBlock[] } }>(`/tdx/blocks?type=${encodeURIComponent(blockType)}&limit=100`),
    { refreshInterval: 300_000 },
  );

  const { data: membersData, isLoading: membersLoading } = useSWR(
    activeBlock ? ["tdx-members", activeBlock.code] : null,
    () => apiFetchV1<{ data: { items: TdxBlockMember[] } }>(`/tdx/blocks/${encodeURIComponent(activeBlock!.code)}/members?limit=60`),
  );

  const liveBlocks = blocksData?.data?.items ?? [];
  const isDemo = Boolean(error) || (!isLoading && !liveBlocks.length);
  const blocks = isDemo ? DEMO_TDX_BLOCKS : liveBlocks;
  const liveMembers = membersData?.data?.items ?? [];
  const members = (!membersLoading && activeBlock && !liveMembers.length) ? DEMO_TDX_MEMBERS : liveMembers;

  useEffect(() => {
    if (!activeBlock && blocks.length) {
      setActiveBlock({ code: blocks[0].block_code, name: blocks[0].block_name });
    }
  }, [blocks, activeBlock]);

  return (
    <div className="space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.tdxBlocks} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">通达信板块</h1>
          <p className="text-sm text-slate-500">通达信概念/行业/地区板块监控</p>
          <DemoBanner show={isDemo} />
        </div>
        <select className="select select-bordered select-sm" value={blockType} onChange={(e) => setBlockType(e.target.value)}>
          <option value="concept">概念板块</option>
          <option value="industry">行业板块</option>
          <option value="region">地区板块</option>
        </select>
      </div>

      {error && <div className="alert alert-error">{error.message}</div>}
      {isLoading && <PageSkeleton rows={3} />}

      {!isLoading && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Block List */}
          <section className="glass-card overflow-x-auto p-4">
            <table className="table w-full">
              <thead>
                <tr><th>#</th><th>板块名称</th><th>涨幅</th><th>涨股比</th><th>龙头</th><th>龙头涨幅</th><th>个股数</th></tr>
              </thead>
              <tbody>
                {blocks.map((b: TdxBlock, i: number) => (
                  <tr
                    key={b.block_code}
                    className={`cursor-pointer ${activeBlock?.code === b.block_code ? "bg-base-200" : ""} hover:bg-base-200`}
                    onClick={() => setActiveBlock({ code: b.block_code, name: b.block_name })}
                  >
                    <td className="text-slate-400">{i + 1}</td>
                    <td className="font-semibold">{b.block_name}</td>
                    <td className={pctClass(b.change_pct)}>{fmtPct(b.change_pct)}</td>
                    <td>{b.rise_ratio != null ? `${(b.rise_ratio * 100).toFixed(0)}%` : "--"}</td>
                    <td>{b.leader_name ?? "--"}</td>
                    <td className={pctClass(b.leader_change_pct)}>{fmtPct(b.leader_change_pct)}</td>
                    <td>{b.stock_count ?? "--"}</td>
                  </tr>
                ))}
                {!blocks.length && (
                  <tr><td colSpan={7} className="py-8 text-center text-slate-500">暂无板块数据</td></tr>
                )}
              </tbody>
            </table>
          </section>

          {/* Members */}
          <section className="glass-card overflow-x-auto p-4">
            {!activeBlock && (
              <div className="flex h-40 items-center justify-center text-sm text-slate-500">请选择左侧板块</div>
            )}
            {membersLoading && (
              <div className="flex h-40 items-center justify-center text-sm text-slate-500">加载成分股中...</div>
            )}
            {!membersLoading && activeBlock && (
              <>
                <h3 className="mb-3 text-sm font-bold">成分股 · {activeBlock.name}</h3>
                <table className="table w-full">
                  <thead><tr><th>代码</th><th>名称</th><th>价格</th><th>涨跌幅</th></tr></thead>
                  <tbody>
                    {members.map((m: TdxBlockMember) => (
                      <tr key={m.symbol}>
                        <td>
                          <Link className="font-mono text-sm link" to={`/stock/${encodeURIComponent(m.symbol)}?m=CN`}>
                            {m.symbol}
                          </Link>
                        </td>
                        <td className="font-medium">{m.name ?? "--"}</td>
                        <td>{m.price != null ? `¥${m.price.toFixed(2)}` : "--"}</td>
                        <td className={pctClass(m.change_pct)}>{fmtPct(m.change_pct)}</td>
                      </tr>
                    ))}
                    {!members.length && (
                      <tr><td colSpan={4} className="py-8 text-center text-slate-500">暂无成分股</td></tr>
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