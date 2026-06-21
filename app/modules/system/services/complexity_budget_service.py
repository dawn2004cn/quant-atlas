"""Complexity Budget — Phase: Optimization.
Service audit, automated wiring validation, and graphify-based doc sync."""

from __future__ import annotations

import ast
import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ServiceAuditEntry:
    """One service entry in the audit."""
    service_name: str
    module_path: str
    lines_of_code: int
    dependency_count: int
    route_count: int = 0
    last_modified: str = ""
    duplicate_of: str = ""  # if this service duplicates another
    recommendation: str = ""  # keep / merge / archive


@dataclass
class ComplexityBudgetReport:
    """Full complexity budget report."""
    total_services: int = 0
    total_loc: int = 0
    duplicate_services: list[str] = field(default_factory=list)
    high_complexity_services: list[dict] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    budget_score: float = 1.0  # 0 = over budget, 1 = healthy
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ComplexityBudgetService:
    """Audits service complexity and enforces budget."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._modules_root = root / "app" / "modules"
        self._services_root = root / "app" / "application" / "services"
        self._report_path = root / "instance" / "complexity_budget.json"
        self._budget_limit = 200  # max LOC per service
        self._max_deps = 15  # max direct dependencies per service

    def run_audit(self) -> ComplexityBudgetReport:
        """Run full service audit."""
        report = ComplexityBudgetReport()
        entries = []

        # Scan all service files
        for root_dir in [self._modules_root, self._services_root]:
            if not root_dir.exists():
                continue
            for py_file in root_dir.rglob("*.py"):
                if py_file.name.startswith("__") or "pycache" in str(py_file):
                    continue
                entry = self._audit_file(py_file)
                if entry:
                    entries.append(entry)

        report.total_services = len(entries)
        report.total_loc = sum(e.lines_of_code for e in entries)

        # Detect duplicates by name similarity
        name_map = defaultdict(list)
        for e in entries:
            name_map[e.service_name].append(e)
        for name, group in name_map.items():
            if len(group) > 1:
                report.duplicate_services.append(name)
                for e in group:
                    e.duplicate_of = f"duplicate: {name} appears {len(group)} times"

        # High complexity services
        for e in entries:
            if e.lines_of_code > self._budget_limit:
                report.high_complexity_services.append({
                    "service": e.service_name,
                    "path": e.module_path,
                    "loc": e.lines_of_code,
                    "deps": e.dependency_count,
                })
                e.recommendation = "split into smaller services"

        # Generate recommendations
        if report.duplicate_services:
            report.recommendations.append(f"合并重复服务: {', '.join(report.duplicate_services)}")
        if report.high_complexity_services:
            for s in report.high_complexity_services:
                report.recommendations.append(f"拆分 {s['service']} ({s['loc']} LOC, {s['deps']} deps)")

        # Budget score
        over_budget = len(report.high_complexity_services)
        duplicates = len(report.duplicate_services)
        report.budget_score = max(0.0, 1.0 - (over_budget * 0.1 + duplicates * 0.15))

        self._save_report(report)
        logger.info("Complexity audit: %d services, %.1f budget score", report.total_services, report.budget_score)
        return report

    def _audit_file(self, py_file: Path) -> ServiceAuditEntry | None:
        """Audit a single Python service file."""
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, Exception):
            return None

        # Count lines of code (non-empty, non-comment)
        loc = sum(1 for line in source.splitlines() if line.strip() and not line.strip().startswith("#"))

        # Count imports (dependencies)
        deps = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)))

        # Extract service name from class definitions
        service_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                service_names.append(node.name)

        if not service_names:
            return None

        rel_path = py_file.relative_to(Path(__file__).resolve().parents[4])
        mod_time = datetime.fromtimestamp(py_file.stat().st_mtime, tz=timezone.utc).isoformat()

        return ServiceAuditEntry(
            service_name=", ".join(service_names),
            module_path=str(rel_path),
            lines_of_code=loc,
            dependency_count=deps,
            last_modified=mod_time,
        )

    def validate_wiring(self, registry: Any | None = None) -> dict[str, Any]:
        """Validate wiring modules and optionally resolve registered factories."""
        results: dict[str, Any] = {
            "ok": True,
            "errors": [],
            "checked": 0,
            "factory_count": 0,
            "factories_resolved": 0,
            "factories_failed": [],
        }
        wiring_dir = Path(__file__).resolve().parents[4] / "app" / "bootstrap_components"
        if not wiring_dir.exists():
            return results

        for wiring_file in sorted(wiring_dir.glob("wiring_*.py")):
            try:
                source = wiring_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and hasattr(node.func, "id") and node.func.id == "register_factory":
                        results["checked"] += 1
            except SyntaxError as exc:
                results["ok"] = False
                results["errors"].append(f"{wiring_file.name}: {exc}")

        try:
            from app.bootstrap_components.service_wiring import _get_registry

            service_registry = _get_registry()
            factory_names = sorted(name for name, entry in getattr(service_registry, "_entries", {}).items() if getattr(entry, "is_factory", False))
            results["factory_count"] = len(factory_names)
            if registry is not None:
                registry_names = registry.keys() if isinstance(registry, dict) else factory_names
                for name in sorted(registry_names):
                    try:
                        instance = service_registry.get_or_none(name)
                        if instance is None:
                            results["factories_failed"].append(name)
                        else:
                            results["factories_resolved"] += 1
                    except Exception as exc:
                        results["ok"] = False
                        results["factories_failed"].append(name)
                        results["errors"].append(f"factory {name}: {exc}")
        except Exception as exc:
            logger.debug("Factory resolution skipped: %s", exc)

        return results

    def generate_dependency_graph(self) -> dict[str, Any]:
        """Generate service dependency graph for documentation."""
        graph = {"nodes": [], "edges": []}
        seen = set()

        for root_dir in [self._modules_root, self._services_root]:
            if not root_dir.exists():
                continue
            for py_file in root_dir.rglob("*.py"):
                if py_file.name.startswith("__") or "pycache" in str(py_file):
                    continue
                try:
                    source = py_file.read_text(encoding="utf-8")
                    tree = ast.parse(source)
                except (SyntaxError, Exception):
                    continue

                rel = str(py_file.relative_to(Path(__file__).resolve().parents[4]))
                if rel not in seen:
                    seen.add(rel)
                    graph["nodes"].append({"id": rel, "group": py_file.parent.name})

                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        for alias in node.names:
                            dep = f"{node.module}.{alias.name}"
                            if dep not in seen:
                                seen.add(dep)
                            graph["edges"].append({"source": rel, "target": dep})

        return graph

    def get_report(self) -> ComplexityBudgetReport | None:
        """Load the latest audit report."""
        if self._report_path.exists():
            data = json.loads(self._report_path.read_text(encoding="utf-8"))
            return ComplexityBudgetReport(**data)
        return None

    def _save_report(self, report: ComplexityBudgetReport):
        self._report_path.write_text(
            json.dumps(report.__dict__, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
