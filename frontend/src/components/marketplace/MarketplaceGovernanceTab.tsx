import { FormEvent } from "react";
import { PageSkeleton } from "../PageSkeleton";
import { MlflowConfigBar } from "../mlflow/MlflowConfigBar";
import { GovernanceVoteFlow } from "../governance/GovernanceVoteFlow";
import type { AlphaGovernanceProposal, AlphaGovernanceVote, MiningFactor } from "../../lib/api";
import type { MlflowRun } from "../../types/mlflow";

interface MarketplaceGovernanceTabProps {
  workbench: any;
  govLoading: boolean;
  busy: boolean;
  govStrategyId: string;
  govExpression: string;
  govSharpe: number;
  govMlflowRunId: string;
  govMiningFactorId: string;
  voteRationale: string;
  mlflowConfig: any;
  miningFactors: MiningFactor[];
  proposals: AlphaGovernanceProposal[];
  voteHistory: AlphaGovernanceVote[];
  govMlflowRuns: MlflowRun[];
  onGovSubmit: (event: FormEvent) => Promise<void>;
  onVote: (proposalId: string, approve: boolean) => Promise<void>;
  onRunMining: () => Promise<void>;
  onProposeMining: (factorId: string) => Promise<void>;
  prefillFromRun: (run: MlflowRun) => void;
  prefillFromMining: (factor: MiningFactor) => void;
  setDetailProposalId: (id: string | null) => void;
  setDetailRunId: (id: string | null) => void;
  setGovStrategyId: (id: string) => void;
  setGovExpression: (expr: string) => void;
  setGovSharpe: (s: number) => void;
  setGovMlflowRunId: (id: string) => void;
  setGovMiningFactorId: (id: string) => void;
  setVoteRationale: (r: string) => void;
}

