from __future__ import annotations
"""Agent Metrics Collector.

Exports agent performance, latency, and success rates for Prometheus integration.
"""


from prometheus_client import Counter, Histogram

# Swarm Metrics
SWARM_RUN_TOTAL = Counter("swarm_runs_total", "Total Swarm runs", ["preset"])
SWARM_TASK_LATENCY = Histogram("swarm_task_latency_seconds", "Latency per task", ["agent_id"])
SWARM_FAILURE_RATE = Counter("swarm_failures_total", "Swarm task failures", ["agent_id"])

# Risk Metrics
SENTINEL_ALERTS = Counter("sentinel_alerts_total", "Sentinel risk alerts", ["severity"])

def record_swarm_start(preset: str):
    SWARM_RUN_TOTAL.labels(preset=preset).inc()

def record_task_result(agent_id: str, duration: float, success: bool):
    SWARM_TASK_LATENCY.labels(agent_id=agent_id).observe(duration)
    if not success:
        SWARM_FAILURE_RATE.labels(agent_id=agent_id).inc()
