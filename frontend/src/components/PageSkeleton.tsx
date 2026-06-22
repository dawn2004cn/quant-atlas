export function PageSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-4 animate-pulse" aria-busy="true" aria-label="加载中">
      {Array.from({ length: rows }, (_, index) => (
        <div
          key={index}
          className="h-20 rounded-xl bg-zinc-900/50 ring-1 ring-zinc-800/50"
        />
      ))}
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