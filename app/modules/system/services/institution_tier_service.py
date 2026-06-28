"""Tier 5: Large Institution — Facade delegating to specialized services.

This module provides a unified interface for institutional-grade features:
- Market impact modeling
- Advanced execution algorithms
- Federated deployment
- RBAC (Role-Based Access Control)
"""

from __future__ import annotations

from app.modules.system.services.market_impact_service import (
    ImpactForecast,
    MarketImpactModelService,
)
from app.modules.system.services.execution_algo_service import (
    ExecutionSchedule,
    POVSchedule,
    AdvancedExecutionAlgoService,
)
from app.modules.system.services.federated_deployment_service import (
    FederatedModelUpdate,
    DeploymentNode,
    FederatedClusterStatus,
    FedAvgRoundResult,
    FederatedDeploymentService,
)
from app.modules.system.services.rbac_service import (
    Permission,
    ResourceType,
    RBACService,
)

__all__ = [
    # Market Impact
    "ImpactForecast",
    "MarketImpactModelService",
    # Execution Algos
    "ExecutionSchedule",
    "POVSchedule",
    "AdvancedExecutionAlgoService",
    # Federated Deployment
    "FederatedModelUpdate",
    "DeploymentNode",
    "FederatedClusterStatus",
    "FedAvgRoundResult",
    "FederatedDeploymentService",
    # RBAC
    "Permission",
    "ResourceType",
    "RBACService",
]
