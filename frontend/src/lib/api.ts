/**
 * API client aligned with Quant Atlas v1/v2 response envelopes.
 */

import type { ExperimentDetail, ExperimentSummary } from "../types/experiment";
import type {
  TimeseriesHealth,
  TimeseriesSyncHistory,
} from "../types/timeseries";
import type {
  BacktestCompareResult,
  BacktestRequest,
  BacktestResult,
  MarketplaceListing,
  MarketplaceOrder,
  WizardPreviewResult,
} from "../types/backtest";
import type { MlflowModelVersion, MlflowRun, MlflowTrackingConfig } from "../types/mlflow";
import type { SignalFlagPoolResponse, SignalFlagScanResponse } from "../types/signalflag";
import type { StockDetailPayload, TradePlan } from "../types/stock";
import type { AlphaFactoryStatus, AlphaKnowledge, AlphaFactorItem, ValidateResult, WeeklyStatus, PaperTradingStatus } from "../types/alpha";
import type { WorkbenchSnapshot } from "../types/workbench";

export type ApiEnvelope<T> = {
  ok?: boolean;
  success?: boolean;
  data?: T;
  meta?: Record<string, unknown>;
  error?: { message?: string; code?: string };
};

function unwrap<T>(json: ApiEnvelope<T> | T): T {
  if (json && typeof json === "object" && "data" in json) {
    const envelope = json as ApiEnvelope<T>;
    if (envelope.data !== undefined) {
      return envelope.data;
    }
  }
  return json as T;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status = 0) {
    super(message);
    this.status = status;
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers ?? {});
  headers.set("Accept", "application/json");
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, {
    ...options,
    credentials: "same-origin",
    headers,
  });

  const json = (await response.json().catch(() => ({}))) as ApiEnvelope<T>;
  if (!response.ok) {
    const message = json?.error?.message || `\u8bf7\u6c42\u5931\u8d25 (${response.status})`;
    throw new ApiError(message, response.status);
  }
  return unwrap<T>(json);
}

/** Session-cookie friendly v1 API (\u64cd\u76d8\u53f0\u7b49). */
export async function apiFetchV1<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const normalized = path.startsWith("/api/v1") ? path : `/api/v1${path}`;
  return apiFetch<T>(normalized, options);
}

export async function probeSessionAuth(): Promise<boolean> {
  const response = await fetch(
    "/api/v1/daily-workbench?market=CN&watchlist_limit=1",
    { credentials: "same-origin", headers: { Accept: "application/json" } },
  );
  return response.status !== 401;
}

export async function loginWithPassword(
  username: string,
  password: string,
): Promise<{ access_token: string; expires_in: number }> {
  const data = await apiFetch<{ access_token: string; expires_in: number }>(
    "/api/v2/auth/token",
    {
      method: "POST",
      body: JSON.stringify({ username, password }),
    },
  );
  // JWT is now set as httpOnly cookie by the server; no localStorage needed
  return data;
}

/** Read CSRF token from classic /login page (session cookie + meta/hidden field). */
async function fetchWebCsrfToken(): Promise<string> {
  const response = await fetch("/login", {
    credentials: "same-origin",
    headers: { Accept: "text/html" },
  });
  if (!response.ok) {
    throw new ApiError("\u65e0\u6cd5\u52a0\u8f7d\u767b\u5f55\u9875", response.status);
  }
  const html = await response.text();
  const meta = html.match(/name="csrf-token"\s+content="([^"]+)"/i);
  if (meta?.[1]) {
    return meta[1];
  }
  const hidden = html.match(/name="csrf_token"\s+value="([^"]+)"/i);
  if (hidden?.[1]) {
    return hidden[1];
  }
  throw new ApiError("\u65e0\u6cd5\u83b7\u53d6 CSRF token");
}

/** Classic Flask-Login session (no JWT required). */
export async function loginWithSession(
  username: string,
  password: string,
): Promise<boolean> {
  const csrfToken = await fetchWebCsrfToken();
  const body = new URLSearchParams({
    username,
    password,
    csrf_token: csrfToken,
  });
  const response = await fetch("/login", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "X-CSRF-Token": csrfToken,
    },
    body,
    redirect: "manual",
  });
  if (response.status === 302 || response.status === 303) {
    return true;
  }
  if (response.ok) {
    return probeSessionAuth();
  }
  throw new ApiError("\u7528\u6237\u540d\u6216\u5bc6\u7801\u9519\u8bef", response.status);
}

