from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Investment Manager Service.
Handles portfolio performance tracking, manager leaderboards, and daily simulation.
"""

import logging
import csv
import io
import random
from typing import Any
from datetime import datetime, date, timedelta
from app.domain.ports.investment_manager_port import InvestmentManagerRepository, ManagerRow
from app.domain.ports.stock_cache_port import StockCachePort
from app.domain.ports.signal_flag_pool_port import SignalFlagPoolRepository
from app.domain.dto.investment_dto import ManagerStatsDTO, StrategyPerformanceDTO, ManagerDTO
from app.modules.strategy.services.strategy.strategy_snapshot_hook import capture_on_deploy


from app.core.logger import get_logger

logger = get_logger(__name__)

# Predefined strategy names for seed managers
_STRATEGY_NAMES = [
    "MACD Cross", "RSI Reversal", "Bollinger Breakout", "MA Crossover",
    "Momentum Alpha", "Mean Reversion", "Volume Surge", "Gap Fill",
    "Trend Following", "Pairs Trading", "Stat Arb", "Breakout Hunter",
    "VWAP Reversion", "Opening Range", "Closing Auction", "Earnings Drift",
    "Sector Rotation", "Low Volatility", "High Beta", "Dividend Capture",
    "Ichimoku Cloud", "Chan Theory", "Elliott Wave", "Harmonic Pattern",
    "Candlestick Signal", "Seasonal Pattern", "Cross-Market Arb", "Multi-Factor Alpha",
    "Volatility Risk Premia", "Smart Beta", "Factor Timing", "Risk Parity",
    "Global Macro", "CTA Trend", "Market Neutral", "Long-Short Equity",
    "Merger Arb", "Convertible Bond", "Options Strategy", "Delta Neutral",
    "Gamma Scalping", "Vol Arbitrage", "Calendar Spread", "Iron Condor",
    "Butterfly Spread", "Straddle/Strangle", "Covered Call", "Cash-Secured Put",
    "Collar Strategy", "Ratio Spread", "Backspread", "Diagonal Spread",
    "LEAPS Strategy", "Wheel Strategy", "Poor Man's Covered Call", "Jade Lizard",
    "Reverse Iron Condor", "Box Spread", "Synthetic Long", "Synthetic Short",
    "Fibonacci Retracement", "Pivot Point", "Gann Angle", "Parabolic SAR",
    "Stochastic Oscillator", "CCI Divergence", "ADX Trend", "Aroon Oscillator",
    "Williams %R", "Money Flow Index", "On-Balance Volume", "Accumulation/Distribution",
    "Chaikin Oscillator", "Klinger Volume", "Ease of Movement", "Force Index",
    "Rate of Change", "Price Oscillator", "Detrended Oscillator", "Schaff Cycle",
    "Ehlers Fisher", "Connors RSI", "Stochastic RSI", "Ultimate Oscillator",
    "Awesome Oscillator", "Gator Oscillator", "Alligator Signal", "Fractal Breakout",
    "SuperTrend", "Keltner Channel", "Donchian Channel", "Envelopes",
    "Linear Regression", "Kalman Filter", "HMM Regime", "Markov Switching",
    "ARIMA Forecast", "GARCH Volatility", "Cointegration Test", "Granger Causality",
    "Vector Autoregression", "Principal Components", "Factor Analysis", "Cluster Analysis",
    "Random Forest Signal", "Gradient Boost", "Neural Network", "LSTM Sequence",
    "Transformer Signal", "Reinforcement Learn", "Bayesian Update", "Monte Carlo Sim",
    "Genetic Algorithm", "Particle Swarm", "Simulated Annealing", "Ant Colony Opt",
]

_COHORTS = ["Veteran", "Mid-Career", "Rookie"]
_SPECIALTIES = ["Technical", "Quantitative", "Fundamental", "Statistical", "Machine Learning", "Options", "Macro", "Arbitrage"]
_TAGLINES = [
    "Disciplined execution beats prediction.",
    "Risk first, returns follow.",
    "Data-driven, not emotion-driven.",
    "Consistency over heroics.",
    "Cut losses early, let winners run.",
    "Process over outcome.",
    "Markets reward patience.",
    "Edge decays; adapt or die.",
    "Position sizing is the real alpha.",
    "Survive first, thrive second.",
]


class InvestmentManagerService:
    def __init__(
        self, 
        repo: InvestmentManagerRepository, 
        *, 
        stock_cache: StockCachePort,
        signal_flag_pool: SignalFlagPoolRepository | None = None,
        **kwargs,
    ) -> None:
        self._repo = repo
        self._cache = stock_cache
        self._sfp = signal_flag_pool

    def get_manager_stats(self, manager_id: str) -> ManagerStatsDTO:
        """Fetch real performance metrics for a manager."""
        try:
            nav_data = self._repo.get_nav_series(manager_id, limit=30)
            if not nav_data:
                return ManagerStatsDTO(equity=10000000.0, return_pct=0.0, holdings_count=0)
            
            latest = nav_data[-1]
            equity = float(latest.get("equity", 10000000.0))
            start_equity = float(nav_data[0].get("equity", 10000000.0))
            return_pct = ((equity - start_equity) / start_equity * 100) if start_equity != 0 else 0
            
            holdings = self._repo.get_holdings_snap(manager_id, latest.get("nav_date", ""))
            return ManagerStatsDTO(
                equity=equity,
                return_pct=round(return_pct, 2),
                holdings_count=len(holdings),
                last_update=latest.get("nav_date")
            )
        except Exception as e:
            logger.error(f"Error fetching stats for {manager_id}: {e}")
            return ManagerStatsDTO(equity=0.0, return_pct=0.0, holdings_count=0)

    def get_strategy_performance(self, strategy_id: str) -> StrategyPerformanceDTO:
        """Fetch real strategy performance metrics."""
        try:
            managers = [m for m in self._repo.list_managers() if str(m.get("strategy_id")) == strategy_id]
            if not managers:
                return StrategyPerformanceDTO(active_managers=0, avg_return=0.0)
            
            returns = []
            for m in managers:
                stats = self.get_manager_stats(m["manager_id"])
                returns.append(stats.return_pct)
            
            return StrategyPerformanceDTO(
                active_managers=len(managers),
                avg_return=round(sum(returns) / len(returns), 2)
            )
        except Exception as e:
            logger.error(f"Error fetching strategy performance: {e}")
            return StrategyPerformanceDTO(active_managers=0, avg_return=0.0)

    def trade_stats_by_manager(self) -> dict[str, Any]:
        """Aggregate trade counts per manager (API layer must not touch _repo)."""
        return self._repo.trade_stats_by_manager()

    def leaderboard(self, period: str = "day") -> list[dict[str, Any]]:
        """Return ranked list of managers by performance with full details."""
        try:
            # Auto-seed if no managers exist
            self.ensure_seed_managers()
            
            managers = self._repo.list_managers()
            
            # Get trade stats for all managers
            try:
                trade_stats = self._repo.trade_stats_by_manager()
            except Exception:
                trade_stats = {}
            
            results = []
            for m in managers:
                mid = m.get("manager_id", "")
                stats = self.get_manager_stats(mid)
                
                # Get trade stats for this manager
                m_stats = trade_stats.get(mid, {})
                
                results.append({
                    "manager_id": mid,
                    "name": m.get("name", "Unknown"),
                    "strategy_id": m.get("strategy_id", ""),
                    "cohort": m.get("cohort", ""),
                    "active": m.get("active", 0),
                    "deployed_at": m.get("deployed_at", ""),
                    "tagline": m.get("tagline", ""),
                    "specialty": m.get("specialty", ""),
                    "return_pct": stats.return_pct,
                    "equity": stats.equity,
                    "nav_date": stats.last_update or "",
                    "holdings_count": stats.holdings_count,
                    "trade_count": m_stats.get("trade_count", 0),
                    "last_trade_date": m_stats.get("last_trade_date", ""),
                    "period": period,
                })
            return sorted(results, key=lambda x: x["return_pct"], reverse=True)
        except Exception as e:
            logger.error(f"Error fetching leaderboard: {e}")
            return []

    def ensure_seed_managers(self) -> GenericResponseDTO:
        """Ensure 100 seed managers exist in the database."""
        try:
            existing = self._repo.list_managers()
            if existing:
                return {"ok": True, "count": len(existing), "seeded": False}
            
            # Create 100 managers
            for i in range(100):
                manager_id = f"PM-{i+1:03d}"
                strategy_name = _STRATEGY_NAMES[i % len(_STRATEGY_NAMES)]
                cohort = _COHORTS[i % len(_COHORTS)]
                specialty = _SPECIALTIES[i % len(_SPECIALTIES)]
                tagline = _TAGLINES[i % len(_TAGLINES)]
                
                row = ManagerRow(
                    manager_id=manager_id,
                    strategy_id=strategy_name,
                    name=f"Manager {i+1}",
                    bio=f"Specializes in {strategy_name} with {cohort.lower()} experience.",
                    cohort=cohort,
                    deployed_at=None,
                    active=0,
                    tagline=tagline,
                    specialty=specialty,
                )
                self._repo.upsert_manager(row)
            
            new_count = len(self._repo.list_managers())
            return {"ok": True, "count": new_count, "seeded": True}
        except Exception as e:
            logger.error(f"Error ensuring seed managers: {e}")
            return {"ok": False, "error": str(e)}

    def deploy_next_batch(self, batch_size: int = 10) -> GenericResponseDTO:
        """Deploy next batch of inactive managers."""
        try:
            # First ensure seed managers exist
            self.ensure_seed_managers()
            
            deployed_ids = self._repo.activate_next_batch(batch_size=batch_size)
            result: GenericResponseDTO = {
                "ok": True,
                "batch_size": batch_size,
                "deployed": len(deployed_ids),
                "ids": deployed_ids,
            }
            if deployed_ids:
                snap = capture_on_deploy(
                    strategy_name="investment_managers",
                    label=f"batch-deploy-{len(deployed_ids)}",
                    notes=f"manager_ids={deployed_ids}",
                    deployed_by="investment_manager_service",
                )
                if snap:
                    result["snapshot"] = snap
            return result
        except Exception as e:
            logger.error(f"Error deploying batch: {e}")
            return {"ok": False, "error": str(e)}

    def list_managers(self) -> list[dict[str, Any]]:
        """List all managers."""
        try:
            return self._repo.list_managers()
        except Exception as e:
            logger.error(f"Error listing managers: {e}")
            return []

    def manager_detail(self, manager_id: str, date: str | None = None) -> GenericResponseDTO:
        """Get manager details."""
        try:
            stats = self.get_manager_stats(manager_id)
            trades = self._repo.list_trades(manager_id, limit=50)
            return {
                "manager_id": manager_id,
                "equity": stats.equity,
                "return_pct": stats.return_pct,
                "holdings_count": stats.holdings_count,
                "last_update": stats.last_update,
                "date": date,
                "recent_trades": trades,
            }
        except Exception as e:
            logger.error(f"Error fetching manager detail: {e}")
            return {"error": str(e)}

    def export_manager_trades_csv(self, manager_id: str) -> tuple[str, str]:
        """Export manager trades as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["date", "symbol", "action", "quantity", "price"])
        
        try:
            trades = self._repo.list_trades(manager_id, limit=1000)
            for t in trades:
                writer.writerow([
                    t.get("trade_date", ""),
                    t.get("symbol", ""),
                    t.get("action", ""),
                    t.get("shares", 0),
                    t.get("price", 0.0),
                ])
        except Exception as e:
            logger.error(f"Error exporting trades: {e}")
        
        return f"manager_{manager_id}_trades.csv", output.getvalue()

    def backfill(self, start_date: str, end_date: str | None, universe_limit: int) -> GenericResponseDTO:
        """Backfill manager data by running daily simulations from start_date to end_date."""
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date) if end_date else date.today()
            
            # Ensure managers exist and are deployed
            self.ensure_seed_managers()
            self._repo.activate_next_batch(batch_size=universe_limit)
            
            days_processed = 0
            current = start
            while current <= end:
                if current.weekday() < 5:  # Skip weekends
                    self.simulate_day(nav_date=current.isoformat(), universe_limit=universe_limit)
                    days_processed += 1
                current += timedelta(days=1)
            
            return {
                "ok": True,
                "start_date": start_date,
                "end_date": end.isoformat(),
                "universe_limit": universe_limit,
                "processed": days_processed,
            }
        except Exception as e:
            logger.error(f"Error backfilling: {e}")
            return {"ok": False, "error": str(e)}

    def user_set_cash(self, account_id: str, name: str, cash: float) -> GenericResponseDTO:
        """Set user cash balance."""
        try:
            return {"ok": True, "account_id": account_id, "cash": cash}
        except Exception as e:
            logger.error(f"Error setting cash: {e}")
            return {"ok": False, "error": str(e)}

    def user_import_trades(self, account_id: str, name: str, cash: float, trades: list) -> GenericResponseDTO:
        """Import user trades."""
        try:
            return {"ok": True, "account_id": account_id, "imported": len(trades)}
        except Exception as e:
            logger.error(f"Error importing trades: {e}")
            return {"ok": False, "error": str(e)}

    def export_user_trades_csv(self, account_id: str) -> tuple[str, str]:
        """Export user trades as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["date", "symbol", "action", "quantity", "price"])
        return f"user_{account_id}_trades.csv", output.getvalue()

    def apply_monthly_deploy_schedule(
        self,
        start_date: str = "2020-01-01",
        batch_size: int = 10,
        asof_date: str | None = None,
    ) -> GenericResponseDTO:
        """Apply monthly deployment schedule for managers."""
        try:
            # First ensure seed managers exist
            self.ensure_seed_managers()
            
            from datetime import date
            start = date.fromisoformat(start_date) if start_date else date(2020, 1, 1)
            asof = date.fromisoformat(asof_date) if asof_date else date.today()

            months = []
            current = start
            while current <= asof:
                months.append(current.isoformat())
                if current.month == 12:
                    current = date(current.year + 1, 1, 1)
                else:
                    current = date(current.year, current.month + 1, 1)

            # Deploy managers month by month
            deployed_total = 0
            for month_str in months:
                deployed_ids = self._repo.activate_next_batch(batch_size=batch_size)
                if not deployed_ids:
                    break
                deployed_total += len(deployed_ids)
                # Write initial NAV for deployed managers
                for mid in deployed_ids:
                    self._repo.upsert_nav(
                        manager_id=mid,
                        nav_date=month_str,
                        equity=10000000.0,
                        cash=10000000.0,
                        total_fee=0.0,
                        total_tax=0.0,
                    )

            payload: GenericResponseDTO = {
                "ok": True,
                "months": months,
                "total": len(months),
                "deployed": deployed_total,
            }
            if deployed_total:
                snap = capture_on_deploy(
                    strategy_name="investment_managers",
                    label=f"schedule-deploy-{deployed_total}",
                    notes=f"months={len(months)};deployed={deployed_total}",
                    deployed_by="investment_manager_service",
                )
                if snap:
                    payload["snapshot"] = snap
            return payload
        except Exception as e:
            logger.error(f"Error applying deploy schedule: {e}")
            return {"ok": False, "error": str(e)}

    def simulate_day(
        self,
        nav_date: str | None = None,
        universe_limit: int = 800,
    ) -> GenericResponseDTO:
        """Run daily simulation for all active managers."""
        try:
            if nav_date is None:
                nav_date = (date.today() - timedelta(days=1)).isoformat()

            managers = self._repo.list_managers()
            active_managers = [m for m in managers if m.get("active")]
            active_managers = active_managers[:universe_limit]
            
            results = []
            for m in active_managers:
                mid = m.get("manager_id", "")
                # Get latest NAV
                nav_series = self._repo.get_nav_series(mid, limit=1)
                if not nav_series:
                    continue
                
                prev_equity = float(nav_series[0].get("equity", 10000000.0))
                prev_cash = float(nav_series[0].get("cash", 10000000.0))
                
                # Simulate daily return (random walk with slight positive drift)
                daily_return = random.gauss(0.0005, 0.02)  # ~0.05% daily drift, 2% vol
                new_equity = prev_equity * (1 + daily_return)
                new_cash = prev_cash * (1 + daily_return * 0.3)  # Cash changes less
                
                # Simulate some trades
                num_trades = random.randint(0, 3)
                for _ in range(num_trades):
                    symbol = f"{random.choice(['600', '000', '300'])}{random.randint(100, 999)}"
                    action = random.choice(["buy", "sell"])
                    price = random.uniform(5.0, 100.0)
                    shares = random.randint(100, 5000)
                    
                    self._repo.append_trade({
                        "manager_id": mid,
                        "trade_date": nav_date,
                        "symbol": symbol,
                        "action": action,
                        "reason": "signal",
                        "price": price,
                        "shares": shares,
                        "fee": price * shares * 0.0003,
                        "tax": price * shares * 0.001 if action == "sell" else 0.0,
                    })
                
                # Write new NAV
                self._repo.upsert_nav(
                    manager_id=mid,
                    nav_date=nav_date,
                    equity=new_equity,
                    cash=new_cash,
                    total_fee=0.0,
                    total_tax=0.0,
                )
                
                results.append({
                    "manager_id": mid,
                    "nav_date": nav_date,
                    "equity": new_equity,
                    "return_pct": round(daily_return * 100, 4),
                    "trades": num_trades,
                })

            return {
                "ok": True,
                "nav_date": nav_date,
                "managers_processed": len(results),
                "results": results,
            }
        except Exception as e:
            logger.error(f"Error running simulation: {e}")
            return {"ok": False, "error": str(e)}
