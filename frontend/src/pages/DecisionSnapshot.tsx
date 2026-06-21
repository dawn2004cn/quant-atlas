import { useParams } from "react-router-dom";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

type DecisionSnapshotData = {
  snapshot_id: string;
  created_at: string;
  symbol: string;
  market: string;
  decision_type: string;
  score: number;
  stance: string;
  evidence: Array<{ source: string; content: string; confidence: number }>;
  alternative_views?: Array<{ title: string; content: string }>;
  decision_tree?: { nodes: Array<{ id: string; label: string; choice: string }> };
  signals: Array<{ name: string; value: number; impact: string }>;
};

export function DecisionSnapshotPage() {
  const { snapshotId } = useParams<{ snapshotId: string }>();

  const { data, error, isLoading } = useSWR(
    snapshotId ? ["decision-snapshot", snapshotId] : null,
    () => apiFetchV1<{ data: DecisionSnapshotData }>(`/decision/snapshot/${encodeURIComponent(snapshotId ?? "")}`),
  );

  const snap = data?.data;
  if (isLoading) return <PageSkeleton rows={4} />;

  if (error) return <div className="alert alert-error">加载失败：{error.message}</div>;
  if (!snap) return <div className="alert alert-warning">快照不存在</div>;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">决策快照</h1>
          <p className="text-sm text-slate-500">
            {snap.symbol} · {snap.market} · {new Date(snap.created_at).toLocaleString("zh-CN")}
          </p>
        </div>
        <div className="text-center">
          <div className="text-4xl font-black text-brand">{snap.score ?? "--"}</div>
          <div className="text-xs text-slate-500">{snap.stance}</div>
        </div>
      </div>

      {/* Decision Type */}
      <div className="glass-card p-4">
        <span className="text-xs font-semibold text-slate-500">决策类型</span>
        <div className="text-lg font-bold">{snap.decision_type}</div>
      </div>

      {/* Evidence chain */}
      {snap.evidence?.length > 0 && (
        <section className="glass-card space-y-3 p-4">
          <h2 className="text-sm font-bold">证据链</h2>
          {snap.evidence.map((e, i) => (
            <div key={i} className="rounded-xl border p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase text-slate-500">{e.source}</span>
                <span className="text-xs">置信度: {(e.confidence * 100).toFixed(0)}%</span>
              </div>
              <p className="mt-1 text-sm">{e.content}</p>
            </div>
          ))}
        </section>
      )}

      {/* Alternative views */}
      {snap.alternative_views && snap.alternative_views.length > 0 && (
        <section className="glass-card space-y-3 p-4">
          <h2 className="text-sm font-bold">反向观点</h2>
          {snap.alternative_views.map((v, i) => (
            <div key={i} className="rounded-xl border-l-4 border-amber-400 bg-amber-50 p-3 dark:bg-amber-950/30">
              <div className="text-sm font-semibold">{v.title}</div>
              <p className="mt-1 text-xs text-slate-600">{v.content}</p>
            </div>
          ))}
        </section>
      )}

      {/* Signals */}
      {snap.signals?.length > 0 && (
        <section className="glass-card overflow-x-auto p-4">
          <h2 className="mb-3 text-sm font-bold">信号汇总</h2>
          <table className="table w-full">
            <thead><tr><th>信号</th><th>值</th><th>影响</th></tr></thead>
            <tbody>
              {snap.signals.map((s) => (
                <tr key={s.name}>
                  <td>{s.name}</td>
                  <td>{s.value}</td>
                  <td className={s.impact === "positive" ? "text-emerald-600" : s.impact === "negative" ? "text-rose-600" : ""}>{s.impact}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

export function DecisionSnapshotPublicPage() {
  const { shareToken } = useParams<{ shareToken: string }>();

  const { data, error, isLoading } = useSWR(
    shareToken ? ["decision-share", shareToken] : null,
    () => apiFetchV1<{ data: DecisionSnapshotData }>(`/snapshots/public/${encodeURIComponent(shareToken ?? "")}`),
  );

  const snap = data?.data;
  if (isLoading) return <PageSkeleton rows={3} />;
  if (error) return <div className="alert alert-error">加载失败</div>;
  if (!snap) return <div className="alert alert-warning">该分享链接不存在或已过期</div>;

  return (
    <div className="space-y-5">
      <div className="rounded-xl bg-brand/10 p-4 text-center">
        <p className="text-sm text-slate-500">公开分享 · 只读模式</p>
      </div>
      <DecisionSnapshotPage />
    </div>
  );
}