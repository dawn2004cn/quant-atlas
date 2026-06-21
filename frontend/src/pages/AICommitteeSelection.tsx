import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

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
  if (error) return <div className="alert alert-error">加载失败：{error.message}</div>;
  if (!data) return <div className="alert alert-warning">暂无选股数据</div>;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">AI 委员会选股</h1>
        <p className="text-sm text-slate-500">
          基于委员会投票共识的精选标的，共识阈值：{(data.threshold * 100).toFixed(0)}%
        </p>
        {data.updated_at && (
          <p className="mt-1 text-xs text-slate-400">
            更新于：{new Date(data.updated_at).toLocaleString("zh-CN")}
          </p>
        )}
      </div>

      <div className="glass-card p-3 text-sm">
        <span className="font-semibold">候选总数：</span>
        <span>{data.total_candidates}</span>
        <span className="ml-4 font-semibold">选中：</span>
        <span>{data.selected_stocks.length}</span>
      </div>

      {data.selected_stocks.length === 0 ? (
        <div className="alert alert-warning">当前无满足共识阈值的选股结果</div>
      ) : (
        data.selected_stocks.map((stock) => (
          <div key={stock.symbol} className="glass-card space-y-3 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-lg font-bold">
                  {stock.symbol}
                  <span className="ml-2 text-xs font-normal text-slate-500">{stock.market}</span>
                </h2>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">共识</span>
                <span className={`text-lg font-bold ${stock.consensus >= data.threshold ? "text-emerald-600" : "text-amber-600"}`}>
                  {(stock.consensus * 100).toFixed(0)}%
                </span>
              </div>
            </div>

            {/* Confidence bar */}
            <div>
              <div className="mb-1 flex justify-between text-xs">
                <span className="text-slate-500">信心指数</span>
                <span className="font-bold">{(stock.confidence * 100).toFixed(1)}%</span>
              </div>
              <progress className="progress progress-primary w-full" value={stock.confidence} max={1} />
            </div>

            {/* Vote counts */}
            <div className="flex gap-4 text-xs">
              <span className="text-emerald-600">赞成：{stock.votes_for}/{stock.total_votes}</span>
              <span className="text-rose-600">反对：{stock.votes_against}/{stock.total_votes}</span>
            </div>

            {stock.summary && (
              <p className="text-sm text-slate-600">{stock.summary}</p>
            )}

            {/* Vote breakdown */}
            {stock.vote_breakdown.length > 0 && (
              <details className="group">
                <summary className="cursor-pointer text-xs font-bold text-slate-500">
                  查看投票详情
                </summary>
                <div className="mt-2 space-y-2">
                  {stock.vote_breakdown.map((vote) => (
                    <div
                      key={vote.member}
                      className="rounded-lg bg-slate-50 p-2 text-xs dark:bg-slate-800"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{vote.member}</span>
                        <span className={`badge badge-xs ${vote.approve ? "badge-success" : "badge-error"}`}>
                          {vote.approve ? "赞成" : "反对"}
                        </span>
                      </div>
                      {vote.rationale && (
                        <p className="mt-1 text-slate-500">{vote.rationale}</p>
                      )}
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        ))
      )}
    </div>
  );
}
