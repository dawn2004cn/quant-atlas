import type { MlflowTrackingConfig } from "../../types/mlflow";

type Props = {
  config?: MlflowTrackingConfig | null;
};

export function MlflowConfigBar({ config }: Props) {
  if (!config) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200/80 bg-slate-50/80 px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-900/40">
      <span className={`badge badge-sm ${config.available ? "badge-success" : "badge-ghost"}`}>
        {config.available ? "MLflow 可用" : "MLflow 未安装"}
      </span>
      {config.experiment ? (
        <span>
          实验：<span className="font-mono">{config.experiment}</span>
        </span>
      ) : null}
      {config.tracking_uri ? (
        <span className="max-w-md truncate font-mono text-slate-500" title={config.tracking_uri}>
          {config.tracking_uri}
        </span>
      ) : (
        <span className="text-slate-500">未配置 MLFLOW_TRACKING_URI</span>
      )}
      {config.register_models ? (
        <span className="badge badge-sm badge-warning">自动注册模型</span>
      ) : (
        <span className="badge badge-sm badge-outline">仅记录 Run</span>
      )}
    </div>
  );
}
