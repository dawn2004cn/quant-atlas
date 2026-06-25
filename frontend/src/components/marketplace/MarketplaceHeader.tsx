import type { MpTab } from "../../pages/Marketplace";

interface MarketplaceHeaderProps {
  score: number;
  orderCount: number;
  listingCount: number;
  activeTab: MpTab;
  onTabChange: (tab: MpTab) => void;
}

export function MarketplaceHeader({
  score,
  orderCount,
  listingCount,
  activeTab,
  onTabChange,
}: MarketplaceHeaderProps) {
  return (
    <>
      <div>
        <h1 className="text-2xl font-bold">Alpha Marketplace</h1>
        <p className="text-sm text-slate-500">因子贡献社区 — 声誉积分协作</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="glass-card p-4">
          <div className="text-2xl font-bold text-violet-600">{Number(score).toFixed(1)}</div>
          <div className="text-xs text-slate-500">我的声誉积分</div>
        </div>
        <div className="glass-card p-4">
          <div className="text-2xl font-bold">{orderCount}</div>
          <div className="text-xs text-slate-500">我的订单</div>
        </div>
        <div className="glass-card p-4">
          <div className="text-2xl font-bold">{listingCount}</div>
          <div className="text-xs text-slate-500">在售列表</div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {(
          [
            ["browse", "浏览市场"],
            ["orders", "我的订单"],
            ["list", "上架因子"],
            ["wallet", "声誉"],
            ["runs", "回测实验"],
            ["governance", "因子治理"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`btn btn-sm ${activeTab === id ? "btn-primary" : "btn-ghost"}`}
            onClick={() => onTabChange(id as MpTab)}
          >
            {label}
          </button>
        ))}
      </div>
    </>
  );
}