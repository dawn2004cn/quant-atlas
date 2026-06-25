import { MlflowConfigBar } from "../mlflow/MlflowConfigBar";
import type { MlflowRun, MlflowModelVersion } from "../../types/mlflow";

interface MarketplaceRunsTabProps {
  mlflowData: any;
  mlflowModels: any;
  mlflowConfig: any;
  busy: boolean;
  prefillFromRun: (run: MlflowRun) => void;
  setDetailRunId: (id: string | null) => void;
  setDetailProposalId: (id: string | null) => void;
}

export function MarketplaceRunsTab({
  mlflowData,
  mlflowModels,
  mlflowConfig,
  prefillFromRun,
  setDetailRunId,
  setDetailProposalId,
}: MarketplaceRunsTabProps) {
  return (
    <div className="space-y-4">
      <MlflowConfigBar config={mlflowConfig} />
      <div className="glass-card overflow-x-auto p-4">
        <h3 className="mb-3 font-semibold">回测实验（Runs）</h3>
        {!mlflowData?.available ? (
          <p className="text-sm text-slate-500">
            MLflow 未安装或未配置。安装 <code>pip install -e &quot;.[mlops]&quot;</code>{" "}
            并设置 <code>MLFLOW_TRACKING_URI</code> 后可查看回测实验记录。
          </p>
        ) : null}
        <table className="table table-sm">
          <thead>
            <tr>
              <th>实验</th>
              <th>标的</th>
              <th>策略</th>
              <th>总收益</th>
              <th>夏普</th>
              <th>状态</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {(mlflowData?.runs ?? []).length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center text-slate-500">
                  暂无 MLflow 回测记录
                </td>
              </tr>
            ) : (
              (mlflowData?.runs ?? []).map((run: MlflowRun) => (
                <tr key={run.run_id}>
                  <td className="font-mono text-xs">
                    <button
                      type="button"
                      className="link link-primary"
                      onClick={() => setDetailRunId(run.run_id)}
                    >
                      {run.run_name}
                    </button>
                  </td>
                  <td>{run.params?.symbol ?? "—"}</td>
                  <td>{run.params?.strategy_name ?? "—"}</td>
                  <td>
                    {run.metrics?.total_return != null
                      ? Number(run.metrics.total_return).toFixed(4)
                      : "—"}
                  </td>
                  <td>
                    {run.metrics?.sharpe != null
                      ? Number(run.metrics.sharpe).toFixed(2)
                      : "—"}
                  </td>
                  <td>
                    <span className="badge badge-outline">{run.status ?? "—"}</span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-ghost btn-xs"
                      onClick={() => prefillFromRun(run)}
                    >
                      治理
                    </button>
                    {run.ui_url ? (
                      <a
                        className="btn btn-ghost btn-xs"
                        href={run.ui_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        UI
                      </a>
                    ) : null}
                    <button
                      type="button"
                      className="btn btn-ghost btn-xs"
                      onClick={() => setDetailRunId(run.run_id)}
                    >
                      详情
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="glass-card overflow-x-auto p-4">
        <h3 className="mb-3 font-semibold">模型注册表（Model Registry）</h3>
        {!mlflowModels?.available ? (
          <p className="text-sm text-slate-500">MLflow Model Registry 未配置。</p>
        ) : null}
        <table className="table table-sm">
          <thead>
            <tr>
              <th>模型</th>
              <th>版本</th>
              <th>阶段</th>
              <th>Sharpe</th>
              <th>Run</th>
              <th>治理</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {(mlflowModels?.models ?? []).length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center text-slate-500">
                  暂无注册模型（可在 MLflow UI 中 register_model 后展示）
                </td>
              </tr>
            ) : (
              (mlflowModels?.models ?? []).map((model: MlflowModelVersion) => (
                <tr key={`${model.name}-${model.version}`}>
                  <td className="font-mono text-xs">{model.name}</td>
                  <td>{model.version ?? "—"}</td>
                  <td>
                    <span className="badge badge-outline">{model.stage ?? "—"}</span>
                  </td>
                  <td>
                    {model.metrics?.sharpe != null
                      ? Number(model.metrics.sharpe).toFixed(2)
                      : "—"}
                  </td>
                  <td className="font-mono text-xs">
                    {model.run_id ? (
                      <button
                        type="button"
                        className="link link-primary"
                        onClick={() => setDetailRunId(model.run_id!)}
                      >
                        {model.run_id.slice(0, 8)}
                      </button>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>
                    {(model.linked_proposals ?? []).length ? (
                      <button
                        type="button"
                        className="link link-primary text-xs"
                        onClick={() =>
                          setDetailProposalId(model.linked_proposals![0].proposal_id)
                        }
                      >
                        {model.linked_proposals!.length} 条提案
                      </button>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>
                    {model.run_id ? (
                      <button
                        type="button"
                        className="btn btn-ghost btn-xs"
                        onClick={() => setDetailRunId(model.run_id!)}
                      >
                        详情
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}