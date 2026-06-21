import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import useSWR from "swr";
import { GovernanceProposalModal } from "../components/governance/GovernanceProposalModal";
import { GovernanceVoteFlow } from "../components/governance/GovernanceVoteFlow";
import { MlflowConfigBar } from "../components/mlflow/MlflowConfigBar";
import { MlflowRunModal } from "../components/mlflow/MlflowRunModal";
import { PageSkeleton } from "../components/PageSkeleton";
import {
  cancelMarketplaceOrder,
  castGovernanceVote,
  contributeToListing,
  creditReputation,
  fetchGovernanceWorkbench,
  fetchMarketplaceListings,
  fetchMarketplaceOrders,
  fetchMlflowModels,
  fetchMlflowRuns,
  fetchMlflowStatus,
  fetchReputationBalance,
  listMarketplaceToken,
  proposeMiningFactorToDao,
  runAlphaMining,
  submitGovernanceProposal,
} from "../lib/api";
import type { AlphaGovernanceProposal, AlphaGovernanceVote, MiningFactor } from "../lib/api";
import type { MarketplaceListing, MarketplaceOrder } from "../types/backtest";
import type { MlflowModelVersion, MlflowRun } from "../types/mlflow";

type MpTab = "browse" | "orders" | "list" | "wallet" | "runs" | "governance";

