/** Shared daisy progress strip for async / loading states (SPA 风格对齐). */
export function AsyncProgressBar({
  label,
  value,
  indeterminate = false,
  className = "",
}: {
  label?: string;
  value?: number;
  indeterminate?: boolean;
  className?: string;
}) {
  const showValue = !indeterminate && typeof value === "number" && Number.isFinite(value);
  return (
    <div className={`space-y-1 ${className}`.trim()} aria-busy="true">
      {(label || showValue) && (
        <div className="flex items-center justify-between text-xs text-zinc-500">
          <span>{label ?? "进度"}</span>
          {showValue ? <span>{Math.round(value)}%</span> : null}
        </div>
      )}
      <progress
        className="progress progress-primary w-full h-2"
        value={indeterminate ? undefined : value}
        max={100}
      />
    </div>
  );
}

export function PageSkeleton({
  rows = 3,
  showProgress = false,
}: {
  rows?: number;
  showProgress?: boolean;
}) {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="加载中">
      {showProgress ? <AsyncProgressBar label="加载中…" indeterminate /> : null}
      <div className="space-y-4 animate-pulse">
        {Array.from({ length: rows }, (_, index) => (
          <div
            key={index}
            className="h-20 rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50"
          />
        ))}
      </div>
    </div>
  );
}

export function TableSkeleton({ rows: rowCount = 5 }: { rows?: number }) {
  return (
    <div className="animate-pulse space-y-1" aria-busy="true">
      <div className="flex gap-4 px-4 py-3">
        <div className="h-4 w-20 rounded bg-zinc-800/40" />
        <div className="h-4 w-32 rounded bg-zinc-800/40" />
        <div className="ml-auto h-4 w-16 rounded bg-zinc-800/40" />
      </div>
      {Array.from({ length: rowCount }, (_, i) => (
        <div key={i} className="flex gap-4 px-4 py-2.5">
          <div className="h-3 w-16 rounded bg-zinc-800/30" />
          <div className="h-3 w-24 rounded bg-zinc-800/30" />
          <div className="ml-auto h-3 w-12 rounded bg-zinc-800/30" />
        </div>
      ))}
    </div>
  );
}