import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetchV1 } from "../lib/api";
import { markOnboardingCompleted } from "../lib/onboarding";

type PersonaChoice = {
  id: string;
  title: string;
  blurb: string;
  risk_tolerance: number;
  experience_score: number;
  trading_frequency: "low" | "medium" | "high";
  nextHint: string;
};

const CHOICES: PersonaChoice[] = [
  {
    id: "novice",
    title: "稳健入门",
    blurb: "少看复杂工具，先盯自选、晨报与风险提示。",
    risk_tolerance: 0.25,
    experience_score: 0.15,
    trading_frequency: "low",
    nextHint: "推荐：自选晨报 → 今日操盘台",
  },
  {
    id: "day_trader",
    title: "活跃交易",
    blurb: "关注盘面异动、信号与仓位预检，节奏更快。",
    risk_tolerance: 0.55,
    experience_score: 0.4,
    trading_frequency: "high",
    nextHint: "推荐：市场全景 → 信号旗 → 自选",
  },
  {
    id: "strategist",
    title: "策略研究",
    blurb: "回测、因子与研究闭环优先，工具面更全。",
    risk_tolerance: 0.6,
    experience_score: 0.75,
    trading_frequency: "medium",
    nextHint: "推荐：策略向导 → 回测 → 因子库",
  },
];

export function OnboardingPage() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function finish(choice: PersonaChoice | null, skip: boolean) {
    setBusy(true);
    setError(null);
    try {
      if (choice && !skip) {
        await apiFetchV1("/user/persona", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            risk_tolerance: choice.risk_tolerance,
            experience_score: choice.experience_score,
            trading_frequency: choice.trading_frequency,
          }),
        });
      }
      markOnboardingCompleted();
      navigate(choice?.id === "strategist" ? "/strategy-wizard" : "/", { replace: true });
    } catch (err) {
      // Still mark local completion so users are not stuck if API is down
      markOnboardingCompleted();
      setError(err instanceof Error ? err.message : "保存失败，已跳过引导");
      navigate("/", { replace: true });
    } finally {
      setBusy(false);
    }
  }

  const active = CHOICES.find((c) => c.id === selected) ?? null;

  return (
    <div className="mx-auto max-w-[720px] space-y-6 py-4">
      <div>
        <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-zinc-500">Welcome</div>
        <h1 className="mt-0.5 text-2xl font-bold tracking-tight text-zinc-100">你更接近哪种用法？</h1>
        <p className="mt-2 text-sm text-zinc-500">
          选一项即可。我们会据此调整默认入口密度；之后可在个人中心再次调整。
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {CHOICES.map((c) => {
          const on = selected === c.id;
          return (
            <button
              key={c.id}
              type="button"
              disabled={busy}
              onClick={() => setSelected(c.id)}
              className={`rounded-xl p-4 text-left transition-colors ring-1 ${
                on
                  ? "bg-emerald-500/10 ring-emerald-500/40"
                  : "bg-zinc-900/50 ring-zinc-800/60 hover:bg-zinc-800/40"
              }`}
            >
              <div className="text-sm font-semibold text-zinc-100">{c.title}</div>
              <p className="mt-2 text-xs leading-relaxed text-zinc-400">{c.blurb}</p>
            </button>
          );
        })}
      </div>

      {active ? (
        <p className="text-xs text-emerald-400/90">{active.nextHint}</p>
      ) : (
        <p className="text-xs text-zinc-600">点选一张卡片后继续。</p>
      )}

      {error ? <p className="text-sm text-rose-400">{error}</p> : null}

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={busy || !active}
          onClick={() => active && void finish(active, false)}
          className="rounded-lg bg-emerald-500/15 px-4 py-2 text-sm font-semibold text-emerald-400 ring-1 ring-emerald-500/30 disabled:opacity-40"
        >
          {busy ? "保存中…" : "开始使用"}
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void finish(null, true)}
          className="rounded-lg px-3 py-2 text-sm text-zinc-400 ring-1 ring-zinc-700/50 hover:bg-zinc-800/50"
        >
          跳过
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            markOnboardingCompleted();
            navigate("/market-coverage", { replace: true });
          }}
          className="text-xs text-zinc-500 hover:text-zinc-300"
        >
          先看数据说明
        </button>
      </div>
    </div>
  );
}
