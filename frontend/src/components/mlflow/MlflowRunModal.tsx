import useSWR from "swr";
import { fetchMlflowRun } from "../../lib/api";
import { usePlatformFeatures } from "../../hooks/usePlatformFeatures";

type Props = {
  runId: string | null;
  onClose: () => void;
  onPrefillGovernance?: (run: {
    run_id: string;
    run_name?: string;
    metrics?: Record<string, number>;
    params?: Record<string, string>;
  }) => void;
  onOpenProposal?: (proposalId: string) => void;
};

export function MlflowRunModal({ runId, onClose, onPrefillGovernance, onOpenProposal }: Props) {
  const { features } = usePlatformFeatures();
  const { data, isLoading, error } = useSWR(
    runId ? `mlflow-run-${runId}` : null,
    () => fetchMlflowRun(runId!),
  );

  const run = data?.run;
  const linkedProposals = data?.linked_proposals ?? [];

  if (!runId) {
    return null;
  }

  return (
    <dialog className="modal modal-open">
      <div className="modal-box max-w-2xl">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold">MLflow 实验详情</h3>
            <p className="font-mono text-xs text-slate-500">{runId}</p>
          </div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
            关闭
          </button>
        </div>

        {isLoading ? <p className="text-sm text-slate-500">加载中…</p> : null}
        {error ? <div className="alert alert-error text-sm">{error.message}</div> : null}

        {run ? (
          <div className="space-y-4 text-sm">
            <dl className="grid gap-2 sm:grid-cols-2">
              <div>
                <dt className="text-xs text-slate-500">实验名</dt>
                <dd>{run.run_name ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">状态</dt>
                <dd>
                  <span className="badge badge-outline">{run.status ?? "—"}</span>
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">标的</dt>
                <dd>{run.params?.symbol ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">策略</dt>
                <dd>{run.params?.strategy_name ?? "—"}</dd>
              </div>
            </dl>

            {run.metrics && Object.keys(run.metrics).length ? (
              <div>
                <div className="text-xs text-slate-500">指标</div>
                <dl className="mt-2 grid gap-2 sm:grid-cols-2">
                  {Object.entries(run.metrics).map(([key, value]) => (
                    <div key={key}>
                      <dt className="text-xs text-slate-500">{key}</dt>
                      <dd className="font-mono">{Number(value).toFixed(4)}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            ) : null}

            {run.params && Object.keys(run.params).length ? (
              <div>
                <div className="text-xs text-slate-500">参数</div>
                <pre className="mt-1 overflow-x-auto rounded-lg bg-slate-100/80 p-2 text-xs dark:bg-slate-800/80">
                  {JSON.stringify(run.params, null, 2)}
                </pre>
              </div>
            ) : null}

            {linkedProposals.length ? (
              <div>
                <div className="text-xs font-semibold text-slate-500">关联治理提案</div>
                <ul className="mt-2 space-y-1 text-xs">
                  {linkedProposals.map((proposal) => (
                    <li key={proposal.proposal_id} className="flex flex-wrap items-center gap-2">
                      <span className="font-mono">{proposal.proposal_id.slice(-8)}</span>
                      <span>{proposal.strategy_id}</span>
                      <span className="badge badge-outline badge-xs">{proposal.status}</span>
                      {onOpenProposal ? (
                        <button
                          type="button"
                          className="btn btn-ghost btn-xs"
                          onClick={() => {
                            onOpenProposal(proposal.proposal_id);
                            onClose();
                          }}
                        >
                          查看提案
                        </button>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div className="flex flex-wrap gap-2">
              {run.ui_url ? (
                <a
                  className="btn btn-outline btn-sm"
                  href={run.ui_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  MLflow UI
                </a>
              ) : null}
              {onPrefillGovernance ? (
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => {
                    onPrefillGovernance(run);
                    onClose();
                  }}
                >
                  填入治理提案
                </button>
              ) : null}
              {features.feature_alpha_marketplace ? (
                <a
                  className="btn btn-outline btn-sm"
                  href={`/app/marketplace?mlflow_run_id=${encodeURIComponent(run.run_id)}#governance`}
                >
                  打开治理深链
                </a>
              ) : null}
            </div>
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
