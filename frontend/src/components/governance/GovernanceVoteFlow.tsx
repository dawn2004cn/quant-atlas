import type { AlphaGovernanceProposal } from "../../lib/api";

const MAJORITY_DEFAULT = 0.6;

type Props = {
  proposal: AlphaGovernanceProposal;
  majorityThreshold?: number;
};

const STEPS = [
  { id: "candidate", label: "候选" },
  { id: "trial", label: "试用" },
  { id: "active", label: "激活" },
] as const;

function resolveStep(status: string): (typeof STEPS)[number]["id"] {
  if (status === "active") return "active";
  if (status === "trial") return "trial";
  return "candidate";
}

export function GovernanceVoteFlow({ proposal, majorityThreshold = MAJORITY_DEFAULT }: Props) {
  const votesFor = proposal.votes_for ?? 0;
  const votesAgainst = proposal.votes_against ?? 0;
  const total = votesFor + votesAgainst;
  const approvalRate = total > 0 ? votesFor / total : 0;
  const tallyStatus = String(proposal.tally?.status ?? "");
  const currentStep = resolveStep(proposal.status);

  let verdict: "pending" | "approved" | "rejected" = "pending";
  if (tallyStatus === "approved" || proposal.status === "active") {
    verdict = "approved";
  } else if (tallyStatus === "rejected") {
    verdict = "rejected";
  }

  return (
    <div className="space-y-3 rounded-lg border border-slate-200/80 p-3 dark:border-slate-700">
      <div className="text-xs font-semibold text-slate-500">治理流程</div>

      <ul className="steps steps-horizontal w-full text-xs">
        {STEPS.map((step) => (
          <li
            key={step.id}
            className={`step ${currentStep === step.id ? "step-primary" : ""}`}
          >
            {step.label}
          </li>
        ))}
      </ul>

      <div>
        <div className="mb-1 flex justify-between text-xs text-slate-500">
          <span>
            赞成 {votesFor} / 反对 {votesAgainst}
          </span>
          <span>
            通过率 {(approvalRate * 100).toFixed(0)}%（阈值 {(majorityThreshold * 100).toFixed(0)}%）
          </span>
        </div>
        <progress
          className="progress progress-primary w-full"
          value={Math.min(approvalRate * 100, 100)}
          max={100}
        />
      </div>

      <div className="flex items-center gap-2 text-xs">
        <span className="text-slate-500">决议：</span>
        {verdict === "pending" ? (
          <span className="badge badge-outline">待投票</span>
        ) : null}
        {verdict === "approved" ? (
          <span className="badge badge-success">已通过</span>
        ) : null}
        {verdict === "rejected" ? (
          <span className="badge badge-error">未通过</span>
        ) : null}
      </div>
    </div>
  );
}
