from __future__ import annotations
"""MySQL Factor Vault - 因子仓库持久化到 MySQL."""


from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.key_encryption import KeyEncryptionService
from app.domain.alpha.factor_vault import FactorVaultStorage
from app.infrastructure.database.db_manager import get_session

from ....core.logger import get_logger


logger = get_logger(__name__)


def _clamped_limit(limit: int, *, cap: int = 500) -> int:
    try:
        n = int(limit)
    except (TypeError, ValueError):
        n = 50
    return max(1, min(n, cap))


class MySQLFactorVault(FactorVaultStorage):
    """MySQL implementation of FactorVault with AES-256-GCM formula encryption."""

    _TABLE = "alpha_factors"
    _kms: KeyEncryptionService | None = None

    @staticmethod
    def _encrypt(text: str) -> str:
        try:
            if MySQLFactorVault._kms is None:
                MySQLFactorVault._kms = KeyEncryptionService()
            return MySQLFactorVault._kms.encrypt(text)
        except Exception:
            return text

    @staticmethod
    def _decrypt(token: str) -> str:
        try:
            if MySQLFactorVault._kms is None:
                MySQLFactorVault._kms = KeyEncryptionService()
            return MySQLFactorVault._kms.decrypt(token)
        except Exception:
            return token

    @staticmethod
    def _mysql_session():
        settings = get_settings()
        if not settings.use_mysql or settings.mysql is None:
            return None
        return get_session(settings.mysql)

    @staticmethod
    def _ensure_table(session: Session) -> None:
        """Create table if not exists (caller owns ``session`` lifecycle)."""
        table = MySQLFactorVault._TABLE
        session.execute(
            text(
                f"""
            CREATE TABLE IF NOT EXISTS `{table}` (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                factor_id VARCHAR(64) UNIQUE NOT NULL,
                formula TEXT NOT NULL,
                regime VARCHAR(32),
                sharpe_ratio DOUBLE,
                max_drawdown DOUBLE,
                backtest_result JSON,
                metadata JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_regime (regime),
                INDEX idx_sharpe (sharpe_ratio DESC),
                INDEX idx_created (created_at DESC)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
            )
        )
        session.commit()

    def save_factor(
        self,
        formula: str,
        *,
        regime: str | None = None,
        sharpe_ratio: float | None = None,
        max_drawdown: float | None = None,
        backtest_result: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        parents: list[str] | None = None,
    ) -> str:
        from ....domain.alpha.factor_vault import get_factor_vault
        from ....infrastructure.memory.arrow_pool import _default_json_dumps

        final_metadata = (metadata or {}).copy()
        if parents:
            final_metadata["parents"] = parents

        vault = get_factor_vault()
        factor_id = vault.save_factor(
            formula,
            regime=regime,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            backtest_result=backtest_result,
            metadata=final_metadata,
            parents=parents,
        )

        session = self._mysql_session()
        if session is None:
            logger.debug("MySQL not configured; factor saved in-memory only: %s", factor_id)
            return factor_id

        try:
            self._ensure_table(session)
            session.execute(
                text(
                    f"""
                INSERT INTO `{self._TABLE}`
                    (factor_id, formula, regime, sharpe_ratio, max_drawdown, backtest_result, metadata)
                    VALUES (:factor_id, :formula, :regime, :sharpe_ratio, :max_drawdown, :backtest_result, :metadata)
                    ON DUPLICATE KEY UPDATE
                        formula=VALUES(formula),
                        regime=VALUES(regime),
                        sharpe_ratio=VALUES(sharpe_ratio),
                        max_drawdown=VALUES(max_drawdown),
                        backtest_result=VALUES(backtest_result),
                        metadata=VALUES(metadata)
                """
                ),
                {
                    "factor_id": factor_id,
                    "formula": self._encrypt(formula),
                    "regime": regime,
                    "sharpe_ratio": sharpe_ratio,
                    "max_drawdown": max_drawdown,
                    "backtest_result": _default_json_dumps(backtest_result),
                    "metadata": _default_json_dumps(final_metadata),
                },
            )
            session.commit()
        except Exception as e:
            session.rollback()
            logger.warning("Failed to save factor to MySQL: %s", e)
        finally:
            session.close()

        return factor_id

    def patch_factor(self, factor_id: str, **updates: Any) -> bool:
        from ....domain.alpha.factor_vault import get_factor_vault
        from ....infrastructure.memory.arrow_pool import _default_json_dumps

        vault = get_factor_vault()
        if not vault.patch_factor(factor_id, **updates):
            return False

        session = self._mysql_session()
        if session is None:
            return True

        rec = vault.get_factor(factor_id)
        if not rec:
            return False

        try:
            self._ensure_table(session)
            session.execute(
                text(
                    f"""
                UPDATE `{self._TABLE}`
                SET regime = :regime,
                    sharpe_ratio = :sharpe_ratio,
                    max_drawdown = :max_drawdown,
                    backtest_result = :backtest_result,
                    metadata = :metadata
                WHERE factor_id = :factor_id
                """
                ),
                {
                    "factor_id": factor_id,
                    "regime": rec.get("regime"),
                    "sharpe_ratio": rec.get("sharpe_ratio"),
                    "max_drawdown": rec.get("max_drawdown"),
                    "backtest_result": _default_json_dumps(rec.get("backtest_result")),
                    "metadata": _default_json_dumps(rec.get("metadata")),
                },
            )
            session.commit()
            return True
        except Exception as exc:
            session.rollback()
            logger.warning("patch_factor failed for %s: %s", factor_id, exc)
            return False
        finally:
            session.close()

    def _row_decrypted(self, row: dict[str, Any]) -> dict[str, Any]:
        row = dict(row)
        if "formula" in row and isinstance(row["formula"], str):
            row["formula"] = self._decrypt(row["formula"])
        return row

    def get_factor(self, factor_id: str) -> dict[str, Any] | None:
        session = self._mysql_session()
        if session is None:
            return None
        try:
            self._ensure_table(session)
            row = (
                session.execute(
                    text(f"SELECT * FROM `{self._TABLE}` WHERE factor_id = :fid"),
                    {"fid": factor_id},
                )
                .mappings()
                .first()
            )
            if not row:
                return None
            return self._row_decrypted(dict(row))
        except Exception as exc:
            logger.warning("get_factor failed for %s: %s", factor_id, exc)
            return None
        finally:
            session.close()

    def search_factors(
        self,
        *,
        regime: str | None = None,
        min_sharpe: float | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        session = self._mysql_session()
        if session is None:
            return []
        safe_limit = _clamped_limit(limit)
        base = f"SELECT * FROM `{self._TABLE}`"
        clauses: list[str] = []
        params: dict[str, Any] = {}

        if regime:
            clauses.append("regime = :regime")
            params["regime"] = regime
        if min_sharpe is not None:
            clauses.append("sharpe_ratio >= :min_sharpe")
            params["min_sharpe"] = min_sharpe

        sql = base
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY sharpe_ratio DESC LIMIT :lim"
        params["lim"] = safe_limit

        try:
            self._ensure_table(session)
            rows = session.execute(text(sql), params).mappings().all()
            return [self._row_decrypted(dict(r)) for r in rows]
        except Exception as exc:
            logger.warning("search_factors failed: %s", exc)
            return []
        finally:
            session.close()

    def list_recent_factors(self, limit: int = 50) -> list[dict[str, Any]]:
        session = self._mysql_session()
        if session is None:
            return []
        safe_limit = _clamped_limit(limit)
        try:
            self._ensure_table(session)
            rows = (
                session.execute(
                    text(
                        f"SELECT * FROM `{self._TABLE}` ORDER BY created_at DESC LIMIT :lim"
                    ),
                    {"lim": safe_limit},
                )
                .mappings()
                .all()
            )
            return [self._row_decrypted(dict(r)) for r in rows]
        except Exception as exc:
            logger.warning("list_recent_factors failed: %s", exc)
            return []
        finally:
            session.close()
