export function DemoBanner({
  show,
  text = "演示数据 · 行情源未就绪或列表为空",
}: {
  show: boolean;
  text?: string;
}) {
  if (!show) return null;
  return (
    <p className="text-[11px] font-mono text-amber-400/90" role="status">
      {text}
    </p>
  );
}
