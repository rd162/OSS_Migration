# Per-Dimension Extraction Strategies

How to build the NetworkX graph for each dimension. Each row: node type,
edge type, extraction method, expected size, what communities mean.

All dimensions converge on the same pipeline after extraction:

```text
source files → AST parse → typed nodes + edges → NetworkX graph →
Leiden community detection → SCC-condensed topological levels →
JSON export → downstream skill consumption
```

See `examples/build_php_graphs.py` for a reference implementation
covering five dimensions (include / call / class / db_table / hook).
Adapt per source language: tree-sitter supports ~50 languages with
the same API.

---

## Universal dimensions

### Call graph

- **Nodes**: qualified callable names — `file::func` or `Class::method`
- **Edges**: directed, one per call site: `caller → callee` with line number
- **Extraction**: AST walk over function/method bodies; resolve calls
  through visible scope + imports; skip language primitives
- **Size**: O(functions × avg-calls-per-function); typically 10k-200k edges
- **Communities mean**: natural function clusters — "auth module",
  "feed engine", "preference layer"
- **Dependency levels**: condense SCCs → topological rank; level 0 =
  leaves (callees with no outgoing calls); higher levels = callers

### Module / include graph

- **Nodes**: source files (or packages for package-level systems)
- **Edges**: directed, one per include/import statement
- **Extraction**: grep-parse import / require / include / use statements
- **Size**: O(files)
- **Communities mean**: file clusters with heavy cross-inclusion;
  typically aligns with logical modules
- **Dependency levels**: lowest = bootstrap (no includes), highest =
  entry points

### Class hierarchy graph

- **Nodes**: class + interface names
- **Edges**: `extends` (single parent) + `implements` (multiple)
- **Extraction**: AST walk over class/interface declarations
- **Size**: O(classes)
- **Communities mean**: inheritance trees — often one per subsystem
- **Dependency levels**: roots (no parent) = level 0; leaves = deepest

### File inventory (not a graph — a table)

- **Nodes**: source files
- **Attributes**: path, size (LOC), language, one-line purpose
- **Extraction**: `find` + `wc -l` + first-docstring / first-comment scan
- **Size**: O(files)
- **Used for**: source index spec, not community detection

---

## Data / schema dimensions

### Entity / schema graph (tables)

- **Nodes**: database table names
- **Edges**: foreign-key constraints — `child_table → parent_table`
- **Extraction**: parse DDL (SQL CREATE TABLE + FOREIGN KEY), OR parse
  ORM model classes with explicit FK declarations
- **Size**: O(tables)
- **Communities mean**: entity clusters — "user core", "articles",
  "preferences"
- **Dependency levels**: tables with no FK = level 0; migrate in
  ascending level order

### ORM model graph (when models are code-first)

- Same as entity graph but built from model classes rather than DDL
- **Edges**: include one-to-many, many-to-many relationship declarations
- **Communities mean**: module-level grouping of related models

### Query / access graph

- **Nodes**: source file × table
- **Edges**: `file → table` with operation type (SELECT / INSERT /
  UPDATE / DELETE / JOIN)
- **Extraction**: regex / AST scan for SQL strings or ORM calls;
  extract table names from FROM / JOIN / INTO / UPDATE clauses
- **Size**: O(files × tables-touched)
- **Communities mean**: files that access the same table cluster —
  candidates for a single service or repository

---

## API / service dimensions

### API / route surface

- **Nodes**: endpoint URL patterns + methods (GET /feeds, POST /auth/login)
- **Edges**: `endpoint → handler function`
- **Extraction**: parse routing declarations (decorators, config tables,
  dispatch tables in controllers)
- **Size**: O(endpoints)
- **Communities mean**: endpoint groups — "auth endpoints", "CRUD on
  resource X"

### Service dependency graph

- **Nodes**: service names (internal + external)
- **Edges**: `caller-service → callee-service` with protocol
- **Extraction**: grep for HTTP clients, gRPC stubs, queue publishers
- **Size**: O(services²) worst case, usually much sparser
- **Communities mean**: service clusters — natural bounded contexts
- **Dependency levels**: leaves = downstream-only services