export async function fetchCurrentUser(): Promise<{
  user_id: number;
  username: string;
  role: string;
}> {
  return apiFetch("/api/v2/auth/me");
}

export async function fetchDailyWorkbench(
  market = "CN",
  watchlistLimit = 12,
): Promise<WorkbenchSnapshot> {
  const query = new URLSearchParams({ market, watchlist_limit: String(watchlistLimit) });
  return apiFetchV1<WorkbenchSnapshot>(`/daily-workbench?${query}`);
}

export async function fetchMarketPanorama(): Promise<{ data: import("../types/market").MarketPanorama }> {
  return apiFetch<{ data: import("../types/market").MarketPanorama }>("/api/v1/markets/CN/panorama");
}

export async function fetchMarketSentiment(): Promise<{ data: { score?: number; level?: string; description?: string } }> {
  return apiFetch<{ data: { score?: number; level?: string; description?: string } }>("/api/v1/markets/CN/sentiment");
}

export async function fetchMarketHeadlines(limit = 40): Promise<{ data: { items?: Array<{ title?: string; summary?: string; source?: string }> } }> {
  return apiFetch(`/api/v1/markets/CN/headlines?limit=${limit}`);
}

export async function fetchAlphaFactoryStatus(): Promise<AlphaFactoryStatus> {
  const data = await apiFetch<{ data?: AlphaFactoryStatus }>("/api/v1/alpha-factory/status");
  return (data as AlphaFactoryStatus);
}

export async function fetchAlphaKnowledge(): Promise<AlphaKnowledge> {
  return apiFetchV1<AlphaKnowledge>("/alpha-factory/knowledge/alphas");
}

export async function fetchAlphaFactors(): Promise<{ items: AlphaFactorItem[]; total: number }> {
  return apiFetchV1("/alpha-factory/factors");
}

export async function fetchFactorRepository(params: {
  page?: number;
  limit?: number;
  regime?: string;
  search?: string;
}): Promise<{
  factors: AlphaFactorItem[];
  total: number;
  page: number;
  limit: number;
  avg_sharpe?: number;
  active_count?: number;
}> {
  const q = new URLSearchParams();
  if (params.page) q.set("page", String(params.page));
  if (params.limit) q.set("limit", String(params.limit));
  if (params.regime) q.set("regime", params.regime);
  if (params.search) q.set("search", params.search);
  return apiFetchV1(`/alpha-factory/factors?${q}`);
}

export async function fetchFactorLineage(params: {
  limit?: number;
}): Promise<{
  nodes: Array<{
    id: string;
    factor_id?: string;
    name?: string;
    type?: string;
    ic?: number;
    ic_proxy?: boolean;
    full_name?: string;
    experiment_id?: string;
    status?: string;
  }>;
  links: Array<{ source: string; target: string }>;
}> {
  const q = new URLSearchParams();
  if (params.limit) q.set("limit", String(params.limit));
  return apiFetchV1(`/alpha-factory/lineage?${q}`);
}

export async function fetchFactorDetail(factorId: string): Promise<{
  factor_id: string;
  formula?: string;
  sharpe_ratio?: number;
  max_drawdown?: number;
  ic_mean?: number;
  regime?: string;
  backtest_result?: {
    annual_return?: number;
    sharpe_ratio?: number;
    win_rate?: number;
    profit_loss_ratio?: number;
    max_drawdown?: number;
    trade_count?: number;
  };
  ic_series?: Array<{ date: string; ic: number }>;
  correlations?: Array<{ factor_id: string; name?: string; value: number }>;
  created_at?: string;
  data_range?: string;
  source?: string;
}> {
  return apiFetchV1(`/alpha-factory/factors?factor_id=${encodeURIComponent(factorId)}`);
}

export async function evolveFactor(factorId: string): Promise<{ status?: string; job_id?: string }> {
  return apiFetchV1("/alpha-factory/evolve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ factor_id: factorId }),
  });
}

