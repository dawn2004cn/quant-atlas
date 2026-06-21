"""Phase D — compliance, access policy, decision review productization."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.domain.compliance.retail_manifest import build_compliance_manifest
from app.modules.system.services.ui.decision_review_queue import (
    DecisionReviewQueue,
    ReviewPriority,
)


def test_compliance_manifest_has_disclaimer_and_sla():
    manifest = build_compliance_manifest()
    assert manifest["disclaimers"]["short"]
    assert manifest["sla"]["decision_review_sla_hours"] == 24


def test_user_access_policy_free_tier():
    from app.modules.user.services.user.user_access_policy_service import UserAccessPolicyService

    svc = UserAccessPolicyService()
    snap = svc.snapshot_for_user(SimpleNamespace(role="free"))
    assert snap["tier"] == "free"
    assert snap["tier_label"] == "免费版"
    disabled = [f for f in snap["features"] if not f["enabled"]]
    assert disabled
    assert snap["limits"]["ai_diagnosis_daily"] == 5


def test_user_access_policy_pro_tier():
    from app.modules.user.services.user.user_access_policy_service import UserAccessPolicyService

    svc = UserAccessPolicyService()
    snap = svc.snapshot_for_user(SimpleNamespace(role="pro"))
    assert snap["tier"] == "pro"
    assert snap["limits"]["watchlist_groups"] == 10


def test_decision_review_product_summary(tmp_path: Path):
    store = tmp_path / "queue.json"
    q = DecisionReviewQueue(store_path=store)
    q.enqueue(
        "d1",
        "CN:600519",
        0.3,
        "test",
        priority=ReviewPriority.HIGH.value,
        review_sla_hours=1,
    )
    summary = q.product_summary()
    assert summary["pending_count"] == 1
    assert summary["high_priority_count"] == 1
    assert summary["sla_hours"] == 24


def test_system_sla_route():
    import werkzeug
    from flask import Blueprint, Flask

    if not hasattr(werkzeug, "__version__"):
        werkzeug.__version__ = "3.0.0"  # type: ignore[attr-defined]

    from app.presentation.api.routes_v1_system_health import register_system_health_routes
    from app.presentation.api.v1_context import ApiV1Context

    app = Flask(__name__)
    bp = Blueprint("health_test", __name__)
    register_system_health_routes(bp, ApiV1Context(enable_legacy_response_fields=False))
    app.register_blueprint(bp, url_prefix="/api/v1")

    res = app.test_client().get("/api/v1/system/sla")
    assert res.status_code == 200
    body = res.get_json()
    assert body["data"]["tier"] == "beta"


def test_compliance_manifest_route():
    import werkzeug
    from flask import Blueprint, Flask

    if not hasattr(werkzeug, "__version__"):
        werkzeug.__version__ = "3.0.0"  # type: ignore[attr-defined]

    from app.presentation.api.routes_v1_compliance import register_compliance_routes
    from app.presentation.api.v1_context import ApiV1Context

    app = Flask(__name__)
    bp = Blueprint("compliance_test", __name__)
    register_compliance_routes(bp, ApiV1Context(enable_legacy_response_fields=False))
    app.register_blueprint(bp, url_prefix="/api/v1")

    res = app.test_client().get("/api/v1/compliance/manifest")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "disclaimers" in data
