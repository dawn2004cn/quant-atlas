"""Investment Manager Repository — re-exports SQLite implementation.

Replaces broken facade chain (investment->facade->investment = circular).
"""
from app.infrastructure.repositories.sqlite.sqlite_investment_manager_repository import (
    SQLiteInvestmentManagerRepository as InvestmentManagerRepository,
)

__all__ = ["InvestmentManagerRepository"]
