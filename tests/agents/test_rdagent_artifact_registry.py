"""RD-Agent 产物注册表。"""

from pathlib import Path

from app.infrastructure.rdagent.artifact_registry import RDAgentArtifactRegistry


def test_register_from_result_writes_bundle(tmp_path: Path):
    reg = RDAgentArtifactRegistry(tmp_path)
    result = {
        "ok": True,
        "provider_uri": "/data/qlib",
        "market": "csi300",
        "benchmark": "SH000300",
        "loop_n": 3,
        "report": {
            "round_count": 1,
            "rounds": [
                {
                    "tasks": [{"factor_name": "f1", "factor_formulation": "a+b"}],
                    "code_snippets": [{"file": "x.py", "snippet": "print(1)"}],
                    "qlib_metrics_series": {"ic": 0.01},
                }
            ],
        },
    }
    arts = reg.register_from_result("run-test-1", result)
    assert len(arts) == 2
    bundle = reg.get_run_bundle("run-test-1")
    assert bundle is not None
    assert bundle["run_id"] == "run-test-1"
    assert len(reg.list_artifact_summaries("run-test-1")) == 2
