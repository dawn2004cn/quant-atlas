"""Tournament promote wires into paper trading scheduler."""

from app.domain.alpha.paper_trading import get_paper_trading_scheduler
from app.modules.strategy.services.tournament.paper_pool_adapter import PaperTradingPoolAdapter
from app.modules.strategy.services.tournament.strategy_tournament_service import (
    StrategyTournamentService,
    TournamentCandidate,
)


def test_accepted_candidate_submits_paper_trading():
    scheduler = get_paper_trading_scheduler()
    before = len(scheduler.get_queue_status())
    pool = PaperTradingPoolAdapter(scheduler=scheduler)
    svc = StrategyTournamentService(paper_pool=pool)
    verdict = svc.evaluate(
        TournamentCandidate(
            strategy_id="nl.test01",
            sharpe=2.0,
            max_drawdown=0.05,
            bias_passed=True,
        ),
    )
    assert verdict.accepted is True
    assert len(scheduler.get_queue_status()) == before + 1
    assert scheduler.get_account("nl.test01") is not None