export async function submitFactorToVault(factorId: string): Promise<{ factor_id?: string }> {
  return apiFetchV1("/alpha-factory/experiment/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ factor_id: factorId, save_to_vault: true }),
  });
}

export async function analyzeExperiment(experimentId: string): Promise<{ status?: string }> {
  return apiFetchV1("/alpha-factory/experiment/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ experiment_id: experimentId }),
  });
}

export async function validateAlphaFormula(formula: string): Promise<ValidateResult> {
  const data = await apiFetch<{ data?: ValidateResult }>(
    `/api/v1/alpha-factory/validate?formula=${encodeURIComponent(formula)}`,
  );
  return (data as ValidateResult);
}

export async function submitRdAgentRun(payload: {
  formula: string;
  goal: string;
  goal_label: string;
  search_space?: string;
  data_scope?: { start_date?: string; end_date?: string };
}): Promise<{ run_id?: string; job_id?: string; poll_url?: string; task_id?: string }> {
  const data = await apiFetch<{
    data?: { run_id?: string; job_id?: string; poll_url?: string; task_id?: string };
  }>("/api/v1/rd-agent/runs", { method: "POST", body: JSON.stringify(payload) });
  const r = (data as any)?.data || data;
  return {
    run_id: r.run_id,
    job_id: r.job_id,
    poll_url: r.poll_url,
    task_id: r.task_id,
  };
}

export async function fetchModelRecommendation(
  symbols?: string,
  market_cap?: string,
  prefer_explainability?: boolean,
): Promise<{ recommendation?: string }> {
  const params = new URLSearchParams();
  if (symbols) params.set("symbols", symbols);
  if (market_cap) params.set("market_cap", market_cap);
  if (prefer_explainability) params.set("prefer_explainability", "true");
  const data = await apiFetch<{ data?: { recommendation?: string } }>(
    `/api/v1/alpha-factory/model/meta-learner?${params}`,
  );
  return (data as any)?.data || data || {};
}

export async function fetchWeeklyStatus(): Promise<WeeklyStatus> {
  const data = await apiFetch<{ data?: WeeklyStatus }>("/api/v1/alpha-factory/weekly");
  return (data as any)?.data || data || {};
}

export async function fetchPaperTradingStatus(): Promise<PaperTradingStatus> {
  const data = await apiFetch<{ data?: PaperTradingStatus }>("/api/v1/alpha-factory/paper-trading");
  return (data as any)?.data || data || {};
}

export async function submitPaperTrading(modelId: string): Promise<{ run_id?: string }> {
  const data = await apiFetch<{ data?: { run_id?: string } }>("/api/v1/alpha-factory/paper-trading", {
    method: "POST",
    body: JSON.stringify({ model_id: modelId, backtest_result: { total_return: 0.1 } }),
  });
  return (data as any)?.data || data || {};
}


export async function fetchTimeseriesHealth(): Promise<TimeseriesHealth> {
  return apiFetchV1("/data/timeseries-health");
}

export async function fetchTimeseriesSyncHistory(
  limit = 5,
  source = "celery_beat",
): Promise<TimeseriesSyncHistory> {
  const query = new URLSearchParams({
    limit: String(limit),
    source,
  });
  return apiFetchV1(`/data/timeseries-sync-history?${query}`);
}

export async function fetchStock(
  symbol: string,
  market = "CN",
): Promise<StockDetailPayload> {
  return apiFetch(`/api/v2/stocks/${encodeURIComponent(symbol)}?market=${market}`);
}

export async function fetchStockHistory(
  symbol: string,
  market = "CN",
  count = 120,
): Promise<unknown> {
  const query = new URLSearchParams({
    market,
    count: String(count),
  });
  return apiFetch(`/api/v2/stocks/${encodeURIComponent(symbol)}/history?${query}`);
}

export async function fetchHealth(): Promise<Record<string, unknown>> {
  return apiFetch("/api/v2/health");
}

