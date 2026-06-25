import { FormEvent } from "react";

interface MarketplaceListTabProps {
  listTokenId: string;
  listPrice: number;
  listSignals: number;
  creditAmount: number;
  setListTokenId: (v: string) => void;
  setListPrice: (v: number) => void;
  setListSignals: (v: number) => void;
  setCreditAmount: (v: number) => void;
  onListSubmit: (event: FormEvent) => Promise<void>;
  onCreditSubmit: (event: FormEvent) => Promise<void>;
  busy: boolean;
  score: number;
  contributionCount?: number;
}

export function MarketplaceListTab({
  listTokenId,
  listPrice,
  listSignals,
  creditAmount,
  setListTokenId,
  setListPrice,
  setListSignals,
  setCreditAmount,
  onListSubmit,
  onCreditSubmit,
  busy,
  score,
  contributionCount,
}: MarketplaceListTabProps) {
  return (
    <>
      <form className="glass-card max-w-lg space-y-4 p-6" onSubmit={onListSubmit}>
        <label className="form-control">
          <span className="label-text">Token ID</span>
          <input
            className="input input-bordered"
            value={listTokenId}
            onChange={(e) => setListTokenId(e.target.value)}
            required
          />
        </label>
        <label className="form-control">
          <span className="label-text">声誉成本</span>
          <input
            type="number"
            min={1}
            className="input input-bordered"
            value={listPrice}
            onChange={(e) => setListPrice(Number(e.target.value))}
            required
          />
        </label>
        <label className="form-control">
          <span className="label-text">信号数量</span>
          <input
            type="number"
            min={1}
            className="input input-bordered"
            value={listSignals}
            onChange={(e) => setListSignals(Number(e.target.value))}
          />
        </label>
        <button type="submit" className="btn btn-primary" disabled={busy}>
          上架
        </button>
      </form>

      <form className="glass-card max-w-lg space-y-4 p-6" onSubmit={onCreditSubmit}>
        <p className="text-sm text-slate-500">
          当前声誉：<strong>{Number(score).toFixed(1)}</strong>
          {contributionCount != null ? (
            <span className="ml-2">（贡献 {contributionCount} 次）</span>
          ) : null}
        </p>
        <label className="form-control">
          <span className="label-text">测试充值积分</span>
          <input
            type="number"
            min={1}
            className="input input-bordered"
            value={creditAmount}
            onChange={(e) => setCreditAmount(Number(e.target.value))}
          />
        </label>
        <button type="submit" className="btn btn-primary" disabled={busy}>
          充值声誉
        </button>
      </form>
    </>
  );
}