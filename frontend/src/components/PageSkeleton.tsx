export function PageSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-4 animate-pulse" aria-busy="true" aria-label="加载中">
      {Array.from({ length: rows }, (_, index) => (
        <div
          key={index}
          className="glass-card h-20 bg-slate-200/50 dark:bg-slate-800/50"
        />
      ))}
    </div>
  );
}