export async function fetchTradePlan(
  symbol: string,
  market = "CN",
  params?: {
    account_equity?: number;
    cash_available?: number;
    risk_per_trade_pct?: number;
    max_position_pct?: number;
  },
): Promise<TradePlan> {
  const query = new URLSearchParams({ symbol, market });
  if (params?.account_equity) query.set("account_equity", String(params.account_equity));
  if (params?.cash_available) query.set("cash_available", String(params.cash_available));
  if (params?.risk_per_trade_pct) query.set("risk_per_trade_pct", String(params.risk_per_trade_pct));
  if (params?.max_position_pct) query.set("max_position_pct", String(params.max_position_pct));
  return apiFetchV1<TradePlan>(`/trade-plan?${query}`);
}

export async function listStrategies(): Promise<unknown> {
  return apiFetch("/api/v2/strategies/");
}

type BacktestAsyncEnvelope = {
  status?: string;
  mode?: string;
  task_id?: string;
  result?: BacktestResult;
};

type CeleryTaskStatus = {
  ok?: boolean;
  state?: string;
  ready?: boolean;
  successful?: boolean;
  failed?: boolean;
  result?: BacktestResult | string;
  error?: string;
};

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export async function fetchCeleryTaskStatus(taskId: string): Promise<CeleryTaskStatus> {
  return apiFetchV1(`/system/celery/task/${encodeURIComponent(taskId)}`);
}

async function waitForBacktestTask(taskId: string): Promise<BacktestResult> {
  for (let attempt = 0; attempt < 45; attempt += 1) {
    const status = await fetchCeleryTaskStatus(taskId);
    if (status.ready) {
      if (status.successful && status.result && typeof status.result === "object") {
        return status.result as BacktestResult;
      }
      throw new ApiError(
        typeof status.result === "string" ? status.result : "\u5f02\u6b65\u56de\u6d4b\u5931\u8d25",
      );
    }
    await sleep(2000);
  }
  throw new ApiError("\u5f02\u6b65\u56de\u6d4b\u8d85\u65f6\uff0c\u8bf7\u7a0d\u540e\u5728\u4efb\u52a1\u4e2d\u5fc3\u67e5\u770b");
}

export async function runBacktest(
  payload: BacktestRequest,
  asyncMode = false,
): Promise<BacktestResult> {
  const suffix = asyncMode ? "?async=1" : "";
  const data = await apiFetch<BacktestResult | BacktestAsyncEnvelope>(
    `/api/v2/strategies/backtest${suffix}`,
    {
      method: "POST",
      body: JSON.stringify({
        symbol: payload.symbol,
        strategy_name: payload.strategy_name,
        strategy: payload.strategy_name,
        start: payload.start,
        end: payload.end,
        initial_capital: payload.initial_capital,
      }),
    },
  );
  if (data && typeof data === "object") {
    const envelope = data as BacktestAsyncEnvelope;
    if (envelope.status === "queued" && envelope.task_id) {
      return waitForBacktestTask(envelope.task_id);
    }
    if (envelope.result && typeof envelope.result === "object") {
      return envelope.result;
    }
  }
  return data as BacktestResult;
}

export async function compareBacktests(payload: {
  symbol: string;
  strategies: string[];
  start: string;
  end: string;
  initial_capital?: number;
}): Promise<BacktestCompareResult> {
  return apiFetch<BacktestCompareResult>("/api/v2/strategies/backtest/compare", {
    method: "POST",
    body: JSON.stringify({
      symbol: payload.symbol,
      strategies: payload.strategies,
      start: payload.start,
      end: payload.end,
      initial_capital: payload.initial_capital ?? 100_000,
    }),
  });
}

export async function fetchWizardTemplates(): Promise<{
  templates?: Array<{ id: string; name: string; is_recommended?: boolean }>;
}> {
  const response = await fetch("/api/v1/strategy/wizard/templates", {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new ApiError(`\u6a21\u677f\u52a0\u8f7d\u5931\u8d25 (${response.status})`, response.status);
  }
  return response.json();
}

export async function previewStrategy(
  templateId: string,
  params: Record<string, unknown>,
  symbol: string,
  market = "CN",
): Promise<WizardPreviewResult> {
  const response = await fetch("/api/v1/strategy/wizard/preview", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      template_id: templateId,
      params: { ...params, symbol, market },
    }),
  });
  const json = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(
      (json as { error?: string }).error || `\u9884\u89c8\u5931\u8d25 (${response.status})`,
      response.status,
    );
  }
  return json as WizardPreviewResult;
}

