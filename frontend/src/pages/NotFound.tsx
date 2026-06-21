import { Link } from "react-router-dom";
import { usePlatformFeatures } from "../hooks/usePlatformFeatures";

export function NotFoundPage() {
  const { features } = usePlatformFeatures();

  return (
    <div className="glass-card mx-auto max-w-lg p-8 text-center">
      <h1 className="text-2xl font-bold">页面不存在</h1>
      <p className="mt-2 text-sm text-slate-500">
        请检查地址，或从操盘台重新导航。
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <Link to="/" className="btn btn-primary btn-sm">
          返回操盘台
        </Link>
        {features.feature_alpha_marketplace ? (
          <Link to="/marketplace" className="btn btn-outline btn-sm">
            因子市场
          </Link>
        ) : null}
      </div>
    </div>
  );
}
