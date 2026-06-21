"""RD-Agent 任务存储。"""

from pathlib import Path

from app.infrastructure.rdagent.job_store import RDAgentJobStore


def test_job_store_roundtrip(tmp_path: Path):
    store = RDAgentJobStore(tmp_path)
    jid = store.create(params_summary={"loop_n": 3})
    assert jid
    store.update(jid, progress=50, message="running")
    row = store.get(jid)
    assert row is not None
    assert row["progress"] == 50
    assert row.get("message") == "running"