export async function fetchReputationBalance(): Promise<{
  reputation_score?: number;
  contribution_count?: number;
}> {
  return apiFetchV1("/alpha/reputation/balance");
}

export async function fetchMarketplaceListings(
  active = true,
): Promise<MarketplaceListing[]> {
  const data = await apiFetchV1<MarketplaceListing[] | { listings?: MarketplaceListing[] }>(
    `/alpha/marketplace/listings?active=${active}`,
  );
  if (Array.isArray(data)) return data;
  return data.listings ?? [];
}

export async function fetchMarketplaceOrders(): Promise<MarketplaceOrder[]> {
  const data = await apiFetchV1<{ orders?: MarketplaceOrder[] }>(
    "/alpha/marketplace/orders",
  );
  return data.orders ?? [];
}

export async function contributeToListing(listingId: string): Promise<{ order_id?: string }> {
  return apiFetchV1("/alpha/marketplace/contribute", {
    method: "POST",
    body: JSON.stringify({ listing_id: listingId }),
  });
}

export async function listMarketplaceToken(payload: {
  token_id: string;
  reputation_cost: number;
  signal_count: number;
}): Promise<{ listing_id?: string }> {
  return apiFetchV1("/alpha/marketplace/list", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function cancelMarketplaceOrder(orderId: string): Promise<void> {
  await apiFetchV1(`/alpha/marketplace/order/${encodeURIComponent(orderId)}/cancel`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function creditReputation(amount: number): Promise<void> {
  await apiFetchV1("/alpha/wallet/credit", {
    method: "POST",
    body: JSON.stringify({ amount }),
  });
}

export async function fetchMlflowRuns(limit = 20): Promise<{
  runs: MlflowRun[];
  available: boolean;
  count: number;
}> {
  return apiFetchV1(`/mlflow/runs?limit=${limit}`);
}

export async function fetchMlflowRun(runId: string): Promise<{
  run: MlflowRun;
  available: boolean;
  linked_proposals?: AlphaGovernanceProposal[];
}> {
  return apiFetchV1(`/mlflow/runs/${encodeURIComponent(runId)}`);
}

export async function fetchMlflowModels(limit = 20): Promise<{
  models: MlflowModelVersion[];
  available: boolean;
  count: number;
}> {
  return apiFetchV1(`/mlflow/models?limit=${limit}`);
}

export async function fetchMlflowStatus(): Promise<{
  available: boolean;
  tracking_uri?: string | null;
  experiment?: string;
  register_models?: boolean;
}> {
  return apiFetchV1("/mlflow/status");
}

export async function fetchExperiments(): Promise<{ experiments: ExperimentSummary[] }> {
  return apiFetch<{ experiments: ExperimentSummary[] }>("/api/v1/experiments");
}

export async function fetchExperiment(expId: string): Promise<ExperimentDetail> {
  return apiFetch<ExperimentDetail>(`/api/v1/experiments/${encodeURIComponent(expId)}`);
}

export type GovernanceTimelineEvent = {
  type: string;
  at: string;
  actor?: string;
  summary: string;
};

export type AlphaGovernanceProposal = {
  proposal_id: string;
  strategy_id: string;
  manager_id: string;
  expression: string;
  status: string;
  votes_for: number;
  votes_against: number;
  submitted_at: string;
  performance_metrics?: Record<string, number>;
  mlflow_run_id?: string;
  mining_factor_id?: string;
  tally?: Record<string, unknown>;
  vote_history?: AlphaGovernanceVote[];
  timeline?: GovernanceTimelineEvent[];
};

export type AlphaGovernanceVote = {
  voter_team: string;
  proposal_id: string;
  approve: boolean;
  rationale?: string;
  voted_at: string;
};

export async function fetchGovernanceStats(): Promise<{
  stats: {
    proposals: number;
    active_factors: number;
    votes: number;
    thresholds?: { majority: number; quorum: number };
  };
  active_factors: Array<Record<string, unknown>>;
}> {
  return apiFetchV1("/alpha/governance/stats");
}

export async function fetchGovernanceProposals(): Promise<AlphaGovernanceProposal[]> {
  const data = await apiFetchV1<{ proposals?: AlphaGovernanceProposal[] }>(
    "/alpha/governance/proposals",
  );
  return data.proposals ?? [];
}

export async function fetchGovernanceProposal(
  proposalId: string,
): Promise<AlphaGovernanceProposal> {
  const data = await apiFetchV1<{ proposal?: AlphaGovernanceProposal }>(
    `/alpha/governance/proposals/${encodeURIComponent(proposalId)}`,
  );
  if (!data.proposal) {
    throw new ApiError("\u63d0\u6848\u4e0d\u5b58\u5728");
  }
  return data.proposal;
}

export async function fetchGovernanceVotes(
  proposalId?: string,
): Promise<AlphaGovernanceVote[]> {
  const suffix = proposalId
    ? `?proposal_id=${encodeURIComponent(proposalId)}`
    : "";
  const data = await apiFetchV1<{ votes?: AlphaGovernanceVote[] }>(
    `/alpha/governance/votes${suffix}`,
  );
  return data.votes ?? [];
}

export async function submitGovernanceProposal(payload: {
  strategy_id: string;
  expression: string;
  performance_metrics?: Record<string, number>;
  manager_id?: string;
  mlflow_run_id?: string;
  mining_factor_id?: string;
}): Promise<{ proposal_id: string }> {
  return apiFetchV1("/alpha/governance/proposals", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function castGovernanceVote(payload: {
  proposal_id: string;
  approve: boolean;
  rationale?: string;
}): Promise<{ proposal_id: string; tally: Record<string, unknown> }> {
  return apiFetchV1("/alpha/governance/vote", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Clear httpOnly JWT cookie + Flask-Login session. */
export async function logoutSession(): Promise<void> {
  try {
    await fetch("/api/v2/auth/logoff", { method: "POST", credentials: "same-origin" });
  } catch {
    // server may be unavailable; still clear session below
  }
  await fetch("/logout", { credentials: "same-origin", redirect: "manual" });
}

export type MiningFactor = {
  factor_id: string;
  expression: string;
  ic_mean?: number;
  sharpe?: number;
  complexity?: number;
  generation?: number;
};

export type GovernanceWorkbench = {
  stats: {
    proposals: number;
    active_factors: number;
    votes: number;
    thresholds?: { majority: number; quorum: number };
  };
  active_factors: Array<Record<string, unknown>>;
  proposals: AlphaGovernanceProposal[];
  votes: AlphaGovernanceVote[];
  mlflow: {
    available: boolean;
    config?: MlflowTrackingConfig;
    runs: MlflowRun[];
  };
  mining_factors: MiningFactor[];
};

export async function fetchGovernanceWorkbench(
  limit = 10,
): Promise<GovernanceWorkbench> {
  return apiFetchV1(`/alpha/governance/workbench?limit=${limit}`);
}

export async function proposeMiningFactorToDao(
  factorId: string,
): Promise<{ proposal_id?: string; factor_id?: string; error?: string }> {
  return apiFetchV1(`/alpha-mining/factors/${encodeURIComponent(factorId)}/propose`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function runAlphaMining(payload?: {
  generations?: number;
  population_size?: number;
}): Promise<{
  generations_run: number;
  population_size: number;
  top_factors: MiningFactor[];
}> {
  return apiFetchV1("/alpha-mining/run", {
    method: "POST",
    body: JSON.stringify(payload ?? {}),
  });
}

export async function fetchSignalFlagPool(date: string): Promise<SignalFlagPoolResponse> {
  const data = await apiFetchV1<SignalFlagPoolResponse>(`/signal-flag/pool?date=${encodeURIComponent(date)}`);
  return data;
}

export async function runSignalFlagScan(date?: string): Promise<SignalFlagScanResponse> {
  const data = await apiFetchV1<SignalFlagScanResponse>("/signal-flag/scan", {
    method: "POST",
    body: JSON.stringify({ pool_date: date || undefined, max_stocks: 800, lookback_days: 160 }),
  });
  return data;
}
