import type { MarketplaceOrder } from "../../types/backtest";

interface MarketplaceOrdersTabProps {
  orders: MarketplaceOrder[];
  busy: boolean;
  onCancel: (orderId?: string) => Promise<void>;
}

export function MarketplaceOrdersTab({
  orders,
  busy,
  onCancel,
}: MarketplaceOrdersTabProps) {
  return (
    <div className="glass-card overflow-x-auto p-4">
      <table className="table table-sm">
        <thead>
          <tr>
            <th>订单</th>
            <th>Listing</th>
            <th>花费</th>
            <th>状态</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {orders.length === 0 ? (
            <tr>
              <td colSpan={5} className="text-center text-slate-500">
                暂无订单
              </td>
            </tr>
          ) : (
            orders.map((item: MarketplaceOrder) => (
              <tr key={item.order_id}>
                <td className="font-mono text-xs">{item.order_id?.slice(0, 10)}</td>
                <td className="font-mono text-xs">{item.listing_id?.slice(0, 8)}</td>
                <td>{(item.reputation_spent ?? item.tokens_spent ?? 0).toFixed(1)}</td>
                <td>
                  <span className="badge badge-outline">{item.status ?? "active"}</span>
                </td>
                <td>
                  {item.status === "active" ? (
                    <button
                      type="button"
                      className="btn btn-error btn-xs"
                      disabled={busy}
                      onClick={() => void onCancel(item.order_id)}
                    >
                      取消
                    </button>
                  ) : null}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}