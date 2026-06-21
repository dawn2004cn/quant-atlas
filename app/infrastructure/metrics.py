"""Prometheus Metrics Integration"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Agent metrics
agent_requests_total = Counter(
    'quant_atlas_agent_requests_total',
    'Total agent API requests',
    ['agent_type', 'status']
)

agent_duration_seconds = Histogram(
    'quant_atlas_agent_duration_seconds',
    'Agent request duration',
    ['agent_type']
)

llm_tokens_total = Counter(
    'quant_atlas_llm_tokens_total',
    'Total LLM tokens used',
    ['model', 'type']
)

llm_requests_total = Counter(
    'quant_atlas_llm_requests_total',
    'Total LLM requests',
    ['model', 'status']
)

swarm_tasks_running = Gauge(
    'quant_atlas_swarm_tasks_running',
    'Number of running swarm tasks'
)

swarm_tasks_total = Counter(
    'quant_atlas_swarm_tasks_total',
    'Total swarm tasks',
    ['preset', 'status']
)

swarm_tasks_duration_seconds = Histogram(
    'quant_atlas_swarm_tasks_duration_seconds',
    'Swarm task duration',
    ['preset']
)

# API metrics
api_requests_total = Counter(
    'quant_atlas_api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status']
)

api_request_duration_seconds = Histogram(
    'quant_atlas_api_request_duration_seconds',
    'API request duration',
    ['endpoint']
)

# System metrics
active_users = Gauge(
    'quant_atlas_active_users',
    'Number of active users'
)

market_data_cache_hits = Counter(
    'quant_atlas_market_data_cache_hits_total',
    'Total market data cache hits'
)

market_data_cache_misses = Counter(
    'quant_atlas_market_data_cache_misses_total',
    'Total market data cache misses'
)


def record_agent_request(agent_type: str, status: str):
    """Record agent request"""
    agent_requests_total.labels(agent_type=agent_type, status=status).inc()


def record_agent_duration(agent_type: str, duration: float):
    """Record agent duration"""
    agent_duration_seconds.labels(agent_type=agent_type).observe(duration)


def record_llm_usage(model: str, token_type: str, tokens: int):
    """Record LLM token usage"""
    llm_tokens_total.labels(model=model, type=token_type).inc(tokens)


def record_swarm_task(preset: str, status: str):
    """Record swarm task"""
    swarm_tasks_total.labels(preset=preset, status=status).inc()


def record_swarm_duration(preset: str, duration: float):
    """Record swarm duration"""
    swarm_tasks_duration_seconds.labels(preset=preset).observe(duration)


def update_running_tasks(count: int):
    """Update running task count"""
    swarm_tasks_running.set(count)


def record_api_request(endpoint: str, method: str, status: int):
    """Record API request"""
    api_requests_total.labels(
        endpoint=endpoint,
        method=method,
        status=str(status)
    ).inc()


def get_metrics():
    """Get all metrics in Prometheus format"""
    return generate_latest()


def get_metrics_content_type():
    """Get Prometheus content type"""
    return CONTENT_TYPE_LATEST