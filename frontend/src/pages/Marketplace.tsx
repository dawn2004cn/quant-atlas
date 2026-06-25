import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import useSWR from "swr";
import { GovernanceProposalModal } from "../components/governance/GovernanceProposalModal";
import { MlflowRunModal } from "../components/mlflow/MlflowRunModal";
import { MarketplaceHeader } from "../components/marketplace/MarketplaceHeader";
import { MarketplaceBrowseTab } from "../components/marketplace/MarketplaceBrowseTab";
import { MarketplaceOrdersTab } from "../components/marketplace/MarketplaceOrdersTab";
import { MarketplaceRunsTab } from "../components/marketplace/MarketplaceRunsTab";
import { MarketplaceGovernanceTab } from "../components/marketplace/MarketplaceGovernanceTab";
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
import type { MiningFactor } from "../lib/api";
import type { } from "../types/backtest";
import type { MlflowRun } from "../types/mlflow";

export type MpTab = "browse" | "orders" | "list" | "wallet" | "runs" | "governance";

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
      <MarketplaceHeader
        score={score}
        orderCount={orders.length}
        listingCount={listings.length}
        activeTab={tab}
        onTabChange={setTab}
      />

      {tab === "browse" ? (
        <MarketplaceBrowseTab
          listings={listings}
          busy={busy}
          onContribute={onContribute}
        />
      ) : null}

      {tab === "orders" ? (
        <MarketplaceOrdersTab
          orders={orders}
          busy={busy}
          onCancel={onCancel}
        />
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
        <MarketplaceRunsTab
          mlflowData={mlflowData}
          mlflowModels={mlflowModels}
          mlflowConfig={mlflowConfig}
          busy={busy}
          prefillFromRun={prefillFromRun}
          setDetailRunId={setDetailRunId}
          setDetailProposalId={setDetailProposalId}
        />
      ) : null}

      {tab === "governance" ? (
        <MarketplaceGovernanceTab
          workbench={workbench}
          govLoading={govLoading}
          busy={busy}
          govStrategyId={govStrategyId}
          govExpression={govExpression}
          govSharpe={govSharpe}
          govMlflowRunId={govMlflowRunId}
          govMiningFactorId={govMiningFactorId}
          voteRationale={voteRationale}
          mlflowConfig={mlflowConfig}
          miningFactors={miningFactors}
          proposals={proposals}
          voteHistory={voteHistory}
          govMlflowRuns={govMlflowRuns}
          onGovSubmit={onGovSubmit}
          onVote={onVote}
          onRunMining={onRunMining}
          onProposeMining={onProposeMining}
          prefillFromRun={prefillFromRun}
          prefillFromMining={prefillFromMining}
          setDetailProposalId={setDetailProposalId}
          setDetailRunId={setDetailRunId}
          setGovStrategyId={setGovStrategyId}
          setGovExpression={setGovExpression}
          setGovSharpe={setGovSharpe}
          setGovMlflowRunId={setGovMlflowRunId}
          setGovMiningFactorId={setGovMiningFactorId}
          setVoteRationale={setVoteRationale}
        />
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