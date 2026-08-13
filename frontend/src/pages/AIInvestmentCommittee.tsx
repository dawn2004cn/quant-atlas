import { useState } from "react";
import useSWR from "swr";
import { CoreWorkflowStrip, PageQuickNav, QUICK_NAV_PRESETS } from "../components/CoreWorkflowStrip";
import { DemoBanner } from "../components/DemoBanner";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";
import { DEMO_INVESTMENT_COMMITTEE } from "../lib/demoCatalog";

type DebateTurn = {
  speaker: string;
  role: string;
  argument: string;
  sentiment: "bullish" | "bearish" | "neutral";
};

type Proposal = {
  id: string;
  title: string;
  description: string;
  proposed_by: string;
  status: "open" | "pass" | "reject";
  votes_for: number;
  votes_against: number;
  total_votes: number;
  deadline: string;
};

type InvestmentCommittee = {
  debates: Array<{
    topic: string;
    moderator: string;
    turns: DebateTurn[];
    started_at: string;
  }>;
  proposals: Proposal[];
  active_members: number;
  updated_at: string;
};

export function AIInvestmentCommitteePage() {
  const [activeTab, setActiveTab] = useState<"debates" | "proposals">("debates");

  const { data, error, isLoading, mutate } = useSWR(
    "ai-investment-committee",
    () => apiFetchV1<InvestmentCommittee>("/ai/investment-committee"),
    { refreshInterval: 30_000 },
  );

  const castVote = async (proposalId: string, approve: boolean) => {
    try {
      await apiFetchV1("/ai/investment-committee/vote", {
        method: "POST",
        body: JSON.stringify({ proposal_id: proposalId, approve }),
      });
      mutate();
    } catch {
      /* vote failed — will show on next refresh */
    }
  };

  if (isLoading && !data && !error) return <PageSkeleton rows={4} />;

  const isDemo = Boolean(error) || !data || (!(data.debates ?? []).length && !(data.proposals ?? []).length);
  const view = isDemo ? DEMO_INVESTMENT_COMMITTEE : data!;

  return (
    <div className="space-y-5">
      <CoreWorkflowStrip />
      <PageQuickNav items={QUICK_NAV_PRESETS.aiInvestmentCommittee} />
      <div>
        <h1 className="text-2xl font-bold">AI 投资委员会</h1>
        <p className="text-sm text-slate-500">
          多智能体辩论与投资决策 · {view.active_members} 名活跃成员
        </p>
        <DemoBanner show={isDemo} />
        {view.updated_at && (
          <p className="mt-1 text-xs text-slate-400">
            更新于：{new Date(view.updated_at).toLocaleString("zh-CN")}
          </p>
        )}
      </div>

      {/* Tabs */}
      <div className="tabs tabs-box">
        <button
          type="button"
          className={`tab ${activeTab === "debates" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("debates")}
        >
          辩论 ({view.debates.length})
        </button>
        <button
          type="button"
          className={`tab ${activeTab === "proposals" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("proposals")}
        >
          提案 ({view.proposals.length})
        </button>
      </div>

      {/* Debates */}
      {activeTab === "debates" && (
        <>
          {view.debates.length === 0 ? (
            <div className="glass-card p-6 text-center text-sm text-slate-400">
              暂无活跃辩论
            </div>
          ) : (
            view.debates.map((debate, idx) => (
              <div key={idx} className="glass-card space-y-3 p-4">
                <div className="flex items-center justify-between">
                  <h2 className="font-bold">{debate.topic}</h2>
                  <span className="text-xs text-slate-400">
                    主持人：{debate.moderator}
                  </span>
                </div>

                <div className="space-y-2">
                  {debate.turns.map((turn, turnIdx) => (
                    <div
                      key={turnIdx}
                      className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800"
                    >
                      <div className="mb-1 flex items-center gap-2">
                        <span className="text-sm font-bold">{turn.speaker}</span>
                        <span className="text-xs text-slate-500">{turn.role}</span>
                        <span
                          className={`badge badge-xs ${
                            turn.sentiment === "bullish"
                              ? "badge-success"
                              : turn.sentiment === "bearish"
                                ? "badge-error"
                                : "badge-ghost"
                          }`}
                        >
                          {turn.sentiment === "bullish"
                            ? "看多"
                            : turn.sentiment === "bearish"
                              ? "看空"
                              : "中性"}
                        </span>
                      </div>
                      <p className="text-sm">{turn.argument}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </>
      )}

      {/* Proposals */}
      {activeTab === "proposals" && (
        <>
          {view.proposals.length === 0 ? (
            <div className="glass-card p-6 text-center text-sm text-slate-400">
              暂无提案
            </div>
          ) : (
            view.proposals.map((proposal) => {
              const passPct =
                proposal.total_votes > 0
                  ? (proposal.votes_for / proposal.total_votes) * 100
                  : 0;
              return (
                <div key={proposal.id} className="glass-card space-y-3 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <h2 className="font-bold">{proposal.title}</h2>
                      <p className="text-xs text-slate-500">
                        发起人：{proposal.proposed_by} · 截止：
                        {new Date(proposal.deadline).toLocaleString("zh-CN")}
                      </p>
                    </div>
                    <span
                      className={`badge ${
                        proposal.status === "pass"
                          ? "badge-success"
                          : proposal.status === "reject"
                            ? "badge-error"
                            : "badge-info"
                      }`}
                    >
                      {proposal.status === "pass"
                        ? "通过"
                        : proposal.status === "reject"
                          ? "驳回"
                          : "投票中"}
                    </span>
                  </div>

                  <p className="text-sm">{proposal.description}</p>

                  {/* Vote progress */}
                  <div>
                    <div className="mb-1 flex justify-between text-xs text-slate-500">
                      <span>
                        赞成 {proposal.votes_for}/{proposal.total_votes}
                      </span>
                      <span>{passPct.toFixed(0)}%</span>
                    </div>
                    <progress
                      className="progress progress-success w-full"
                      value={proposal.votes_for}
                      max={proposal.total_votes || 1}
                    />
                  </div>

                  {/* Vote buttons */}
                  {proposal.status === "open" && (
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="btn btn-success btn-sm"
                        onClick={() => castVote(proposal.id, true)}
                      >
                        赞成
                      </button>
                      <button
                        type="button"
                        className="btn btn-error btn-sm"
                        onClick={() => castVote(proposal.id, false)}
                      >
                        反对
                      </button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </>
      )}
    </div>
  );
}
