import type { MarketplaceListing } from "../../types/backtest";

interface MarketplaceBrowseTabProps {
  listings: MarketplaceListing[];
  busy: boolean;
  onContribute: (listingId?: string) => Promise<void>;
}

export function MarketplaceBrowseTab({
  listings,
  busy,
  onContribute,
}: MarketplaceBrowseTabProps) {
  return (
    <div className="glass-card overflow-x-auto p-4">
      <table className="table table-sm">
        <thead>
          <tr>
            <th>Token</th>
            <th>贡献者</th>
            <th>声誉成本</th>
            <th>信号数</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {listings.length === 0 ? (
            <tr>
              <td colSpan={5} className="text-center text-slate-500">
                暂无在售因子
              </td>
            </tr>
          ) : (
            listings.map((item: MarketplaceListing) => (
              <tr key={item.listing_id ?? item.token_id}>
                <td className="font-mono text-xs">{item.token_id}</td>
                <td>{item.seller_id}</td>
                <td>{(item.reputation_cost ?? item.price_tokens ?? 0).toFixed(1)}</td>
                <td>{item.signal_count ?? "-"}</td>
                <td>
                  <button
                    type="button"
                    className="btn btn-primary btn-xs"
                    disabled={busy}
                    onClick={() => void onContribute(item.listing_id)}
                  >
                    贡献
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}