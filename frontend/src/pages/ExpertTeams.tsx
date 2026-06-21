import { useState } from "react";
import useSWR from "swr";
import { PageSkeleton } from "../components/PageSkeleton";
import { apiFetchV1 } from "../lib/api";

/* ── Types ── */
type ExpertTeam = {
  team_id: string;
  name: string;
  description?: string;
  member_count: number;
  specialty?: string[];
  leader_name?: string;
  avatar_url?: string;
  total_return_pct?: number;
  active_projects?: number;
  tags?: string[];
};

type TeamsResponse = {
  items: ExpertTeam[];
  total: number;
};

/* ── Format helpers ── */
function fmtPct(v?: number | null): string {
  if (v == null || Number.isNaN(v)) return "--";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

/* ── Component ── */
export function ExpertTeamsPage() {
  const [searchQuery, setSearchQuery] = useState("");

  const { data, error, isLoading } = useSWR(
    "expert-teams",
    () => apiFetchV1<TeamsResponse>("/expert-teams"),
    { refreshInterval: 120_000 },
  );

  const teams = data?.items ?? [];

  const filtered = searchQuery
    ? teams.filter(
        (t: ExpertTeam) =>
          t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (t.specialty ?? []).some((s) =>
            s.toLowerCase().includes(searchQuery.toLowerCase()),
          ),
      )
    : teams;

  if (isLoading && !teams.length) return <PageSkeleton rows={4} />;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">专家团队</h1>
          <p className="text-sm text-slate-500">
            各领域专家团队协作，覆盖多标的覆盖与策略研究
          </p>
        </div>
        <input
          type="search"
          className="input input-bordered input-sm w-48"
          placeholder="搜索团队 / 专长"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {/* Error */}
      {error && <div className="alert alert-error">加载失败：{error.message}</div>}

      {/* Card Grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map((t: ExpertTeam) => (
          <div
            key={t.team_id}
            className="glass-card rounded-2xl p-5 space-y-4 hover:shadow-md transition-shadow"
          >
            {/* Header */}
            <div className="flex items-center gap-3">
              <div className="avatar placeholder">
                <div className="w-12 rounded-full bg-brand/10 text-brand">
                  <span className="text-lg font-bold">
                    {t.name?.charAt(0) ?? "?"}
                  </span>
                </div>
              </div>
              <div className="flex-1">
                <div className="font-bold">{t.name}</div>
                {t.leader_name && (
                  <div className="text-xs text-slate-500">
                    组长：{t.leader_name}
                  </div>
                )}
              </div>
              <div className="badge badge-ghost">{t.member_count} 人</div>
            </div>

            {/* Description */}
            {t.description && (
              <p className="text-xs text-slate-600 line-clamp-2">
                {t.description}
              </p>
            )}

            {/* Stats */}
            <div className="grid grid-cols-2 gap-3 text-center">
              <div className="rounded-lg bg-slate-100 p-2 dark:bg-slate-800">
                <div className="text-xs text-slate-500">总收益</div>
                <div
                  className={`text-sm font-bold ${
                    (t.total_return_pct ?? 0) >= 0
                      ? "text-emerald-600"
                      : "text-rose-600"
                  }`}
                >
                  {fmtPct(t.total_return_pct)}
                </div>
              </div>
              <div className="rounded-lg bg-slate-100 p-2 dark:bg-slate-800">
                <div className="text-xs text-slate-500">活跃项目</div>
                <div className="text-sm font-bold">
                  {t.active_projects ?? 0}
                </div>
              </div>
            </div>

            {/* Specialty Tags */}
            {t.specialty && t.specialty.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {t.specialty.map((s) => (
                  <span key={s} className="badge badge-ghost badge-sm">
                    {s}
                  </span>
                ))}
              </div>
            )}

            {/* Tags */}
            {t.tags && t.tags.length > 0 && (
              <div className="flex flex-wrap gap-1 border-t border-base-200 pt-2">
                {t.tags.map((tag) => (
                  <span
                    key={tag}
                    className="badge badge-outline badge-sm text-xs"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Empty */}
      {!filtered.length && (
        <div className="py-12 text-center text-slate-500">
          {searchQuery ? "未找到匹配的团队" : "暂无专家团队数据"}
        </div>
      )}
    </div>
  );
}