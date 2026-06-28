"""Evidence management implementation."""

from app.domain.dto.evidence_dto import EvidenceDTO, EvidenceType
from app.infrastructure.database.mysql_client import mysql_connect
from app.config import AppSettings


from app.core.logger import get_logger

logger = get_logger(__name__)

class EvidenceManager:
    """Standardized manager for research evidence and results."""

    def __init__(self, settings: AppSettings):
        self._settings = settings

    def write_evidence(self, evidence: EvidenceDTO) -> bool:
        """Write research evidence to database."""
        try:
            # Assuming a table 'research_evidence' exists
            conn = mysql_connect(self._settings.mysql)
            with conn.cursor() as cur:
                sql = "INSERT INTO research_evidence (id, type, payload, created_at) VALUES (%s, %s, %s, %s)"
                cur.execute(sql, (
                    evidence.id,
                    evidence.type.value,
                    evidence.model_dump_json(),
                    evidence.created_at
                ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to write evidence {evidence.id}: {e}")
            return False

    def read_evidence(self, evidence_id: str) -> EvidenceDTO | None:
        """Read evidence by ID."""
        try:
            conn = mysql_connect(self._settings.mysql)
            with conn.cursor() as cur:
                cur.execute("SELECT id, type, payload, created_at FROM research_evidence WHERE id = %s", (evidence_id,))
                row = cur.fetchone()
                if not row:
                    return None
                return EvidenceDTO(id=row[0], type=EvidenceType(row[1]), payload=row[2], created_at=row[3])
        except Exception as e:
            logger.error(f"Failed to read evidence {evidence_id}: {e}")
            return None
