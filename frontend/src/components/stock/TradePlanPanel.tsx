import { useState } from "react";
import useSWR from "swr";
import type { TradePlan as TradePlanType } from "../../types/stock";

function fmt(v: number | undefined | null, decimals = 2): string {
  if (v == null || Number.isNaN(Number(v))) return "--";
  return Number(v).toFixed(decimals);
}

function cls(v: number | undefined | null): string {
  if (v == null) return "";
  return v >= 0 ? "text-green-600" : "text-red-500";
}

function esc(t: string | undefined | null): string {
  if (!t) return "";
  return t
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function TradePlanPanel({
  symbol,
  market,
}: {
  symbol: string;
  market: string;
}) {
  const [accountEquity] = useState(100000);
  const [riskPct] = useState(1.0);
  const [maxPosPct] = useState(15.0);

  const query = new URLSearchParams({
    symbol,
    market,
    account_equity: String(accountEquity),
    risk_per_trade_pct: String(riskPct),
    max_position_pct: String(maxPosPct),
  });

  const { data, error, isLoading, mutate } = useSWR<TradePlanType>(
    ["trade-plan", symbol, market, accountEquity, riskPct, maxPosPct],
    () =>
      fetch(`/api/v1/trade-plan?${query}`, { credentials: "same-origin" })
        .then((r) => r.json())
        .then((d) => d.data ?? d),
    { revalidateOnFocus: false },
  );

  const plan = data?.plan ?? {};
  const cards = data?.risk_cards ?? [];
  const scenarios = data?.scenario_analysis ?? [];
  const warnings = data?.soft_warnings ?? [];
  const riskCheck = data?.risk_check ?? {};

  return (
    <section className="glass-card p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">买卖计划</h3>
        <button
          className="btn btn-ghost btn-sm"
          onClick={() => void mutate()}
          disabled={isLoading}
        >
          {isLoading ? "加载中…" : "刷新"}
        </button>
      </div>

      {error && (
        <div className="alert alert-error text-sm">
          交易计划加载失败：{String(error)}
        </div>
      )}

      {isLoading && !data && (
        <div className="text-sm text-slate-500">生成交易计划…</div>
      )}

      {data && (
        <>
          {/* Price card */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div>
              <div className="text-xs text-slate-500">入场价</div>
              <div className="text-xl font-bold">¥{fmt(plan.entry_price)}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">止损价</div>
              <div className="text-xl font-bold text-red-500">
                ¥{fmt(plan.stop_loss)}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">目标价</div>
              <div className="text-xl font-bold text-green-600">
                ¥{fmt(plan.target_price)}
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">建议股数</div>
              <div className="text-xl font-bold">
                {fmt(plan.recommended_shares, 0)} 股
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">仓位占比</div>
              <div className="text-xl font-bold">
                {fmt(plan.position_weight_pct)}%
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">盈亏比</div>
              <div className="text-xl font-bold">
                {fmt(plan.risk_reward_ratio)}
              </div>
            </div>
          </div>

          {/* Risk check badge */}
          <div className="flex items-center gap-2">
            <span
              className={`badge ${riskCheck.allowed === false ? "badge-error" : "badge-success"}`}
            >
              {riskCheck.allowed === false ? "风控未通过" : "风控预检通过"}
            </span>
            <span className="text-xs text-slate-500">
              {riskCheck.reason || "基于当前参数生成计划"}
            </span>
          </div>

          {/* Soft warnings */}
          {warnings.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm space-y-1">
              <strong className="text-amber-800">决策副驾驶</strong>
              {warnings.map((w, i) => (
                <div key={i} className="text-amber-700">
                  ⚠ {w.message}
                </div>
              ))}
            </div>
          )}

          {/* Buy reasons + failure conditions + execution notes */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="border rounded-lg p-3">
              <strong className="text-sm">买入理由</strong>
              <ul className="mt-2 space-y-1 text-sm text-slate-600">
                {(plan.buy_reason ?? []).map((r, i) => (
                  <li key={i}>• {esc(r)}</li>
                ))}
                {(plan.buy_reason ?? []).length === 0 && (
                  <li className="text-slate-400">暂无</li>
                )}
              </ul>
            </div>

            <div className="border rounded-lg p-3">
              <strong className="text-sm">失效条件</strong>
              <ul className="mt-2 space-y-1 text-sm text-slate-600">
                {(plan.failure_conditions ?? []).map((f, i) => (
                  <li key={i}>• {esc(f)}</li>
                ))}
                {(plan.failure_conditions ?? []).length === 0 && (
                  <li className="text-slate-400">暂无</li>
                )}
              </ul>
            </div>

            <div className="border rounded-lg p-3">
              <strong className="text-sm">执行备注</strong>
              <ul className="mt-2 space-y-1 text-sm text-slate-600">
                {(plan.execution_notes ?? []).map((n, i) => (
                  <li key={i}>• {esc(n)}</li>
                ))}
                {(plan.execution_notes ?? []).length === 0 && (
                  <li className="text-slate-400">暂无</li>
                )}
              </ul>
            </div>
          </div>

          {/* Risk cards */}
          {cards.length > 0 && (
            <div>
              <strong className="text-sm">风险卡片</strong>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-2">
                {cards.map((card, i) => (
                  <div
                    key={i}
                    className={`border rounded-lg p-3 ${
                      card.level === "high"
                        ? "border-red-200 bg-red-50"
                        : card.level === "medium"
                          ? "border-amber-200 bg-amber-50"
                          : "border-slate-200"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <strong className="text-sm">{card.title}</strong>
                      <span className="badge badge-ghost badge-xs">
                        {card.level}
                      </span>
                    </div>
                    <div className="text-xs text-slate-600 mt-1">
                      {card.content}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Scenario analysis */}
          {scenarios.length > 0 && (
            <div>
              <strong className="text-sm">情景推演</strong>
              <div className="overflow-x-auto mt-2">
                <table className="table table-sm">
                  <thead>
                    <tr>
                      <th>情景</th>
                      <th>价格</th>
                      <th>盈亏</th>
                      <th>账户影响</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scenarios.map((s, i) => (
                      <tr key={i}>
                        <td>
                          {esc(s.name)}{" "}
                          {s.is_worst_case && (
                            <span className="badge badge-error badge-xs">最差</span>
                          )}
                        </td>
                        <td>¥{fmt(s.price)}</td>
                        <td className={cls(s.pnl)}>
                          {fmt(s.pnl)} 元
                        </td>
                        <td className={cls(s.account_impact_pct)}>
                          {fmt(s.account_impact_pct)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}