export function MarketplacePage() {
  const [searchParams] = useSearchParams();
  const [tab, setTab] = useState<MpTab>("browse");
  const [toast, setToast] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [listTokenId, setListTokenId] = useState("");
  const [listPrice, setListPrice] = useState(10);
  const [listSignals, setListSignals] = useState(100);
  const [creditAmount, setCreditAmount] = useState(50);

  const [govStrategyId, setGovStrategyId] = useState("");
  const [govExpression, setGovExpression] = useState("");
  const [govSharpe, setGovSharpe] = useState(1.0);
  const [govMlflowRunId, setGovMlflowRunId] = useState("");
  const [govMiningFactorId, setGovMiningFactorId] = useState("");
  const [voteRationale, setVoteRationale] = useState("");
  const [detailProposalId, setDetailProposalId] = useState<string | null>(null);
  const [detailRunId, setDetailRunId] = useState<string | null>(null);

  useEffect(() => {
    if (window.location.hash === "#governance") {
      setTab("governance");
    }
    if (window.location.hash === "#runs") {
      setTab("runs");
    }
    const proposalId = searchParams.get("proposal_id");
    const runIdView = searchParams.get("run_id");
    const strategy =
      searchParams.get("strategy") || searchParams.get("strategy_name") || "";
    const symbol = searchParams.get("symbol") || "";
    const sharpe = searchParams.get("sharpe");
    const mlflowRunId = searchParams.get("mlflow_run_id") || "";
    if (proposalId) {
      setTab("governance");
      setDetailProposalId(proposalId);
    }
    if (runIdView) {
      setTab("runs");
      setDetailRunId(runIdView);
    }
    if (strategy || symbol || sharpe || mlflowRunId) {
      setTab("governance");
      if (strategy) setGovStrategyId(strategy);
      if (symbol && strategy) {
        setGovExpression(`backtest:${strategy}@${symbol}`);
      } else if (symbol) {
        setGovExpression(`backtest:${symbol}`);
      }
      if (sharpe) setGovSharpe(Number(sharpe));
      if (mlflowRunId) setGovMlflowRunId(mlflowRunId);
    }
  }, [searchParams]);

  const { data: balance, mutate: refreshBalance } = useSWR(
    "reputation-balance",
    fetchReputationBalance,
  );
  const { data: listings = [], mutate: refreshListings } = useSWR(
    "mp-listings",
    () => fetchMarketplaceListings(true),
  );
  const { data: orders = [], mutate: refreshOrders } = useSWR(
    "mp-orders",
    fetchMarketplaceOrders,
  );
  const { data: mlflowData } = useSWR(
    tab === "runs" ? "mlflow-runs" : null,
    () => fetchMlflowRuns(25),
  );
  const { data: mlflowModels } = useSWR(
    tab === "runs" ? "mlflow-models" : null,
    () => fetchMlflowModels(25),
  );
  const { data: mlflowStatus } = useSWR(
    tab === "runs" ? "mlflow-status" : null,
    fetchMlflowStatus,
  );
  const {
    data: workbench,
    mutate: refreshWorkbench,
    isLoading: govLoading,
  } = useSWR(
    tab === "governance" ? "gov-workbench" : null,
    () => fetchGovernanceWorkbench(12),
  );

  const proposals = workbench?.proposals ?? [];
  const voteHistory = workbench?.votes ?? [];
  const miningFactors = workbench?.mining_factors ?? [];
  const govMlflowRuns = workbench?.mlflow?.runs ?? [];
  const mlflowConfig = workbench?.mlflow?.config ?? mlflowStatus ?? null;

  function notify(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(null), 3000);
  }

  async function onContribute(listingId?: string) {
    if (!listingId) return;
    setBusy(true);
    try {
      const res = await contributeToListing(listingId);
      notify(`贡献成功：${res.order_id ?? ""}`);
      await Promise.all([refreshOrders(), refreshBalance(), refreshListings()]);
    } catch (err) {
      notify(err instanceof Error ? err.message : "贡献失败");
    } finally {
      setBusy(false);
    }
  }

  async function onCancel(orderId?: string) {
    if (!orderId || !window.confirm("确定取消此订单？")) return;
    setBusy(true);
    try {
      await cancelMarketplaceOrder(orderId);
      notify("订单已取消");
      await Promise.all([refreshOrders(), refreshBalance()]);
    } catch (err) {
      notify(err instanceof Error ? err.message : "取消失败");
    } finally {
      setBusy(false);
    }
  }

  async function onListSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const res = await listMarketplaceToken({
        token_id: listTokenId,
        reputation_cost: listPrice,
        signal_count: listSignals,
      });
      notify(`上架成功：${res.listing_id ?? ""}`);
      setListTokenId("");
      await Promise.all([refreshListings(), refreshBalance()]);
    } catch (err) {
      notify(err instanceof Error ? err.message : "上架失败");
    } finally {
      setBusy(false);
    }
  }

  async function onCreditSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await creditReputation(creditAmount);
      notify(`获得 ${creditAmount} 声誉积分`);
      await refreshBalance();
    } catch (err) {
      notify(err instanceof Error ? err.message : "充值失败");
    } finally {
      setBusy(false);
    }
  }

  async function onGovSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const res = await submitGovernanceProposal({
        strategy_id: govStrategyId,
        expression: govExpression,
        performance_metrics: { sharpe: govSharpe },
        mlflow_run_id: govMlflowRunId || undefined,
        mining_factor_id: govMiningFactorId || undefined,
      });
      notify(`提案已提交：${res.proposal_id}`);
      setGovStrategyId("");
      setGovExpression("");
      setGovMlflowRunId("");
      setGovMiningFactorId("");
      await refreshWorkbench();
    } catch (err) {
      notify(err instanceof Error ? err.message : "提案失败");
    } finally {
      setBusy(false);
    }
  }

  async function onProposeMining(factorId: string) {
    setBusy(true);
    try {
      const res = await proposeMiningFactorToDao(factorId);
      if (res.error) {
        notify(res.error);
        return;
      }
      notify(`挖掘因子已提案：${res.proposal_id ?? ""}`);
      await refreshWorkbench();
    } catch (err) {
      notify(err instanceof Error ? err.message : "提案失败");
    } finally {
      setBusy(false);
    }
  }

  async function onRunMining() {
    setBusy(true);
    try {
      const res = await runAlphaMining({ generations: 5, population_size: 30 });
      notify(`挖掘完成：${res.top_factors?.length ?? 0} 个优质因子`);
      await refreshWorkbench();
    } catch (err) {
      notify(err instanceof Error ? err.message : "挖掘失败");
    } finally {
      setBusy(false);
    }
  }

  function prefillFromRun(run: MlflowRun) {
    setGovStrategyId(String(run.params?.strategy_name ?? run.run_name ?? ""));
    setGovExpression(
      `mlflow:${run.run_name ?? run.run_id} symbol=${run.params?.symbol ?? ""}`,
    );
    const sharpe = run.metrics?.sharpe;
    if (sharpe != null) setGovSharpe(Number(sharpe));
    setGovMlflowRunId(run.run_id);
    setGovMiningFactorId("");
    setTab("governance");
  }

  function prefillFromMining(factor: MiningFactor) {
    setGovStrategyId(factor.factor_id);
    setGovExpression(factor.expression);
    if (factor.sharpe != null) setGovSharpe(Number(factor.sharpe));
    setGovMiningFactorId(factor.factor_id);
    setGovMlflowRunId("");
  }

  async function onVote(proposalId: string, approve: boolean) {
    setBusy(true);
    try {
      const res = await castGovernanceVote({
        proposal_id: proposalId,
        approve,
        rationale: voteRationale,
      });
      const status = String(res.tally?.status ?? "");
      notify(`投票成功${status ? `：${status}` : ""}`);
      setVoteRationale("");
      await refreshWorkbench();
    } catch (err) {
      notify(err instanceof Error ? err.message : "投票失败");
    } finally {
      setBusy(false);
    }
  }

  const score = balance?.reputation_score ?? 0;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Alpha Marketplace</h1>
        <p className="text-sm text-slate-500">因子贡献社区 — 声誉积分协作</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="glass-card p-4">
          <div className="text-2xl font-bold text-violet-600">{Number(score).toFixed(1)}</div>
          <div className="text-xs text-slate-500">我的声誉积分</div>
        </div>
        <div className="glass-card p-4">
          <div className="text-2xl font-bold">{orders.length}</div>
          <div className="text-xs text-slate-500">我的订单</div>
        </div>
        <div className="glass-card p-4">
          <div className="text-2xl font-bold">{listings.length}</div>
          <div className="text-xs text-slate-500">在售列表</div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {(
          [
            ["browse", "浏览市场"],
            ["orders", "我的订单"],
            ["list", "上架因子"],
            ["wallet", "声誉"],
            ["runs", "回测实验"],
            ["governance", "因子治理"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`btn btn-sm ${tab === id ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "browse" ? (
        <div className="glass-card overflow-x-auto p-4">
          <table className="table table-sm">
            <thead>
              <tr>
                <th>Token</th>
                <th>贡献者</th>
                <th>声誉成本</th>
                <th>信号数</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {listings.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center text-slate-500">
                    暂无在售因子
                  </td>
                </tr>
              ) : (
                listings.map((item: MarketplaceListing) => (
                  <tr key={item.listing_id ?? item.token_id}>
                    <td className="font-mono text-xs">{item.token_id}</td>
                    <td>{item.seller_id}</td>
                    <td>{(item.reputation_cost ?? item.price_tokens ?? 0).toFixed(1)}</td>
                    <td>{item.signal_count ?? "-"}</td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-primary btn-xs"
                        disabled={busy}
                        onClick={() => void onContribute(item.listing_id)}
                      >
                        贡献
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : null}

      {tab === "orders" ? (
        <div className="glass-card overflow-x-auto p-4">
          <table className="table table-sm">
            <thead>
              <tr>
                <th>订单</th>
                <th>Listing</th>
                <th>花费</th>
                <th>状态</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {orders.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center text-slate-500">
                    暂无订单
                  </td>
                </tr>
              ) : (
                orders.map((item: MarketplaceOrder) => (
                  <tr key={item.order_id}>
                    <td className="font-mono text-xs">{item.order_id?.slice(0, 10)}</td>
                    <td className="font-mono text-xs">{item.listing_id?.slice(0, 8)}</td>
                    <td>{(item.reputation_spent ?? item.tokens_spent ?? 0).toFixed(1)}</td>
                    <td>
                      <span className="badge badge-outline">{item.status ?? "active"}</span>
                    </td>
                    <td>
                      {item.status === "active" ? (
                        <button
                          type="button"
                          className="btn btn-error btn-xs"
                          disabled={busy}
                          onClick={() => void onCancel(item.order_id)}
                        >
                          取消
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : null}

      {tab === "list" ? (
        <form className="glass-card max-w-lg space-y-4 p-6" onSubmit={onListSubmit}>
          <label className="form-control">
            <span className="label-text">Token ID</span>
            <input
              className="input input-bordered"
              value={listTokenId}
              onChange={(e) => setListTokenId(e.target.value)}
              required
            />
          </label>
          <label className="form-control">
            <span className="label-text">声誉成本</span>
            <input
              type="number"
              min={1}
              className="input input-bordered"
              value={listPrice}
              onChange={(e) => setListPrice(Number(e.target.value))}
              required
            />
          </label>
          <label className="form-control">
            <span className="label-text">信号数量</span>
            <input
              type="number"
              min={1}
              className="input input-bordered"
              value={listSignals}
              onChange={(e) => setListSignals(Number(e.target.value))}
            />
          </label>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            上架
          </button>
        </form>
      ) : null}

      {tab === "wallet" ? (
        <form className="glass-card max-w-lg space-y-4 p-6" onSubmit={onCreditSubmit}>
          <p className="text-sm text-slate-500">
            当前声誉：<strong>{Number(score).toFixed(1)}</strong>
            {balance?.contribution_count != null ? (
              <span className="ml-2">（贡献 {balance.contribution_count} 次）</span>
            ) : null}
          </p>
          <label className="form-control">
            <span className="label-text">测试充值积分</span>
            <input
              type="number"
              min={1}
              className="input input-bordered"
              value={creditAmount}
              onChange={(e) => setCreditAmount(Number(e.target.value))}
            />
          </label>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            充值声誉
          </button>
        </form>
      ) : null}

      {tab === "runs" ? (
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
      ) : null}

      {tab === "governance" ? (
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
              治理阈值：赞成率 ≥{" "}
              {(workbench.stats.thresholds.majority * 100).toFixed(0)}%，法定人数{" "}
              {workbench.stats.thresholds.quorum}
            </p>
          ) : null}

          <div className="glass-card overflow-x-auto p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-semibold">Auto-Alpha 挖掘 → DAO 一键提案</h3>
              <button
                type="button"
                className="btn btn-outline btn-sm"
                disabled={busy}
                onClick={() => void onRunMining()}
              >
                运行挖掘
              </button>
            </div>
            <table className="table table-sm">
              <thead>
                <tr>
                  <th>Factor</th>
                  <th>表达式</th>
                  <th>IC</th>
                  <th>Sharpe</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {miningFactors.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center text-slate-500">
                      暂无挖掘因子（可先调用 POST /api/v1/alpha-mining/run）
                    </td>
                  </tr>
                ) : (
                  miningFactors.map((factor: MiningFactor) => (
                    <tr key={factor.factor_id}>
                      <td className="font-mono text-xs">{factor.factor_id}</td>
                      <td className="max-w-[10rem] truncate font-mono text-xs">
                        {factor.expression}
                      </td>
                      <td>{factor.ic_mean != null ? Number(factor.ic_mean).toFixed(3) : "—"}</td>
                      <td>{factor.sharpe != null ? Number(factor.sharpe).toFixed(2) : "—"}</td>
                      <td className="flex gap-1">
                        <button
                          type="button"
                          className="btn btn-primary btn-xs"
                          disabled={busy}
                          onClick={() => void onProposeMining(factor.factor_id)}
                        >
                          提案
                        </button>
                        <button
                          type="button"
                          className="btn btn-ghost btn-xs"
                          disabled={busy}
                          onClick={() => prefillFromMining(factor)}
                        >
                          填表
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="glass-card overflow-x-auto p-4">
            <h3 className="mb-3 font-semibold">MLflow 回测实验（关联提案）</h3>
            {!workbench?.mlflow?.available ? (
              <p className="text-sm text-slate-500">
                MLflow 未配置时可手动填写下方提案表单。
              </p>
            ) : null}
            <table className="table table-sm">
              <thead>
                <tr>
                  <th>实验</th>
                  <th>标的</th>
                  <th>策略</th>
                  <th>Sharpe</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {govMlflowRuns.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center text-slate-500">
                      暂无 MLflow 记录
                    </td>
                  </tr>
                ) : (
                  govMlflowRuns.map((run: MlflowRun) => (
                    <tr key={run.run_id}>
                      <td className="font-mono text-xs">{run.run_name}</td>
                      <td>{run.params?.symbol ?? "—"}</td>
                      <td>{run.params?.strategy_name ?? "—"}</td>
                      <td>
                        {run.metrics?.sharpe != null
                          ? Number(run.metrics.sharpe).toFixed(2)
                          : "—"}
                      </td>
                      <td className="flex gap-1">
                        <button
                          type="button"
                          className="btn btn-ghost btn-xs"
                          onClick={() => prefillFromRun(run)}
                        >
                          填表
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

          <form className="glass-card max-w-xl space-y-4 p-6" onSubmit={onGovSubmit}>
            <h3 className="font-semibold">提交因子提案</h3>
            <label className="form-control">
              <span className="label-text">Strategy ID</span>
              <input
                className="input input-bordered"
                value={govStrategyId}
                onChange={(e) => setGovStrategyId(e.target.value)}
                required
              />
            </label>
            <label className="form-control">
              <span className="label-text">表达式</span>
              <input
                className="input input-bordered font-mono text-sm"
                value={govExpression}
                onChange={(e) => setGovExpression(e.target.value)}
                placeholder="close / open - 1"
                required
              />
            </label>
            <label className="form-control">
              <span className="label-text">Sharpe（ZK 证明输入）</span>
              <input
                type="number"
                step="0.01"
                className="input input-bordered"
                value={govSharpe}
                onChange={(e) => setGovSharpe(Number(e.target.value))}
              />
            </label>
            {govMlflowRunId || govMiningFactorId ? (
              <p className="text-xs text-slate-500">
                关联：
                {govMlflowRunId ? (
                  <span className="ml-1 font-mono">MLflow {govMlflowRunId.slice(0, 8)}</span>
                ) : null}
                {govMiningFactorId ? (
                  <span className="ml-1 font-mono">挖掘 {govMiningFactorId}</span>
                ) : null}
              </p>
            ) : null}
            <button type="submit" className="btn btn-primary" disabled={busy}>
              提交提案
            </button>
          </form>

          <label className="form-control max-w-xl px-1">
            <span className="label-text">投票备注（可选）</span>
            <input
              className="input input-bordered input-sm"
              value={voteRationale}
              onChange={(e) => setVoteRationale(e.target.value)}
              placeholder="赞成/反对理由"
            />
          </label>

          <div className="glass-card overflow-x-auto p-4">
            <h3 className="mb-3 font-semibold">待决议提案</h3>
            {proposals.length > 0 ? (
              <div className="mb-4 max-w-xl">
                <GovernanceVoteFlow
                  proposal={proposals[0]}
                  majorityThreshold={workbench?.stats.thresholds?.majority}
                />
                <p className="mt-1 text-xs text-slate-500">
                  展示最新提案「{proposals[0].strategy_id}」投票进度；点击 ID 查看全部详情。
                </p>
              </div>
            ) : null}
            <table className="table table-sm">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>策略</th>
                  <th>表达式</th>
                  <th>关联</th>
                  <th>状态</th>
                  <th>票型</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {proposals.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center text-slate-500">
                      暂无提案（已持久化至 instance/alpha_proposals.json）
                    </td>
                  </tr>
                ) : (
                  proposals.map((item: AlphaGovernanceProposal) => (
                    <tr key={item.proposal_id}>
                      <td className="font-mono text-xs">
                        <button
                          type="button"
                          className="link link-primary"
                          onClick={() => setDetailProposalId(item.proposal_id)}
                        >
                          {item.proposal_id.slice(-8)}
                        </button>
                      </td>
                      <td>{item.strategy_id}</td>
                      <td className="max-w-[12rem] truncate font-mono text-xs">
                        {item.expression}
                      </td>
                      <td className="font-mono text-xs">
                        {item.mlflow_run_id
                          ? `mlf:${item.mlflow_run_id.slice(0, 6)}`
                          : item.mining_factor_id
                            ? `min:${item.mining_factor_id.slice(0, 8)}`
                            : "—"}
                      </td>
                      <td>
                        <span className="badge badge-outline">{item.status}</span>
                      </td>
                      <td>
                        {item.votes_for}/{item.votes_against}
                      </td>
                      <td className="flex gap-1">
                        <button
                          type="button"
                          className="btn btn-success btn-xs"
                          disabled={busy}
                          onClick={() => void onVote(item.proposal_id, true)}
                        >
                          赞成
                        </button>
                        <button
                          type="button"
                          className="btn btn-error btn-xs"
                          disabled={busy}
                          onClick={() => void onVote(item.proposal_id, false)}
                        >
                          反对
                        </button>
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
              <thead>
                <tr>
                  <th>提案</th>
                  <th>团队</th>
                  <th>立场</th>
                  <th>理由</th>
                  <th>时间</th>
                </tr>
              </thead>
              <tbody>
                {voteHistory.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="text-center text-slate-500">
                      暂无投票记录
                    </td>
                  </tr>
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
      ) : null}

      {toast ? (
        <div className="toast toast-end toast-top">
          <div className="alert alert-info text-sm shadow-lg">{toast}</div>
        </div>
      ) : null}

      <GovernanceProposalModal
        proposalId={detailProposalId}
        onClose={() => setDetailProposalId(null)}
      />

      <MlflowRunModal
        runId={detailRunId}
        onClose={() => setDetailRunId(null)}
        onPrefillGovernance={prefillFromRun}
        onOpenProposal={(proposalId) => setDetailProposalId(proposalId)}
      />

      <a className="btn btn-outline btn-sm" href="/alpha-marketplace">
        打开经典版 Marketplace
      </a>
    </div>
  );
}
