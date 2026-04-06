# New: no PHP equivalent — Gunicorn production configuration.
# Phase 6 B3: process safety (R01, R02, R04).
import multiprocessing

# R01: gthread worker — NOT gevent.
# psycopg2 is NOT gevent-safe without psycogreen; gthread is the safe choice.
worker_class = "gthread"

# R04: standard formula; override via GUNICORN_WORKERS env if needed.
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
max_requests = 500
max_requests_jitter = 50
timeout = 120

bind = "0.0.0.0:5000"
loglevel = "info"
accesslog = "-"
errorlog = "-"


def post_fork(server, worker):
    """
    R02: post_fork fires after every worker fork regardless of preload_app.
    dispose() closes the parent's PostgreSQL file descriptors so the child
    opens fresh connections.  Skipping this causes shared-FD silent data
    corruption when multiple workers write through the same socket.

    New: no PHP equivalent — PHP used Apache/FPM process isolation automatically.
    """
    try:
        from ttrss.extensions import db
        db.engine.dispose()
    except RuntimeError:
        # If we're outside app context, skip disposal — the next request will create it
        pass
