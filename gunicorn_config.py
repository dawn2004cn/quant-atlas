"""
Production WSGI entry point for gunicorn with gevent workers.

Usage:
    gunicorn -c gunicorn_config.py app.wsgi:app
    # OR
    gunicorn -w 4 -k gevent -b 0.0.0.0:5000 app.wsgi:app
"""

import multiprocessing
import os

# Bind
bind = "0.0.0.0:{}".format(os.getenv("GUNICORN_PORT", "5000"))

# Workers
# Recommended: (2 * CPU cores) + 1 for gevent
workers = int(os.getenv("GUNICORN_WORKERS", str(multiprocessing.cpu_count() * 2 + 1)))
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gevent")
threads = int(os.getenv("GUNICORN_THREADS", "1"))

# Timeouts
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))

# Logging
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

# Process naming
proc_name = "quant-atlas"

# Server mechanics
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "10000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "1000"))
preload_app = True

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190


def on_starting(server):
    """Log startup info."""
    server.log.info("Quant Atlas starting with %s workers (%s class)", workers, worker_class)


def post_fork(server, worker):
    """Called after a worker has been forked."""
    server.log.debug("Worker spawned (pid=%s)", worker.pid)


def worker_abort(worker):
    """Called when a worker received the QUIT signal."""
    worker.log.info("Worker shutting down (pid=%s)", worker.pid)
