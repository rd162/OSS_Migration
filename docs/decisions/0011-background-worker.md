# ADR-0011: Background Worker Architecture

- **Status**: accepted
- **Date proposed**: 2026-04-03
- **Date accepted**: 2026-04-04
- **Deciders**: rd

## Context

The PHP codebase runs a background feed update daemon (`update_daemon2.php`) that:
- Forks child processes via `pcntl_fork()` to update feeds in parallel
- Uses `flock()` on a lockfile to prevent multiple daemon instances
- Runs in an infinite loop with configurable sleep intervals (`DAEMON_SLEEP_INTERVAL`)
- Supports a configurable max feeds per update cycle (`DAEMON_FEED_LIMIT=500`) and parallel child processes (`MAX_JOBS=2`)
- Performs housekeeping tasks: session garbage collection, feed purging, OPML auto-import

Additionally, `update.php` provides CLI commands for one-shot operations (update all feeds, update single feed, user management). Some deployments use cron instead of the daemon.

The Python replacement must support:
- Periodic feed updates (every N minutes per feed)
- Parallel processing of independent feeds
- Housekeeping tasks (purge, session cleanup, digest emails)
- Graceful shutdown and restart
- Monitoring and observability

## Options

### A: Celery + Redis

Use Celery as the distributed task queue with Redis as the broker and result backend. Celery Beat handles periodic scheduling. Each feed update is a Celery task.

- Industry standard for Python background tasks
- Built-in retry, rate limiting, priority queues
- Celery Beat for periodic scheduling (replaces cron + daemon loop)
- Flower for real-time monitoring dashboard
- Redis shared with session store (ADR-0007)

### B: APScheduler

Use APScheduler (Advanced Python Scheduler) with a PostgreSQL or Redis job store. Jobs are scheduled in-process or via a separate scheduler process.

- Lighter than Celery — single process, no broker required (with in-process store)
- Supports cron-like, interval, and date triggers
- Less mature for distributed / multi-worker scenarios
- No built-in monitoring dashboard
- Job store in PostgreSQL avoids Redis dependency

### C: asyncio Tasks (In-Process)

Run background tasks as `asyncio` coroutines within the same process (requires FastAPI or async framework). Use `asyncio.create_task()` for feed updates, `asyncio.sleep()` for scheduling.

- No external dependencies
- Requires async framework (couples to ADR-0002 decision)
- Single-process — no parallelism beyond async I/O
- CPU-bound tasks (feed parsing) block the event loop without `run_in_executor`
- No persistence — tasks lost on process restart

### D: systemd Timer + Script

Use systemd timers (or cron) to invoke a Python CLI script periodically. The script updates all due feeds, then exits. No long-running daemon.

- Simplest operational model
- No broker, no queue, no daemon
- Parallelism via `concurrent.futures.ProcessPoolExecutor` within the script
- No real-time monitoring; relies on systemd journal / log files
- Scheduling granularity limited to systemd timer resolution

## Trade-off Analysis

| Criterion | A: Celery + Redis | B: APScheduler | C: asyncio | D: systemd Timer |
|-----------|------------------|----------------|------------|-------------------|
| Parallelism | Excellent (workers) | Limited (threads) | I/O only (async) | Good (ProcessPool) |
| Scheduling flexibility | Excellent (Beat) | Excellent | Manual | Good (systemd timers) |
| Retry / error handling | Built-in | Basic | Manual | Manual |
| Monitoring | Flower dashboard | Custom | Custom | journalctl |
| Operational complexity | Medium (Redis + workers) | Low | Low | Very low |
| Scalability | Horizontal (add workers) | Vertical only | Vertical only | Vertical only |
| Task persistence | Yes (Redis/DB) | Yes (job store) | No | N/A (stateless runs) |
| Infrastructure requirements | Redis | None or PostgreSQL | None | systemd |
| Community / ecosystem | Very large | Medium | Python stdlib | OS-level |

## Preliminary Recommendation

**Option A (Celery + Redis)** — the proven choice for Python background processing at scale. Key reasons:

1. **Redis is already required** for session management (ADR-0007), so no new infrastructure
2. **Celery Beat** replaces both the daemon loop and cron scheduling with a single declarative configuration
3. **Flower** provides real-time task monitoring out of the box
4. **Horizontal scaling**: add Celery workers to handle more feeds without code changes
5. **Retry logic**: built-in exponential backoff for failed feed fetches (replaces PHP's manual retry counting)

Feed update task design:
- One Celery Beat schedule entry triggers a `dispatch_feed_updates` task every N minutes
- `dispatch_feed_updates` queries for due feeds and fans out individual `update_feed(feed_id)` tasks
- Each `update_feed` task is idempotent and independently retryable

## Decision

**Option A: Celery + Redis**

Feed update pipeline uses a two-task fan-out architecture:
- One Celery Beat schedule entry triggers `dispatch_feed_updates` every N minutes (configurable via `DAEMON_SLEEP_INTERVAL` equivalent)
- `dispatch_feed_updates` queries for feeds due for update and fans out one `update_feed(feed_id)` task per feed
- Each `update_feed` task is idempotent and independently retryable (max 3 retries, exponential backoff)
- Redis broker is shared with the session store (ADR-0007) — no new infrastructure required
- Celery Beat runs as exactly one instance (single-replica or leader election)

## Consequences

- If Option A: Redis becomes a hard runtime dependency (shared with sessions)
- If Option A: Celery workers run as separate processes (systemd units or Docker containers)
- If Option A: Celery Beat must run as exactly one instance (leader election or single-replica)
- If Option B: simpler deployment but limited scalability for large installations
- If Option C: tightly coupled to async framework choice; not viable with Flask
- If Option D: simplest deployment but no real-time monitoring or dynamic scheduling
