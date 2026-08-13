import { Link } from "react-router-dom";
import useSWR from "swr";
import { PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import { DEMO_COMMITTEE_SELECTION } from "../lib/demoCatalog";

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50 ${className}`}>{children}</div>;
}

type CommitteeVote = {
  member: string;
  approve: boolean;
  rationale?: string;
};

type SelectedStock = {
  symbol: string;
  market: string;
  confidence: number;
  votes_for: number;
  votes_against: number;
  total_votes: number;
  consensus: number;
  vote_breakdown: CommitteeVote[];
  summary?: string;
};

type CommitteeSelection = {
  selected_stocks: SelectedStock[];
  total_candidates: number;
  threshold: number;
  updated_at: string;
};

export function AICommitteeSelectionPage() {
  const { data, error, isLoading } = useSWR(
    "ai-committee-selection",
    () => apiFetchV1<CommitteeSelection>("/ai-committee/selection"),
    { refreshInterval: 60_000 },
  );

  if (isLoading && !data) return <PageSkeleton rows={3} />;

  const isDemo = Boolean(error) || !data || !(data.selected_stocks ?? []).length;
  const view = isDemo ? DEMO_COMMITTEE_SELECTION : data;

  return (
    <div className="mx-auto max-w-[1400px] space-y-5">
      <PageQuickNav items={QUICK_NAV_PRESETS.aiCommitteeSelection} />
      <div>
        <h1 className="text-2xl font-bold">AI 委员会选股</h1>
        <p className="text-sm text-zinc-500">
          基于委员会投票共识的精选标的，共识阈值：{(view.threshold * 100).toFixed(0)}%
        </p>
        <DemoBanner show={isDemo} />
        {view.updated_at && (
          <p className="mt-1 text-xs text-zinc-400">
            更新于：{view.updated_at === "演示" ? "演示" : new Date(view.updated_at).toLocaleString("zh-CN")}
          </p>
        )}
      </div>

      <Panel className="p-3 text-sm">
        <span className="font-semibold">候选总数：</span>
        <span>{view.total_candidates}</span>
        <span className="ml-4 font-semibold">选中：</span>
        <span>{view.selected_stocks.length}</span>
      </Panel>

      {view.selected_stocks.length === 0 ? (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-400">当前无满足共识阈值的选股结果</div>
      ) : (
        view.selected_stocks.map((stock) => (
          <Panel key={stock.symbol} className="space-y-3 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-lg font-bold">
                  <Link className="link" to={`/stock/${encodeURIComponent(stock.symbol)}?m=CN`}>
                    {stock.symbol}
                  </Link>
                  <span className="ml-2 text-xs font-normal text-zinc-500">{stock.market}</span>
                </h2>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-zinc-500">共识</span>
                <span className={`text-lg font-bold ${stock.consensus >= view.threshold ? "text-emerald-400" : "text-amber-400"}`}>
                  {(stock.consensus * 100).toFixed(0)}%
                </span>
              </div>
            </div>

            {/* Confidence bar */}
            <div>
              <div className="mb-1 flex justify-between text-xs">
                <span className="text-zinc-500">信心指数</span>
                <span className="font-bold">{(stock.confidence * 100).toFixed(1)}%</span>
              </div>
              <progress className="progress progress-primary w-full" value={stock.confidence} max={1} />
            </div>

            {/* Vote counts */}
            <div className="flex gap-4 text-xs">
              <span className="text-emerald-400">赞成：{stock.votes_for}/{stock.total_votes}</span>
              <span className="text-rose-400">反对：{stock.votes_against}/{stock.total_votes}</span>
            </div>

            {stock.summary && (
              <p className="text-sm text-zinc-400">{stock.summary}</p>
            )}

            {/* Vote breakdown */}
            {stock.vote_breakdown.length > 0 && (
              <details className="group">
                <summary className="cursor-pointer text-xs font-bold text-zinc-500">
                  查看投票详情
                </summary>
                <div className="mt-2 space-y-2">
                  {stock.vote_breakdown.map((vote) => (
                    <div
                      key={vote.member}
                      className="rounded-lg bg-zinc-50 p-2 text-xs dark:bg-zinc-800"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{vote.member}</span>
                        <span className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold ${vote.approve ? "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30" : "bg-rose-500/15 text-rose-400 ring-1 ring-rose-500/30"}`}>
                          {vote.approve ? "赞成" : "反对"}
                        </span>
                      </div>
                      {vote.rationale && (
                        <p className="mt-1 text-zinc-500">{vote.rationale}</p>
                      )}
                    </div>
                  ))}
                </div>
              </details>
            )}
          </Panel>
        ))
      )}
    </div>
  );
}