export function MarketplaceGovernanceTab({
  workbench, govLoading, busy,
  govStrategyId, govExpression, govSharpe,
  govMlflowRunId, govMiningFactorId, voteRationale, mlflowConfig,
  miningFactors, proposals, voteHistory, govMlflowRuns,
  onGovSubmit, onVote, onRunMining, onProposeMining,
  prefillFromRun, prefillFromMining,
  setDetailProposalId, setDetailRunId,
  setGovStrategyId, setGovExpression, setGovSharpe, setVoteRationale,
}: MarketplaceGovernanceTabProps) {
  return (
    <div className="space-y-4">
      {govLoading ? <PageSkeleton rows={4} /> : null}
      <MlflowConfigBar config={mlflowConfig} />
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="glass-card p-4">
          <div className="text-2xl font-bold">{workbench?.stats.proposals ?? 0}</div>
          <div className="text-xs text-slate-500">提案数</div>
        </div>
        <div className="glass-card p-4">
          <div className="text-2xl font-bold">{workbench?.stats.votes ?? 0}</div>
          <div className="text-xs text-slate-500">累计投票</div>
        </div>
        <div className="glass-card p-4">
          <div className="text-2xl font-bold">{workbench?.stats.active_factors ?? 0}</div>
          <div className="text-xs text-slate-500">已激活因子</div>
        </div>
      </div>
      {workbench?.stats.thresholds ? (
        <p className="text-xs text-slate-500">
          治理阈值：赞成率 ≥ {(workbench.stats.thresholds.majority * 100).toFixed(0)}%，法定人数 {workbench.stats.thresholds.quorum}
        </p>
      ) : null}

      <div className="glass-card overflow-x-auto p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-semibold">Auto-Alpha 挖掘 → DAO 一键提案</h3>
          <button type="button" className="btn btn-outline btn-sm" disabled={busy} onClick={() => void onRunMining()}>
            运行挖掘
          </button>
        </div>
        <table className="table table-sm">
          <thead>
            <tr><th>Factor</th><th>表达式</th><th>IC</th><th>Sharpe</th><th /></tr>
          </thead>
          <tbody>
            {miningFactors.length === 0 ? (
              <tr><td colSpan={5} className="text-center text-slate-500">暂无挖掘因子</td></tr>
            ) : (
              miningFactors.map((factor: MiningFactor) => (
                <tr key={factor.factor_id}>
                  <td className="font-mono text-xs">{factor.factor_id}</td>
                  <td className="max-w-[10rem] truncate font-mono text-xs">{factor.expression}</td>
                  <td>{factor.ic_mean != null ? Number(factor.ic_mean).toFixed(3) : "—"}</td>
                  <td>{factor.sharpe != null ? Number(factor.sharpe).toFixed(2) : "—"}</td>
                  <td className="flex gap-1">
                    <button type="button" className="btn btn-primary btn-xs" disabled={busy} onClick={() => void onProposeMining(factor.factor_id)}>提案</button>
                    <button type="button" className="btn btn-ghost btn-xs" disabled={busy} onClick={() => prefillFromMining(factor)}>填表</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="glass-card overflow-x-auto p-4">
        <h3 className="mb-3 font-semibold">MLflow 回测实验（关联提案）</h3>
        {!workbench?.mlflow?.available ? (<p className="text-sm text-slate-500">MLflow 未配置时可手动填写下方提案表单。</p>) : null}
        <table className="table table-sm">
          <thead><tr><th>实验</th><th>标的</th><th>策略</th><th>Sharpe</th><th /></tr></thead>
          <tbody>
            {govMlflowRuns.length === 0 ? (
              <tr><td colSpan={5} className="text-center text-slate-500">暂无 MLflow 记录</td></tr>
            ) : (
              govMlflowRuns.map((run: MlflowRun) => (
                <tr key={run.run_id}>
                  <td className="font-mono text-xs">{run.run_name}</td>
                  <td>{run.params?.symbol ?? "—"}</td>
                  <td>{run.params?.strategy_name ?? "—"}</td>
                  <td>{run.metrics?.sharpe != null ? Number(run.metrics.sharpe).toFixed(2) : "—"}</td>
                  <td className="flex gap-1">
                    <button type="button" className="btn btn-ghost btn-xs" onClick={() => prefillFromRun(run)}>填表</button>
                    {run.ui_url ? (<a className="btn btn-ghost btn-xs" href={run.ui_url} target="_blank" rel="noreferrer">UI</a>) : null}
                    <button type="button" className="btn btn-ghost btn-xs" onClick={() => setDetailRunId(run.run_id)}>详情</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <form className="glass-card max-w-xl space-y-4 p-6" onSubmit={onGovSubmit}>
        <h3 className="font-semibold">提交因子提案</h3>
        <label className="form-control">
          <span className="label-text">Strategy ID</span>
          <input className="input input-bordered" value={govStrategyId} onChange={(e) => setGovStrategyId(e.target.value)} required />
        </label>
        <label className="form-control">
          <span className="label-text">表达式</span>
          <input className="input input-bordered font-mono text-sm" value={govExpression} onChange={(e) => setGovExpression(e.target.value)} placeholder="close / open - 1" required />
        </label>
        <label className="form-control">
          <span className="label-text">Sharpe（ZK 证明输入）</span>
          <input type="number" step="0.01" className="input input-bordered" value={govSharpe} onChange={(e) => setGovSharpe(Number(e.target.value))} />
        </label>
        {govMlflowRunId || govMiningFactorId ? (
          <p className="text-xs text-slate-500">
            关联：{govMlflowRunId ? <span className="ml-1 font-mono">MLflow {govMlflowRunId.slice(0, 8)}</span> : null}{govMiningFactorId ? <span className="ml-1 font-mono">挖掘 {govMiningFactorId}</span> : null}
          </p>
        ) : null}
        <button type="submit" className="btn btn-primary" disabled={busy}>提交提案</button>
      </form>

      <label className="form-control max-w-xl px-1">
        <span className="label-text">投票备注（可选）</span>
        <input className="input input-bordered input-sm" value={voteRationale} onChange={(e) => setVoteRationale(e.target.value)} placeholder="赞成/反对理由" />
      </label>

      <div className="glass-card overflow-x-auto p-4">
        <h3 className="mb-3 font-semibold">待决议提案</h3>
        {proposals.length > 0 ? (
          <div className="mb-4 max-w-xl">
            <GovernanceVoteFlow proposal={proposals[0]} majorityThreshold={workbench?.stats.thresholds?.majority} />
            <p className="mt-1 text-xs text-slate-500">展示最新提案「{proposals[0].strategy_id}」投票进度；点击 ID 查看全部详情。</p>
          </div>
        ) : null}
        <table className="table table-sm">
          <thead><tr><th>ID</th><th>策略</th><th>表达式</th><th>关联</th><th>状态</th><th>票型</th><th /></tr></thead>
          <tbody>
            {proposals.length === 0 ? (
              <tr><td colSpan={7} className="text-center text-slate-500">暂无提案</td></tr>
            ) : (
              proposals.map((item: AlphaGovernanceProposal) => (
                <tr key={item.proposal_id}>
                  <td className="font-mono text-xs"><button type="button" className="link link-primary" onClick={() => setDetailProposalId(item.proposal_id)}>{item.proposal_id.slice(-8)}</button></td>
                  <td>{item.strategy_id}</td>
                  <td className="max-w-[12rem] truncate font-mono text-xs">{item.expression}</td>
                  <td className="font-mono text-xs">{item.mlflow_run_id ? `mlf:${item.mlflow_run_id.slice(0, 6)}` : item.mining_factor_id ? `min:${item.mining_factor_id.slice(0, 8)}` : "—"}</td>
                  <td><span className="badge badge-outline">{item.status}</span></td>
                  <td>{item.votes_for}/{item.votes_against}</td>
                  <td className="flex gap-1">
                    <button type="button" className="btn btn-success btn-xs" disabled={busy} onClick={() => void onVote(item.proposal_id, true)}>赞成</button>
                    <button type="button" className="btn btn-error btn-xs" disabled={busy} onClick={() => void onVote(item.proposal_id, false)}>反对</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="glass-card overflow-x-auto p-4">
        <h3 className="mb-3 font-semibold">投票审计（JSONL）</h3>
        <table className="table table-sm">
          <thead><tr><th>提案</th><th>团队</th><th>立场</th><th>理由</th><th>时间</th></tr></thead>
          <tbody>
            {voteHistory.length === 0 ? (
              <tr><td colSpan={5} className="text-center text-slate-500">暂无投票记录</td></tr>
            ) : (
              voteHistory.map((row: AlphaGovernanceVote, idx: number) => (
                <tr key={`${row.proposal_id}-${row.voted_at}-${idx}`}>
                  <td className="font-mono text-xs">{row.proposal_id.slice(-8)}</td>
                  <td>{row.voter_team}</td>
                  <td>{row.approve ? "赞成" : "反对"}</td>
                  <td className="max-w-[10rem] truncate">{row.rationale || "—"}</td>
                  <td className="text-xs">{row.voted_at}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}