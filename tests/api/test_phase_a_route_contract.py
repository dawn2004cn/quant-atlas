"""Phase A: canonical API paths used by high-traffic pages must exist."""

from __future__ import annotations

import pytest

from app.presentation.api.route_contract import (
    CRITICAL_ROUTE_MODULES,
    missing_canonical_paths,
)


PHASE_A_PATHS = tuple(
    path for spec in CRITICAL_ROUTE_MODULES for path in spec.paths
) + (
    "/api/v1/phase18/zen/search",
    "/api/v1/phase18/zen/toggle",
    "/api/v1/phase18/resonance/field",
)


@pytest.mark.parametrize("path", PHASE_A_PATHS)
def test_phase_a_canonical_path_registered(client, path: str):
    """Each path must resolve (not 404) for anonymous GET where applicable."""
    app = client.application
    assert path not in missing_canonical_paths(app.url_map), f"missing from url_map: {path}"
