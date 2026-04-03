# ADR-0015: HTTP Client for Feed Fetching

- **Status**: proposed
- **Date proposed**: 2026-04-03
- **Deciders**: TBD

## Context

The PHP codebase fetches feeds using `curl` via the `fetch_file_contents()` function in `include/functions.php`. Key behaviors:
- 45-second timeout (`CURLOPT_TIMEOUT`)
- Follows redirects up to 20 hops (`CURLOPT_FOLLOWLOCATION`)
- Conditional GET with `If-Modified-Since` and `If-None-Match` (ETag) headers
- Custom User-Agent string (`SELF_USER_AGENT`)
- HTTP Basic Auth for authenticated feeds
- SSL certificate verification (configurable)
- Proxy support (`HTTP_PROXY`)
- Cookie handling for feeds that require session cookies
- Response size limiting to prevent memory exhaustion

The Python replacement must support all these features. Feed fetching is the most I/O-intensive operation — a typical installation fetches hundreds to thousands of feeds, making concurrency and efficiency critical.

## Options

### A: requests (Synchronous)

Use `requests`, the most popular Python HTTP library. Synchronous, blocking I/O. Concurrency achieved via thread pools (e.g., `concurrent.futures.ThreadPoolExecutor`).

- Extremely well-known, mature, battle-tested
- Simple API for all required features
- Synchronous — requires threads for concurrency
- `requests-cache` available for response caching
- Session objects for connection pooling and cookie persistence

### B: httpx (Async + Sync)

Use `httpx`, a modern HTTP client that supports both sync and async modes. API closely mirrors `requests` but adds HTTP/2 and async support.

- Both sync and async interfaces (same API)
- HTTP/2 support (multiplexed connections)
- Built-in timeout configuration (connect, read, write, pool)
- `If-Modified-Since` / ETag conditional requests supported
- Connection pooling via `AsyncClient` / `Client`
- Actively maintained, growing adoption

### C: aiohttp (Async Only)

Use `aiohttp`, the established async HTTP client for Python. Fully async, requires `asyncio` event loop.

- Mature async HTTP client (large community)
- Excellent performance for high-concurrency I/O
- Different API from `requests` (less familiar)
- Requires async framework or manual event loop management
- `ClientSession` for connection pooling
- No sync mode — testing and CLI usage require `asyncio.run()`

## Trade-off Analysis

| Criterion | A: requests | B: httpx | C: aiohttp |
|-----------|-----------|---------|------------|
| Async support | No (threads only) | Yes (native) | Yes (native, async-only) |
| HTTP/2 | No | Yes | No |
| API familiarity | Highest | High (requests-like) | Medium |
| Conditional GET (ETag/If-Modified-Since) | Manual headers | Manual headers | Manual headers |
| Connection pooling | Session object | Client object | ClientSession |
| Timeout granularity | Total only | Connect/read/write/pool | Total + individual |
| Proxy support | Yes | Yes | Yes |
| SSL configuration | Yes | Yes | Yes |
| Concurrency model | ThreadPoolExecutor | asyncio + gather | asyncio + gather |
| Feed fetching throughput | Limited by threads | High (async + HTTP/2) | High (async) |
| Sync usage (CLI, tests) | Native | Native (sync mode) | Requires asyncio.run() |
| Community / maturity | Very high | High (growing) | High |
| Cookie handling | Session cookies | Client cookies | ClientSession cookies |

## Preliminary Recommendation

**Option B (httpx)** — provides the best balance of modern features and practical usability:

1. **Async support** enables fetching hundreds of feeds concurrently without thread overhead
2. **HTTP/2 multiplexing** reduces connection overhead for hosts serving multiple feeds
3. **Sync mode** available for CLI tools, tests, and simple scripts (no `asyncio.run()` boilerplate)
4. **requests-compatible API** minimizes learning curve
5. **Granular timeouts** (connect: 10s, read: 45s) replace the single `CURLOPT_TIMEOUT`

Feed fetching architecture:
```python
async with httpx.AsyncClient(
    timeout=httpx.Timeout(connect=10.0, read=45.0, write=10.0, pool=5.0),
    follow_redirects=True,
    max_redirects=20,
    http2=True,
) as client:
    # Fan out feed fetches with concurrency limit
    results = await asyncio.gather(*[
        fetch_feed(client, feed) for feed in due_feeds
    ])
```

Conditional GET implementation:
- Store `Last-Modified` and `ETag` from responses in the `ttrss_feeds` table
- Send `If-Modified-Since` and `If-None-Match` headers on subsequent requests
- Handle `304 Not Modified` by skipping feed parsing

## Decision

**TBD**

## Consequences

- If Option B: httpx is a newer library than requests but is stable and widely adopted
- If Option B: HTTP/2 support can reduce bandwidth and latency for multi-feed hosts
- If Option B: async feed fetching integrates naturally with Celery tasks (run async within sync task via `asyncio.run()`)
- If Option A: simpler but thread-based concurrency is less efficient for I/O-bound workloads
- If Option C: best async performance but async-only API complicates CLI tools and testing
- All options: conditional GET support must be implemented at the application layer (storing and sending ETag/Last-Modified headers)
