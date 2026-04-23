# App Archetype → Candidate Dimensions (starter table)

Use this as a **starting point** for ∆3. Drop rows that don't apply;
add rows for dimensions the source actually exhibits. Every dimension
carried forward must be grounded in concrete source evidence.

---

## Archetype detection

Detect in ∆1 from source shape + entry points + deployment artifacts.
An app may span multiple archetypes (e.g. web app + daemon).

| Archetype               | Tell-tale evidence                                              |
| ----------------------- | --------------------------------------------------------------- |
| Web application         | HTTP entry, templates, session store, DB                        |
| REST/RPC API service    | HTTP entry, no UI, API contract layer, DB                       |
| CLI tool                | `main()` / argparse / click, no HTTP layer                      |
| Daemon / background job | Long-running loop, scheduler, worker pool, no HTTP              |
| Desktop application     | Event loop, widget framework (Qt, wx, Electron)                 |
| Mobile application      | Platform manifest, view hierarchy, lifecycle callbacks          |
| ETL / data pipeline     | Source → transform → sink DAG, batch scheduler                  |
| Protocol implementation | Packet parsers, state machine, bounded I/O loop                 |
| Library / SDK           | Public API surface, no own entry point, published package       |
| Embedded / IoT          | HAL layer, timer-driven code, constrained memory                |
| Messaging broker / bus  | Topics, subscribers, producers, delivery guarantees             |
| Batch / reporting       | Scheduled job → query → format → deliver                        |
| Plugin host             | Hook registry, plugin loader, extension-point interface         |
| Mixed                   | Multiple archetypes — analyse each                              |

---

## Universal dimensions (almost always relevant)

| Dimension           | Captures                                         |
| ------------------- | ------------------------------------------------ |
| Call graph          | Caller → callee edges between functions/methods  |
| Module / include    | Static import / include edges between files     |
| Class hierarchy     | Class / interface extends / implements graph     |
| File inventory      | Size, language, one-line purpose per file        |

These apply to any non-trivial source. Always extract them.

---

## Archetype → candidate dimensions

### Web application

| Dimension                            | Purpose                                                  |
| ------------------------------------ | -------------------------------------------------------- |
| Entity / schema graph                | Models before business logic                             |
| API / route surface                  | Inbound contract — order of endpoint migration           |
| Frontend / backend coupling          | HTML/JS + server handler pairs                           |
| Session / auth surface               | Trust boundaries, credential handling                    |
| Plugin / hook graph (if pluggable)   | Extension-point coverage + parity                        |
| Caching / counter graph              | Derived-state recomputation order                        |
| Background-job graph (if present)    | Daemon / worker boundary                                 |
| Template / view graph                | Server-rendered templates + inheritance                  |
| Security surface                     | Auth, crypto, CSRF, session, input-validation layers     |
| Deployment topology                  | Container / reverse-proxy / infra graph                  |

### REST/RPC API service

| Dimension                   | Purpose                                       |
| --------------------------- | --------------------------------------------- |
| Entity / schema graph       | Same as web app                               |
| API contract surface        | Endpoint set, versioning, error envelope     |
| Service dependency graph    | Outbound calls to other services / databases  |
| Authn / authz               | Token / JWT / OAuth surface                   |
| Error contract              | Exception → HTTP code mapping                 |
| Background-job graph        | Webhooks / async workers                      |

### CLI tool

| Dimension                 | Purpose                                       |
| ------------------------- | --------------------------------------------- |
| Command tree              | Sub-commands + flags + options                |
| Input / output contract   | stdin / stdout / file IO / exit codes         |
| Config precedence         | Flag > env > file > default                   |
| Filesystem surface        | Read / write paths, lock files                |
| Side-effect boundary      | Network, subprocess, mutable state            |

### Daemon / background job

| Dimension               | Purpose                                     |
| ----------------------- | ------------------------------------------- |
| Event loop topology     | Scheduler + handlers + dispatch             |
| Queue / topic graph     | Source queues → processors → sinks          |
| Timer / cron surface    | Scheduled jobs + intervals                  |
| State machine           | Process lifecycle (init / run / stop)       |
| Observability surface   | Logs, metrics, health checks                |

### ETL / data pipeline

| Dimension                     | Purpose                                 |
| ----------------------------- | --------------------------------------- |
| Source → sink DAG             | Pipeline topology; batch vs stream      |
| Schema-evolution graph        | Input schemas × output schemas          |
| Transformation graph          | Step-by-step data transformations       |
| Idempotency / checkpoint map  | Restart / backfill boundary             |

### Protocol implementation

| Dimension                  | Purpose                                |
| -------------------------- | -------------------------------------- |
| Protocol state machine     | States + events + transitions          |
| Packet / frame grammar     | Wire-format parsing + validation       |
| Timer / timeout graph      | Keepalive, retransmit, deadline        |
| Error / alert surface      | Protocol-level error handling          |
| Interoperability matrix    | Peer implementations + known quirks    |

### Library / SDK

| Dimension                 | Purpose                                  |
| ------------------------- | ---------------------------------------- |
| Public API surface        | Exported symbols + stability guarantees  |
| Version compatibility     | Major / minor / patch boundaries         |
| Transitive deps graph     | Third-party coupling                     |
| Example / test surface    | Test coverage per API                    |

### Embedded / IoT

| Dimension                  | Purpose                              |
| -------------------------- | ------------------------------------ |
| Hardware-abstraction layer | HAL modules + their consumers        |
| Interrupt / ISR graph      | Time-critical paths                  |
| Memory / resource budget   | Per-module static allocation         |
| Peripheral driver map      | Device drivers + their abstractions  |
| Power / sleep state graph  | Sleep / wake transitions             |

### Plugin host / extensible system

| Dimension                  | Purpose                                     |
| -------------------------- | ------------------------------------------- |
| Hook / extension-point graph | Registration × invocation edges           |
| Plugin lifecycle           | Load / init / enable / disable / unload     |
| Sandbox boundary           | What plugins can do and cannot              |
| Compatibility matrix       | Plugin API version × host version           |

### Mobile application

| Dimension                       | Purpose                                  |
| ------------------------------- | ---------------------------------------- |
| View hierarchy                  | Screens + navigation graph               |
| Lifecycle event graph           | Create / resume / background / destroy   |
| Platform capability surface     | Camera, location, push, storage          |
| Asset pipeline                  | Bundled resources + localization         |

---

## Cross-cutting dimensions (add where they apply)

| Dimension                         | Add when                                    |
| --------------------------------- | ------------------------------------------- |
| Configuration / feature-flag      | Extensive config constants or flag surface  |
| Concurrency / scheduling          | Multi-threaded, async, event-driven         |
| Security surface                  | Handles auth, encryption, sessions, crypto  |
| Regulatory / compliance boundary  | GDPR / HIPAA / PCI scope                    |
| Observability / telemetry         | Logging, metrics, tracing instrumentation   |
| Internationalisation              | i18n / l10n infrastructure present          |
| Testing topology                  | Test types + fixture graph                  |

---

## How to use this table in ∆3

1. From ∆1, determine the archetype(s).
2. Start with the **Universal dimensions** + the **Archetype-specific**
   rows for every archetype the source exhibits.
3. Add **Cross-cutting** rows whose "Add when" condition is true.
4. For each candidate dimension: verify there is concrete source
   evidence (grep a representative construct). If zero evidence, drop it.
5. Add dimensions the table does not list but the source clearly needs
   (record the rationale in the ∆3 scratch note).
6. Target 6–12 dimensions for a typical mid-scale app. Fewer is fine
   for small apps; more is a sign of overclassifying.
