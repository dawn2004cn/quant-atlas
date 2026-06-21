"""Phase H — React/Vite SPA scaffold."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def test_frontend_scaffold_files_exist():
    required = [
        FRONTEND / "package.json",
        FRONTEND / "vite.config.ts",
        FRONTEND / "src" / "App.tsx",
        FRONTEND / "src" / "pages" / "Login.tsx",
        FRONTEND / "src" / "pages" / "Dashboard.tsx",
        FRONTEND / "src" / "pages" / "StockDetail.tsx",
        FRONTEND / "src" / "lib" / "api.ts",
        FRONTEND / "src" / "hooks" / "useRealtime.ts",
        FRONTEND / "src" / "hooks" / "useAnalysisStream.ts",
        FRONTEND / "src" / "components" / "stock" / "AiInsightPanel.tsx",
        FRONTEND / "src" / "types" / "backtest.ts",
        FRONTEND / "src" / "types" / "workbench.ts",
        FRONTEND / "src" / "pages" / "Marketplace.tsx",
        FRONTEND / "src" / "types" / "stock.ts",
        FRONTEND / "src" / "components" / "stock" / "StockQuoteCard.tsx",
        FRONTEND / "src" / "components" / "charts" / "EquityCurveChart.tsx",
        FRONTEND / "src" / "components" / "governance" / "GovernanceProposalModal.tsx",
        FRONTEND / "src" / "components" / "governance" / "GovernanceVoteFlow.tsx",
        FRONTEND / "src" / "components" / "governance" / "GovernanceTimeline.tsx",
        FRONTEND / "src" / "components" / "mlflow" / "MlflowRunModal.tsx",
        FRONTEND / "src" / "components" / "mlflow" / "MlflowConfigBar.tsx",
        FRONTEND / "src" / "components" / "ProtectedRoute.tsx",
        FRONTEND / "src" / "components" / "PageSkeleton.tsx",
        FRONTEND / "src" / "pages" / "NotFound.tsx",
        FRONTEND / "src" / "components" / "workbench" / "RealtimeBar.tsx",
    ]
    for path in required:
        assert path.is_file(), f"missing {path.relative_to(ROOT)}"


def test_spa_route_registered():
    import werkzeug

    if not hasattr(werkzeug, "__version__"):
        werkzeug.__version__ = "3.0.0"  # type: ignore[attr-defined]

    from flask import Flask

    from app.presentation.web.pages import create_pages_blueprint

    app = Flask(__name__)
    app.register_blueprint(create_pages_blueprint())
    paths = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/app" in paths
    assert "/app/<path:asset_path>" in paths
