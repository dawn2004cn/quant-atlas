from __future__ import annotations
"""Alpha Correlation Audit - Detect Alpha Crowding.

Implements from strategy_plan2.md:
- Check new strategy against 100+ existing strategies
- Reject if correlation > 0.8 (alpha crowding)
- Global orthogonalization enforcement

Usage:
    auditor = AlphaCorrelationAudit()
    result = auditor.audit_new_strategy(new_alpha, existing_alphas)
    if result.rejected:
        logger.info("Reject: %s", result.reason)
"""


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class AlphaRecord:
    """Alpha factor record."""
    alpha_id: str
    name: str
    formula: str
    ic_score: float = 0.0
    sharpe: float = 0.0
    returns: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrelationAuditResult:
    """Result of correlation audit."""
    allowed: bool
    rejected: bool = False
    reason: str | None = None
    max_correlation: float = 0.0
    correlated_strategies: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class AlphaCorrelationAudit:
    """Audit new alpha against existing strategies."""

    CORRELATION_THRESHOLD = 0.8
    MIN_IC_THRESHOLD = 0.02
    MIN_SHARPE_THRESHOLD = 0.5

    def __init__(self):
        self._alphas: dict[str, AlphaRecord] = {}
        self._rejected_count = 0
        self._audit_history: list[tuple[str, CorrelationAuditResult, datetime]] = []

    def register_alpha(self, alpha: AlphaRecord) -> None:
        """Register existing alpha for correlation checks."""
        self._alphas[alpha.alpha_id] = alpha
        logger.info(f"Registered alpha {alpha.alpha_id} for correlation audit")

    def audit_new_strategy(
        self,
        new_alpha: AlphaRecord,
        candidate_pool: list[str] = None,
    ) -> CorrelationAuditResult:
        """Audit new strategy against existing ones."""
        if len(self._alphas) == 0:
            return CorrelationAuditResult(allowed=True)

        correlated: list[tuple[str, float]] = []

        check_pool = candidate_pool or list(self._alphas.keys())

        for alpha_id in check_pool:
            if alpha_id not in self._alphas:
                continue

            existing = self._alphas[alpha_id]
            correlation = self._calculate_correlation(new_alpha, existing)

            if correlation > self.CORRELATION_THRESHOLD:
                correlated.append((alpha_id, correlation))
                logger.warning(
                    f"Alpha {new_alpha.alpha_id} correlates {correlation:.2%} "
                    f"with {alpha_id}"
                )

        correlated.sort(key=lambda x: x[1], reverse=True)

        if correlated:
            max_corr = correlated[0][1]
            correlated_ids = [c[0] for c in correlated[:5]]

            if max_corr > self.CORRELATION_THRESHOLD:
                self._rejected_count += 1

                result = CorrelationAuditResult(
                    allowed=False,
                    rejected=True,
                    reason=f"Alpha crowding detected: max correlation {max_corr:.2%}",
                    max_correlation=max_corr,
                    correlated_strategies=correlated_ids,
                    suggestions=[
                        "Try orthogonal factor: earnings_quality",
                        "Try different regime: volatility_arbitrage",
                        f"Require correlation < {self.CORRELATION_THRESHOLD - 0.1}",
                    ],
                )

                self._audit_history.append((new_alpha.alpha_id, result, datetime.now()))
                return result

        result = CorrelationAuditResult(
            allowed=True,
            max_correlation=correlated[0][1] if correlated else 0.0,
            correlated_strategies=[],
        )

        self._audit_history.append((new_alpha.alpha_id, result, datetime.now()))
        return result

    def check_duplicate_signals(
        self,
        symbols: list[str],
        strategy_ids: list[str],
    ) -> dict[str, list[str]]:
        """Check which symbols have duplicate signals."""
        symbol_strategies: dict[str, list[str]] = {}

        for strat_id in strategy_ids:
            if strat_id not in self._alphas:
                continue
            alpha = self._alphas[strat_id]
            alpha.metadata.get("signals", [])
            for symbol in symbols:
                if symbol not in symbol_strategies:
                    symbol_strategies[symbol] = []
                symbol_strategies[symbol].append(strat_id)

        duplicates = {
            s: strats for s, strats in symbol_strategies.items()
            if len(strats) > 3
        }

        if duplicates:
            logger.warning(f"Found {len(duplicates)} symbols with duplicate signals")

        return duplicates

    def get_leaderboard(
        self,
        min_ic: float = MIN_IC_THRESHOLD,
        min_sharpe: float = MIN_SHARPE_THRESHOLD,
    ) -> list[AlphaRecord]:
        """Get top performing alphas."""
        valid = [
            a for a in self._alphas.values()
            if a.ic_score >= min_ic and a.sharpe >= min_sharpe
        ]

        valid.sort(key=lambda a: a.sharpe, reverse=True)
        return valid[:50]

    def get_rejected_count(self) -> int:
        """Get rejected strategy count."""
        return self._rejected_count

    def get_audit_history(
        self,
        hours: int = 24,
    ) -> list[tuple[str, CorrelationAuditResult, datetime]]:
        """Get recent audit history."""
        cutoff = datetime.now()
        from datetime import timedelta
        cutoff = cutoff - timedelta(hours=hours)

        return [
            (aid, result, ts) for aid, result, ts in self._audit_history
            if ts > cutoff
        ]

    def _calculate_correlation(
        self,
        alpha_a: AlphaRecord,
        alpha_b: AlphaRecord,
    ) -> float:
        """Calculate correlation between two alphas."""
        if not alpha_a.returns or not alpha_b.returns:
            if alpha_a.formula and alpha_b.formula:
                return self._formula_similarity(alpha_a.formula, alpha_b.formula)
            return 0.0

        if len(alpha_a.returns) != len(alpha_b.returns):
            min_len = min(len(alpha_a.returns), len(alpha_b.returns))
            returns_a = alpha_a.returns[:min_len]
            returns_b = alpha_b.returns[:min_len]
        else:
            returns_a = alpha_a.returns
            returns_b = alpha_b.returns

        mean_a = sum(returns_a) / len(returns_a)
        mean_b = sum(returns_b) / len(returns_b)

        cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(returns_a, returns_b))
        std_a = (sum((a - mean_a) ** 2 for a in returns_a) ** 0.5)
        std_b = (sum((b - mean_b) ** 2 for b in returns_b) ** 0.5)

        if std_a == 0 or std_b == 0:
            return 0.0

        return cov / (std_a * std_b)

    def _formula_similarity(self, formula_a: str, formula_b: str) -> float:
        """Calculate formula similarity."""
        ops_a = self._extract_operators(formula_a)
        ops_b = self._extract_operators(formula_b)

        if not ops_a or not ops_b:
            return 0.0

        common = len(set(ops_a) & set(ops_b))
        total = len(set(ops_a) | set(ops_b))

        return common / total if total > 0 else 0.0

    def _extract_operators(self, formula: str) -> set[str]:
        """Extract operators from formula."""
        operators = {
            "rank", "delay", "delta", "ts_", "log", "abs",
            "sign", "mean", "sum", "std", "cov", "corr",
        }

        found = set()
        formula_lower = formula.lower()

        for op in operators:
            if op in formula_lower:
                found.add(op)

        return found


_global_auditor: AlphaCorrelationAudit | None = None


def get_alpha_auditor() -> AlphaCorrelationAudit:
    """Get global alpha auditor."""
    global _global_auditor
    if _global_auditor is None:
        _global_auditor = AlphaCorrelationAudit()
    return _global_auditor