### Event / message flow graph

- **Nodes**: topics / queues + publishers + subscribers
- **Edges**: `publisher → topic`, `topic → subscriber`
- **Extraction**: parse publish / subscribe / emit calls
- **Size**: O(topics + subscribers)
- **Communities mean**: event-flow pipelines
- **Dependency levels**: roots = producers; leaves = terminal consumers

---

## Extension / plugin dimensions

### Hook / extension-point graph

- **Nodes**: hook constants + (file or class that registers or invokes)
- **Edges**: `REGISTERS` (plugin → hook) and `INVOKES` (host → hook)
- **Extraction**: grep for `HOOK_` constants + their registration
  and invocation call-sites
- **Size**: O(hooks × (registers + invokes))
- **Communities mean**: hook families — "render-time hooks",
  "fetch-time hooks"

### Plugin lifecycle graph

- **Nodes**: plugin modules
- **Edges**: `plugin → lifecycle event` (load, init, enable, disable)
- **Extraction**: parse plugin manifests / base-class overrides

---

## Behavioural dimensions

### Protocol state machine

- **Nodes**: states (enum values)
- **Edges**: `state → next-state` labelled with triggering event
- **Extraction**: parse state enum + transition tables or switch/case
  dispatchers
- **Size**: O(states × events)
- **Communities mean**: sub-protocol phases (handshake, established,
  teardown)

### Concurrency / scheduling graph

- **Nodes**: goroutines / threads / tasks / actors
- **Edges**: `task → task` via channel / queue / mutex
- **Extraction**: parse `go` / `Thread.start` / `asyncio.create_task`
  / `spawn`
- **Communities mean**: concurrency clusters — producer-consumer
  pairs, worker pools

### Data-pipeline topology

- **Nodes**: source + transform + sink components
- **Edges**: `source → transform → sink`
- **Extraction**: parse pipeline DSL (Airflow DAG, dbt graph, pipe
  operators)
- **Size**: O(stages)
- **Communities mean**: pipeline sub-flows
- **Dependency levels**: sources = level 0; sinks = level max

---

## Cross-cutting dimensions

### Security surface

- Not always a clean graph — sometimes a **typed set** with
  relationships:
- **Nodes**: auth methods, crypto primitives, session managers,
  input validators, output encoders
- **Edges**: `auth-method → protected-resource`, `validator → input-source`
- **Extraction**: grep for crypto APIs, session APIs, auth decorators
- **Purpose**: coverage check for "every public endpoint has auth + CSRF"

### Configuration / feature-flag surface

- **Nodes**: config keys + flags
- **Edges**: `flag → gated-code-branch`
- **Extraction**: grep for flag-check calls + config-key reads

### Frontend / backend coupling

- **Nodes**: JS files / components + backend handlers
- **Edges**: `component → handler` via AJAX URL, RPC stub, form action
- **Extraction**: grep for `fetch(...)`, `XMLHttpRequest`, form
  actions, RPC client stubs
- **Communities mean**: UI features and their server support

### Template / view graph

- **Nodes**: templates
- **Edges**: `template → partial` via include / extends
- **Extraction**: parse template engine's `{% include %}` / `{% extends %}`

---

## Implementation notes

**One extractor per dimension** — don't try to build a universal parser.
A dimension's extractor is typically 100–300 lines of AST walk + regex.

**Community detection is the same for every dimension** — Leiden on
an undirected projection; fall back to NetworkX
`greedy_modularity_communities` if `leidenalg` is not installed.

**Dependency levels are the same** — `nx.condensation` (SCC → DAG) then
topological sort.

**Language-agnostic** — the reference implementation targets PHP via
tree-sitter. Replace the tree-sitter language binding
(`tree_sitter_python`, `tree_sitter_typescript`, etc.) to target
another language. ~50 languages supported.

**Output format** — one JSON per dimension with
`nodes / edges / communities / levels / members`. A
`communities_summary.json` aggregates across dimensions for the
downstream ∆5 budget planner.

**Large graphs** — for >100k edge graphs, sample or batch by file;
the community structure is usually stable under sub-sampling. Record
the sampling strategy in the dimension spec.
