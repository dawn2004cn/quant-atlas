import type { GovernanceTimelineEvent } from "../../lib/api";

const TYPE_LABELS: Record<string, string> = {
  submitted: "提交",
  vote_approve: "赞成",
  vote_reject: "反对",
  approved: "通过",
  pending: "计票",
  activated: "激活",
};

const TYPE_BADGE: Record<string, string> = {
  submitted: "badge-info",
  vote_approve: "badge-success",
  vote_reject: "badge-error",
  approved: "badge-success",
  pending: "badge-warning",
  activated: "badge-primary",
};

function formatAt(value: string | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

type Props = {
  events: GovernanceTimelineEvent[];
};

export function GovernanceTimeline({ events }: Props) {
  if (!events.length) {
    return <p className="text-xs text-slate-500">暂无审批时间线</p>;
  }

  return (
    <ul className="timeline timeline-vertical timeline-compact ms-2 max-h-72 overflow-y-auto">
      {events.map((event, index) => (
        <li key={`${event.type}-${event.at}-${index}`}>
          {index > 0 ? <hr /> : null}
          <div className="timeline-start text-xs text-slate-500">{formatAt(event.at)}</div>
          <div className="timeline-middle">
            <span className={`badge badge-xs ${TYPE_BADGE[event.type] ?? "badge-ghost"}`}>
              {TYPE_LABELS[event.type] ?? event.type}
            </span>
          </div>
          <div className="timeline-end timeline-box mb-2 text-xs">
            <div>{event.summary}</div>
            {event.actor ? <div className="mt-1 text-slate-500">{event.actor}</div> : null}
          </div>
          <hr />
        </li>
      ))}
    </ul>
  );
}
