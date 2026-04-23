# Reference graph-builder examples

## `build_php_graphs.py` — 5-dimension PHP graph builder

Reference implementation for ∆4 (per-dimension graph extraction).
Produced by the OSS_Migration project's modernization of TT-RSS (PHP
→ Python). Uses tree-sitter-php + NetworkX + Leiden.

### Dimensions it builds

| Dimension | Graph shape                                            |
| --------- | ------------------------------------------------------ |
| include   | DiGraph of PHP file → file via require/include         |
| call      | DiGraph of qualified callables (file::func or Class::method) |
| db_table  | DiGraph of file → DB table name with SQL op kind       |
| class     | DiGraph of class → parent class or implemented interface |
| hook      | DiGraph of file → HOOK_* constant (REGISTERS / INVOKES) |

### Output

One JSON per dimension with `nodes / edges / communities / levels /
members`, plus a `communities_summary.json` aggregate, plus a
`report.txt` human-readable community listing.

### Dependencies

```text
pip install tree-sitter tree-sitter-php networkx igraph leidenalg
```

`leidenalg` + `igraph` are optional — NetworkX
`greedy_modularity_communities` is the fallback.

### Usage

```bash
python build_php_graphs.py \
    --source source-repos/ttrss-php/ttrss \
    --output tools/graph_analysis/output
```

### How to adapt for another source language

1. Replace the `tree_sitter_php` binding with the language-appropriate
   one (`tree_sitter_python`, `tree_sitter_typescript`, etc. — ~50
   languages supported).
2. Update the AST-node-name constants (function definition,
   class declaration, import statement) to match the new grammar.
3. Update the include/import regex for the target language's syntax.
4. Re-tune `PHP_PRIMITIVES` → a language-appropriate builtin blocklist.
5. For graph-types that don't apply (e.g., PHP-specific `HOOK_`
   constants), remove; add target-specific extractors for dimensions
   the new language exhibits (e.g., Python decorators as a
   registration dimension).

The NetworkX + Leiden pipeline after AST extraction is
language-agnostic — reuse as-is.

### Relationship to the specs-extractor skill

This script is the **∆4 reference implementation**. It is not itself
part of the skill's procedural flow — the skill invokes it (or an
adapted version) as a tool. The ∆3 dimension discovery determines
which graph builders run, and the ∆5 budget heuristics operate on
the output of whatever builder(s) produced the most relevant graphs
for this specific source.
