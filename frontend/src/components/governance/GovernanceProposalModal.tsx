import useSWR from "swr";
import { fetchGovernanceProposal, fetchMlflowRun, fetchGovernanceStats } from "../../lib/api";
import type { AlphaGovernanceProposal, AlphaGovernanceVote } from "../../lib/api";
import { GovernanceVoteFlow } from "./GovernanceVoteFlow";
import { GovernanceTimeline } from "./GovernanceTimeline";

type Props = {
  proposalId: string | null;
  onClose: () => void;
};

export function GovernanceProposalModal({ proposalId, onClose }: Props) {
  const { data: proposal, isLoading, error } = useSWR(
    proposalId ? `gov-detail-${proposalId}` : null,
    () => fetchGovernanceProposal(proposalId!),
  );

  const mlflowRunId = proposal?.mlflow_run_id;
  const { data: mlflowData } = useSWR(
    mlflowRunId ? `mlflow-detail-${mlflowRunId}` : null,
    () => fetchMlflowRun(mlflowRunId!),
  );
  const { data: govStats } = useSWR("gov-stats-thresholds", fetchGovernanceStats);

  const majorityThreshold =
    Number(govStats?.stats?.thresholds?.majority) || 0.6;

  if (!proposalId) {
    return null;
  }

  return (
    <dialog className="modal modal-open">
      <div className="modal-box max-w-2xl">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold">提案详情</h3>
            <p className="font-mono text-xs text-slate-500">{proposalId}</p>
          </div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            关闭
          </button>
        </div>

        {isLoading ? <p className="text-sm text-slate-500">加载中…</p> : null}
        {error ? (
          <div className="alert alert-error text-sm">{error.message}</div>
        ) : null}

        {proposal ? (
          <div className="space-y-4 text-sm">
            <dl className="grid gap-2 sm:grid-cols-2">
              <div>
                <dt className="text-xs text-slate-500">策略</dt>
                <dd>{proposal.strategy_id}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">提交人</dt>
                <dd>{proposal.manager_id}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">状态</dt>
                <dd>
                  <span className="badge badge-outline">{proposal.status}</span>
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">票型</dt>
                <dd>
                  {proposal.votes_for}/{proposal.votes_against}
                </dd>
              </div>
            </dl>

            <GovernanceVoteFlow
              proposal={proposal}
              majorityThreshold={majorityThreshold}
            />

            {(proposal.timeline ?? []).length ? (
              <div>
                <div className="mb-2 text-xs font-semibold text-slate-500">审批时间线</div>
                <GovernanceTimeline events={proposal.timeline ?? []} />
              </div>
            ) : null}

            <div>
              <div className="text-xs text-slate-500">表达式</div>
              <pre className="mt-1 overflow-x-auto rounded-lg bg-slate-900/90 p-3 text-xs text-slate-100">
                {proposal.expression}
              </pre>
            </div>

            {proposal.performance_metrics ? (
              <div>
                <div className="text-xs text-slate-500">绩效指标</div>
                <pre className="mt-1 overflow-x-auto rounded-lg bg-slate-100/80 p-2 text-xs dark:bg-slate-800/80">
                  {JSON.stringify(proposal.performance_metrics, null, 2)}
                </pre>
              </div>
            ) : null}

            <LineageBlock proposal={proposal} mlflowRun={mlflowData?.run} />

            {proposal.tally ? (
              <div>
                <div className="text-xs text-slate-500">计票结果</div>
                <pre className="mt-1 text-xs">{JSON.stringify(proposal.tally, null, 2)}</pre>
              </div>
            ) : null}

            {(proposal.vote_history ?? []).length ? (
              <div className="overflow-x-auto">
                <div className="mb-2 text-xs font-semibold text-slate-500">投票审计</div>
                <table className="table table-xs">
                  <thead>
                    <tr>
                      <th>团队</th>
                      <th>立场</th>
                      <th>理由</th>
                      <th>时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(proposal.vote_history ?? []).map(
                      (row: AlphaGovernanceVote, idx: number) => (
                        <tr key={`${row.voter_team}-${idx}`}>
                          <td>{row.voter_team}</td>
                          <td>{row.approve ? "赞成" : "反对"}</td>
                          <td className="max-w-[8rem] truncate">{row.rationale || "—"}</td>
                          <td className="text-xs">{row.voted_at}</td>
                        </tr>
                      ),
                    )}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
      <form method="dialog" className="modal-backdrop">
        <button type="button" onClick={onClose}>
          close
        </button>
      </form>
    </dialog>
  );
}

function LineageBlock({
  proposal,
  mlflowRun,
}: {
  proposal: AlphaGovernanceProposal;
  mlflowRun?: {
    run_id: string;
    run_name?: string;
    status?: string;
    ui_url?: string;
    metrics?: Record<string, number>;
    params?: Record<string, string>;
  };
}) {
  if (!proposal.mlflow_run_id && !proposal.mining_factor_id) {
    return null;
  }

  return (
    <div className="rounded-lg border border-slate-200/80 p-3 dark:border-slate-700">
      <div className="text-xs font-semibold text-slate-500">血缘关联</div>
      {proposal.mining_factor_id ? (
        <p className="mt-1 font-mono text-xs">挖掘因子：{proposal.mining_factor_id}</p>
      ) : null}
      {proposal.mlflow_run_id ? (
        <p className="mt-1 font-mono text-xs">MLflow run：{proposal.mlflow_run_id}</p>
      ) : null}
      {mlflowRun ? (
        <dl className="mt-2 grid gap-1 text-xs sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">实验名</dt>
            <dd>{mlflowRun.run_name ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">状态</dt>
            <dd>{mlflowRun.status ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">标的</dt>
            <dd>{mlflowRun.params?.symbol ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Sharpe</dt>
            <dd>
              {mlflowRun.metrics?.sharpe != null
                ? Number(mlflowRun.metrics.sharpe).toFixed(2)
                : "—"}
            </dd>
          </div>
        </dl>
      ) : proposal.mlflow_run_id ? (
        <p className="mt-1 text-xs text-slate-500">MLflow 详情不可用或未配置</p>
      ) : null}
      {"ui_url" in (mlflowRun ?? {}) && mlflowRun?.ui_url ? (
        <a
          className="btn btn-outline btn-xs mt-2"
          href={mlflowRun.ui_url}
          target="_blank"
          rel="noreferrer"
        >
          打开 MLflow UI
        </a>
      ) : null}
    </div>
  );
}
