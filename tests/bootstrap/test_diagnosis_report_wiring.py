from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import warnings

try:
    from app.bootstrap_components.wiring_trading import wire_diagnosis_report_service
except ImportError:
    wire_diagnosis_report_service = None


def test_wire_diagnosis_report_service_deprecated() -> None:
    if wire_diagnosis_report_service is None:
        pytest.skip("wire_diagnosis_report_service removed from wiring_trading")
    class Services:
        diagnosis_report_service: MagicMock | None = None
        ai_analysis_service = MagicMock()
        trade_plan_service = MagicMock()
        ai_evidence_service = MagicMock()
        industry_chain_service = MagicMock()

    services = Services()

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        wire_diagnosis_report_service(services)
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message).lower()
        # The wire function is now a no-op; service stays None.
        assert services.diagnosis_report_service is None
