"""build_php_graphs.py — PHP Dependency Graph Analysis for TT-RSS Migration

PURPOSE
-------
Parse the TT-RSS PHP source tree with tree-sitter-php and build five NetworkX
dimension graphs.  Run Leiden community detection (or Louvain fallback) on
each graph's undirected projection, then compute SCC-based topological
dependency levels for the directed graphs.  Output JSON + human-readable
reports to help validate and correct:
  - specs/10-migration-dimensions.md
  - specs/13-decomposition-map.md

DIMENSIONS
----------
1. include  — DiGraph of PHP file → file via require_once / include_once
2. call     — DiGraph of qualified callables (file::func or Class::method)
3. db_table — DiGraph of file → DB table name with SQL operation kind
4. class    — DiGraph of PHP class → parent class or implemented interface
5. hook     — DiGraph of file → HOOK_* constant (REGISTERS or INVOKES)

COMMUNITY DETECTION
-------------------
- Primary:  leidenalg + igraph  (pip install leidenalg igraph)
- Fallback: NetworkX greedy_modularity_communities (no extra install needed)

OUTPUT (to --output dir, default tools/graph_analysis/output/)
--------------------------------------------------------------
  {dim}_graph.json          — nodes, edges, communities, levels, members
  communities_summary.json  — all dimensions combined
  report.txt                — human-readable community assignments

USAGE
-----
  cd OSS_Migration
  pip install tree-sitter tree-sitter-php networkx igraph leidenalg
  python tools/graph_analysis/build_php_graphs.py \\
      --source source-repos/ttrss-php/ttrss \\
      --output tools/graph_analysis/output

OPTIONAL FLAGS
--------------
  --dims include,call,db_table,class,hook   (subset of dimensions to build)
  --resolution 1.0                          (Leiden resolution parameter)
  --no-builtins                             (already default — skip PHP builtins)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Optional heavy dependencies
# ---------------------------------------------------------------------------
try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False
    print("[WARN] networkx not installed — install with: pip install networkx", file=sys.stderr)

try:
    import igraph as ig
    import leidenalg
    HAS_LEIDEN = True
except ImportError:
    HAS_LEIDEN = False
    print("[INFO] leidenalg/igraph not found — using NetworkX Louvain fallback", file=sys.stderr)

try:
    import tree_sitter_php as tsPHP
    from tree_sitter import Language, Parser
    HAS_TREESITTER = True
    PHP_LANGUAGE = Language(tsPHP.language_php())
except Exception as _ts_exc:
    HAS_TREESITTER = False
    print(f"[WARN] tree-sitter-php unavailable ({_ts_exc}) — "
          "install with: pip install tree-sitter tree-sitter-php", file=sys.stderr)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PHP_PRIMITIVES: Set[str] = {
    # type constructors / casts
    "array", "list", "object", "string", "int", "float", "bool",
    # inspection
    "isset", "empty", "unset", "is_array", "is_string", "is_int", "is_float",
    "is_bool", "is_null", "is_object", "is_numeric",
    # string
    "strlen", "substr", "strpos", "strrpos", "str_replace", "str_repeat",
    "str_pad", "str_split", "str_contains", "str_starts_with", "str_ends_with",
    "trim", "ltrim", "rtrim", "strtolower", "strtoupper", "ucfirst", "lcfirst",
    "ucwords", "implode", "explode", "nl2br", "htmlspecialchars",
    "htmlspecialchars_decode", "htmlentities", "strip_tags", "addslashes",
    "stripslashes", "quotemeta", "wordwrap", "sprintf", "printf", "fprintf",
    "vsprintf", "number_format", "chunk_split",
    # regex
    "preg_match", "preg_match_all", "preg_replace", "preg_replace_callback",
    "preg_split", "preg_quote",
    # array
    "count", "in_array", "array_key_exists", "array_keys", "array_values",
    "array_merge", "array_push", "array_pop", "array_shift", "array_unshift",
    "array_slice", "array_splice", "array_search", "array_unique",
    "array_reverse", "array_flip", "array_combine", "array_diff",
    "array_intersect", "array_filter", "array_map", "array_walk",
    "array_chunk", "array_pad", "array_column", "sort", "rsort", "asort",
    "arsort", "ksort", "krsort", "usort", "uasort", "uksort", "shuffle",
    # math
    "abs", "ceil", "floor", "round", "max", "min", "pow", "sqrt", "rand",
    "mt_rand", "floatval", "boolval", "settype", "intval", "strval",
    # date / time
    "date", "time", "mktime", "strtotime", "gmdate", "date_create",
    "date_format", "microtime", "sleep", "usleep",
    # json
    "json_encode", "json_decode",
    # output / control
    "echo", "print", "var_dump", "var_export", "print_r", "die", "exit",
    "header", "headers_sent", "ob_start", "ob_end_clean", "ob_get_clean",
    # filesystem (common)
    "file_exists", "is_file", "is_dir", "file_get_contents", "file_put_contents",
    "fopen", "fclose", "fread", "fwrite", "fgets", "fputs", "feof",
    "unlink", "rename", "mkdir", "rmdir", "glob", "scandir", "basename",
    "dirname", "realpath", "pathinfo",
    # misc
    "defined", "define", "constant", "class_exists", "method_exists",
    "function_exists", "get_class", "get_parent_class", "is_a",
    "call_user_func", "call_user_func_array", "func_get_args",
    "error_reporting", "set_error_handler", "trigger_error",
    "ini_set", "ini_get", "extension_loaded",
    "session_start", "session_destroy", "session_id",
    "md5", "sha1", "hash", "crc32", "base64_encode", "base64_decode",
    "urlencode", "urldecode", "rawurlencode", "rawurldecode",
    "http_build_query", "parse_url", "parse_str",
    "mysql_real_escape_string", "pg_escape_string",
    "chr", "ord",
}

SQL_TABLE_RE = re.compile(
    r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE|TRUNCATE)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
    re.IGNORECASE,
)
SQL_OP_RE = re.compile(
    r"\b(SELECT|INSERT|UPDATE|DELETE|TRUNCATE)\b",
    re.IGNORECASE,
)
HOOK_CONST_RE = re.compile(r"\bHOOK_[A-Z_]+\b")
INCLUDE_RE = re.compile(
    r"""(?:require_once|include_once|require|include)\s*[(\s]?\s*['"]([^'"]+)['"]""",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class NodeInfo:
    label: str
    file: Optional[str] = None
    line: Optional[int] = None
    loc: Optional[int] = None
    kind: Optional[str] = None   # function / method / static / class / table / hook

@dataclass
class EdgeInfo:
    src: str
    dst: str
    kind: Optional[str] = None
    line: Optional[int] = None

@dataclass
class PHPFileData:
    """All extracted information from a single PHP file."""
    path: str                             # relative to source root
    abs_path: str
    loc: int
    includes: List[Tuple[str, str]] = field(default_factory=list)  # (kind, target_rel)
    functions: List[Tuple[str, int]] = field(default_factory=list) # (name, line)
    methods: List[Tuple[str, str, int, str]] = field(default_factory=list)  # (cls, meth, line, kind)
    calls: List[Tuple[str, str, int]] = field(default_factory=list)         # (caller_qname, callee, line)
    classes: List[Tuple[str, Optional[str], List[str], int]] = field(default_factory=list)
    # classes: (name, parent, interfaces, line)
    db_accesses: List[Tuple[str, str, int]] = field(default_factory=list)   # (table, op, line)
    hook_registers: List[Tuple[str, int]] = field(default_factory=list)     # (hook_const, line)
    hook_invokes: List[Tuple[str, int]] = field(default_factory=list)       # (hook_const, line)

# ---------------------------------------------------------------------------
# Tree-sitter helpers
# ---------------------------------------------------------------------------

def _iter_tree(node: Any) -> Iterator[Any]:
    """Recursive pre-order traversal of a tree-sitter Node."""
    yield node
    for child in node.children:
        yield from _iter_tree(child)


def _node_text(node: Any, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _line(node: Any) -> int:
    return node.start_point[0] + 1  # 1-based


# ---------------------------------------------------------------------------
# PHP File Parser
# ---------------------------------------------------------------------------

class PHPFileParser:
    """Parse a single PHP file using tree-sitter and extract structured data."""

    def __init__(self, source_root: Path):
        self.source_root = source_root
        if HAS_TREESITTER:
            self._parser = Parser(PHP_LANGUAGE)
        else:
            self._parser = None

    def parse_file(self, abs_path: Path) -> PHPFileData:
        rel = str(abs_path.relative_to(self.source_root))
        source_bytes = abs_path.read_bytes()
        loc = source_bytes.count(b"\n") + 1

        data = PHPFileData(path=rel, abs_path=str(abs_path), loc=loc)

        if HAS_TREESITTER and self._parser is not None:
            try:
                tree = self._parser.parse(source_bytes)
                self._extract_all(tree.root_node, source_bytes, data)
            except Exception as exc:
                print(f"[WARN] tree-sitter parse error in {rel}: {exc}", file=sys.stderr)
                self._regex_fallback(source_bytes, data)
        else:
            self._regex_fallback(source_bytes, data)

        return data

    # ------------------------------------------------------------------
    # Tree-sitter extraction
    # ------------------------------------------------------------------

    def _extract_all(self, root: Any, src: bytes, data: PHPFileData) -> None:
        """Walk the entire AST and dispatch on node type."""
        class_stack: List[str] = []
        func_stack: List[str] = []
        self._walk(root, src, data, class_stack, func_stack)

    def _walk(self, node: Any, src: bytes, data: PHPFileData,
              class_stack: List[str], func_stack: List[str]) -> None:
        ntype = node.type

        if ntype == "class_declaration":
            self._handle_class(node, src, data, class_stack, func_stack)
            return  # handled recursion inside

        if ntype in ("function_definition", "function_declaration"):
            self._handle_function(node, src, data, class_stack, func_stack)
            return  # recursion handled inside

        if ntype == "method_declaration":
            self._handle_method(node, src, data, class_stack, func_stack)
            return  # recursion handled inside

        if ntype in ("include_expression", "include_once_expression",
                     "require_expression", "require_once_expression"):
            self._handle_include(node, src, data)

        if ntype == "function_call_expression":
            self._handle_function_call(node, src, data, class_stack, func_stack)

        if ntype == "member_call_expression":
            self._handle_member_call(node, src, data, class_stack, func_stack)

        if ntype == "static_method_call_expression":
            self._handle_static_call(node, src, data, class_stack, func_stack)

        if ntype == "string" or ntype == "encapsed_string":
            self._handle_string(node, src, data)

        # Always recurse
        for child in node.children:
            self._walk(child, src, data, class_stack, func_stack)

    def _handle_class(self, node: Any, src: bytes, data: PHPFileData,
                      class_stack: List[str], func_stack: List[str]) -> None:
        name_node = self._child_by_type(node, "name")
        if name_node is None:
            return
        class_name = _node_text(name_node, src)
        line = _line(node)

        parent: Optional[str] = None
        interfaces: List[str] = []

        base_clause = self._child_by_type(node, "base_clause")
        if base_clause:
            for n in _iter_tree(base_clause):
                if n.type == "name":
                    parent = _node_text(n, src)
                    break

        class_iface = self._child_by_type(node, "class_implements")
        if class_iface:
            for n in class_iface.children:
                if n.type == "name":
                    interfaces.append(_node_text(n, src))

        data.classes.append((class_name, parent, interfaces, line))
        class_stack.append(class_name)

        # Recurse into class body
        body = self._child_by_type(node, "declaration_list")
        if body:
            for child in body.children:
                self._walk(child, src, data, class_stack, func_stack)

        class_stack.pop()

    def _handle_function(self, node: Any, src: bytes, data: PHPFileData,
                         class_stack: List[str], func_stack: List[str]) -> None:
        name_node = self._child_by_type(node, "name")
        if name_node is None:
            return
        fname = _node_text(name_node, src)
        line = _line(node)

        if class_stack:
            # Nested function inside class body — treat as method
            cls = class_stack[-1]
            data.methods.append((cls, fname, line, "function"))
        else:
            data.functions.append((fname, line))

        func_stack.append(fname)
        for child in node.children:
            self._walk(child, src, data, class_stack, func_stack)
        func_stack.pop()

    def _handle_method(self, node: Any, src: bytes, data: PHPFileData,
                       class_stack: List[str], func_stack: List[str]) -> None:
        name_node = self._child_by_type(node, "name")
        if name_node is None:
            return
        mname = _node_text(name_node, src)
        line = _line(node)
        cls = class_stack[-1] if class_stack else "__global__"

        # Detect static vs instance
        kind = "method"
        for child in node.children:
            if child.type == "static":
                kind = "static"
                break

        data.methods.append((cls, mname, line, kind))

        func_stack.append(mname)
        for child in node.children:
            self._walk(child, src, data, class_stack, func_stack)
        func_stack.pop()

    def _handle_include(self, node: Any, src: bytes, data: PHPFileData) -> None:
        ntype = node.type
        kind_map = {
            "include_expression": "include",
            "include_once_expression": "include_once",
            "require_expression": "require",
            "require_once_expression": "require_once",
        }
        kind = kind_map.get(ntype, "include")

        # Find string child
        for n in _iter_tree(node):
            if n.type in ("string", "encapsed_string"):
                raw = _node_text(n, src).strip("\"'")
                # Normalise path
                raw = raw.replace("\\", "/")
                data.includes.append((kind, raw))
                break

    def _handle_function_call(self, node: Any, src: bytes, data: PHPFileData,
                              class_stack: List[str], func_stack: List[str]) -> None:
        # function_call_expression: name + arguments
        fname_node = node.children[0] if node.children else None
        if fname_node is None:
            return
        fname = _node_text(fname_node, src)
        if fname in PHP_PRIMITIVES:
            return
        line = _line(node)

        caller = self._current_qname(data, class_stack, func_stack)

        # Detect add_hook / run_hooks and extract HOOK_ argument
        if fname in ("add_hook", "run_hooks"):
            hook_const = self._extract_hook_arg(node, src)
            if hook_const:
                if fname == "add_hook":
                    data.hook_registers.append((hook_const, line))
                else:
                    data.hook_invokes.append((hook_const, line))
            return

        data.calls.append((caller, fname, line))

    def _handle_member_call(self, node: Any, src: bytes, data: PHPFileData,
                            class_stack: List[str], func_stack: List[str]) -> None:
        # object->method(...)
        # Children: object, '->', name, arguments
        method_node = None
        for child in node.children:
            if child.type == "name" and _node_text(child, src) not in ("->",):
                method_node = child
        if method_node is None:
            return
        mname = _node_text(method_node, src)
        if mname in PHP_PRIMITIVES:
            return
        line = _line(node)
        caller = self._current_qname(data, class_stack, func_stack)

        # Detect add_hook / run_hooks calls on $this or PluginHost
        if mname in ("add_hook", "run_hooks"):
            hook_const = self._extract_hook_arg(node, src)
            if hook_const:
                if mname == "add_hook":
                    data.hook_registers.append((hook_const, line))
                else:
                    data.hook_invokes.append((hook_const, line))
            return

        data.calls.append((caller, mname, line))

    def _handle_static_call(self, node: Any, src: bytes, data: PHPFileData,
                            class_stack: List[str], func_stack: List[str]) -> None:
        # Class::method(...)
        # Children: class_name, '::', name, arguments
        parts = []
        for child in node.children:
            if child.type in ("name", "variable_name"):
                parts.append(_node_text(child, src))
        if len(parts) >= 2:
            callee = "::".join(parts[-2:])
            mname = parts[-1]
            if mname not in PHP_PRIMITIVES:
                line = _line(node)
                caller = self._current_qname(data, class_stack, func_stack)

                # Detect PluginHost::getInstance()->add_hook / run_hooks pattern
                if mname in ("add_hook", "run_hooks"):
                    hook_const = self._extract_hook_arg(node, src)
                    if hook_const:
                        if mname == "add_hook":
                            data.hook_registers.append((hook_const, line))
                        else:
                            data.hook_invokes.append((hook_const, line))
                    return

                data.calls.append((caller, callee, line))

    def _extract_hook_arg(self, call_node: Any, src: bytes) -> Optional[str]:
        """Extract the first HOOK_* constant argument from a call node's arguments."""
        args_node = None
        for child in call_node.children:
            if child.type == "arguments":
                args_node = child
                break
        if args_node is None:
            return None
        for n in _iter_tree(args_node):
            text = _node_text(n, src)
            if HOOK_CONST_RE.fullmatch(text):
                return text
        return None

    def _handle_string(self, node: Any, src: bytes, data: PHPFileData) -> None:
        text = _node_text(node, src)
        self._extract_sql(text, data, _line(node))

    def _extract_sql(self, text: str, data: PHPFileData, line: int) -> None:
        for m in SQL_TABLE_RE.finditer(text):
            table = m.group(1).lower()
            if not table.startswith("ttrss_"):
                continue  # skip non-ttrss tables
            # Determine operation from surrounding context
            op_match = SQL_OP_RE.search(text[:m.start()])
            if not op_match:
                op_match = SQL_OP_RE.search(text)
            op = op_match.group(1).upper() if op_match else "SELECT"
            data.db_accesses.append((table, op, line))

    def _current_qname(self, data: PHPFileData, class_stack: List[str],
                       func_stack: List[str]) -> str:
        """Build a qualified caller name from current class and function/method scope."""
        if class_stack and func_stack:
            return f"{class_stack[-1]}::{func_stack[-1]}"
        if class_stack:
            return f"{class_stack[-1]}::__init__"
        if func_stack:
            return f"{data.path}::{func_stack[-1]}"
        return data.path

    @staticmethod
    def _child_by_type(node: Any, type_name: str) -> Optional[Any]:
        for child in node.children:
            if child.type == type_name:
                return child
        return None

    # ------------------------------------------------------------------
    # Regex fallback (when tree-sitter is unavailable)
    # ------------------------------------------------------------------

    def _regex_fallback(self, source_bytes: bytes, data: PHPFileData) -> None:
        text = source_bytes.decode("utf-8", errors="replace")
        print(f"[WARN] Using regex fallback for {data.path} — "
              "call graph edges will NOT be populated (tree-sitter required)",
              file=sys.stderr)
        # Includes
        for m in INCLUDE_RE.finditer(text):
            raw = m.group(1).replace("\\", "/")
            keyword = m.group(0).split()[0].lower()
            data.includes.append((keyword, raw))
        # SQL
        for line_no, line_text in enumerate(text.splitlines(), 1):
            self._extract_sql(line_text, data, line_no)
        # Hooks — heuristic: detect add_hook / run_hooks calls by regex
        add_hook_re = re.compile(
            r"\b(?:add_hook|run_hooks)\s*\(\s*(HOOK_[A-Z_]+)", re.IGNORECASE
        )
        for line_no, line_text in enumerate(text.splitlines(), 1):
            m = add_hook_re.search(line_text)
            if m:
                hook = m.group(1)
                if "add_hook" in line_text[:m.start() + 8]:
                    data.hook_registers.append((hook, line_no))
                else:
                    data.hook_invokes.append((hook, line_no))
            else:
                for hm in HOOK_CONST_RE.finditer(line_text):
                    data.hook_invokes.append((hm.group(0), line_no))
        # Classes
        cls_re = re.compile(
            r"class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?",
            re.IGNORECASE,
        )
        for line_no, line_text in enumerate(text.splitlines(), 1):
            cm = cls_re.search(line_text)
            if cm:
                cname = cm.group(1)
                parent = cm.group(2)
                ifaces_raw = cm.group(3) or ""
                ifaces = [i.strip() for i in ifaces_raw.split(",") if i.strip()]
                data.classes.append((cname, parent, ifaces, line_no))
        # Functions
        func_re = re.compile(r"function\s+(\w+)\s*\(", re.IGNORECASE)
        for line_no, line_text in enumerate(text.splitlines(), 1):
            fm = func_re.search(line_text)
            if fm:
                data.functions.append((fm.group(1), line_no))


# ---------------------------------------------------------------------------
# Include path resolver
# ---------------------------------------------------------------------------

class IncludeResolver:
    """Resolve PHP include paths relative to the source root."""

    def __init__(self, source_root: Path):
        self.source_root = source_root
        # Build lookup: basename → set of relative paths
        self._basename_map: Dict[str, List[str]] = defaultdict(list)
        for p in source_root.rglob("*.php"):
            rel = str(p.relative_to(source_root))
            self._basename_map[p.name].append(rel)

    def resolve(self, including_file_rel: str, include_target: str) -> Optional[str]:
        """Return relative-to-source-root path for the included file."""
        target = Path(include_target)
        # Candidates:
        # 1. Relative to including file's directory
        including_dir = Path(including_file_rel).parent
        candidate1 = including_dir / target
        # 2. Relative to source root
        candidate2 = target
        # 3. Strip leading ../ ../ traversals (PHP sets include_path to root)
        parts = list(target.parts)
        while parts and parts[0] in ("..", "."):
            parts.pop(0)
        candidate3 = Path(*parts) if parts else None

        for cand in [candidate1, candidate2, candidate3]:
            if cand is None:
                continue
            abs_cand = (self.source_root / cand).resolve()
            if abs_cand.exists():
                try:
                    return str(abs_cand.relative_to(self.source_root))
                except ValueError:
                    pass

        return None


# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------

class GraphBuilder:
    """Build the five dimension graphs from a collection of PHPFileData."""

    def __init__(self, source_root: Path):
        self.source_root = source_root
        self._resolver = IncludeResolver(source_root)

    def build_include_graph(self, files: List[PHPFileData]) -> "nx.DiGraph":
        G = nx.DiGraph(name="include")
        for fd in files:
            G.add_node(fd.path, loc=fd.loc, label=_short_label(fd.path))
            for kind, target in fd.includes:
                resolved = self._resolver.resolve(fd.path, target)
                if resolved and resolved != fd.path:
                    G.add_edge(fd.path, resolved, kind=kind)
        return G

    def build_call_graph(self, files: List[PHPFileData]) -> "nx.DiGraph":
        G = nx.DiGraph(name="call")

        # Index all defined callables and build a bare-name → qualified-name lookup
        defined: Set[str] = set()
        bare_to_qname: Dict[str, str] = {}  # bare_name → qualified_name (last wins)

        for fd in files:
            for fname, line in fd.functions:
                qname = f"{fd.path}::{fname}"
                G.add_node(qname, file=fd.path, line=line, kind="function",
                           label=fname)
                defined.add(qname)
                defined.add(fname)
                bare_to_qname[fname] = qname
            for cls, meth, line, kind in fd.methods:
                qname = f"{cls}::{meth}"
                G.add_node(qname, file=fd.path, line=line, kind=kind,
                           label=f"{cls}.{meth}")
                defined.add(qname)
                defined.add(meth)
                bare_to_qname[meth] = qname

        # Add edges
        for fd in files:
            for caller, callee, line in fd.calls:
                if callee in PHP_PRIMITIVES:
                    continue
                # Resolve callee to a defined node
                callee_node = self._resolve_callee(callee, defined,
                                                   bare_to_qname, G)
                if callee_node and callee_node != caller:
                    if caller not in G.nodes:
                        G.add_node(caller, file=fd.path, line=line,
                                   kind="context", label=_short_label(caller))
                    G.add_edge(caller, callee_node, line=line)
        return G

    def build_db_table_graph(self, files: List[PHPFileData]) -> "nx.DiGraph":
        G = nx.DiGraph(name="db_table")

        # Collect all tables encountered during parsing
        all_tables: Set[str] = set()
        for fd in files:
            for table, op, line in fd.db_accesses:
                all_tables.add(table)
        for t in all_tables:
            G.add_node(t, label=t.replace("ttrss_", ""), kind="table")

        # Add file→table edges
        for fd in files:
            if not fd.db_accesses:
                continue
            G.add_node(fd.path, loc=fd.loc, label=_short_label(fd.path),
                       kind="file")
            for table, op, line in fd.db_accesses:
                if G.has_edge(fd.path, table):
                    # Merge ops
                    existing = G[fd.path][table].get("kind", "")
                    if op not in existing:
                        G[fd.path][table]["kind"] = existing + "," + op
                else:
                    G.add_edge(fd.path, table, kind=op, line=line)
        return G

    def build_class_graph(self, files: List[PHPFileData]) -> "nx.DiGraph":
        G = nx.DiGraph(name="class")
        for fd in files:
            for cname, parent, interfaces, line in fd.classes:
                G.add_node(cname, file=fd.path, line=line, label=cname,
                           kind="class")
                if parent:
                    G.add_node(parent, label=parent, kind="class")
                    G.add_edge(cname, parent, kind="extends")
                for iface in interfaces:
                    G.add_node(iface, label=iface, kind="interface")
                    G.add_edge(cname, iface, kind="implements")
        return G

    def build_hook_graph(self, files: List[PHPFileData]) -> "nx.DiGraph":
        G = nx.DiGraph(name="hook")

        # Collect all known hook constants from parsed data (no out-of-band read)
        all_hooks: Set[str] = set()
        for fd in files:
            for hook, _ in fd.hook_registers:
                all_hooks.add(hook)
            for hook, _ in fd.hook_invokes:
                all_hooks.add(hook)

        for h in all_hooks:
            G.add_node(h, label=h.replace("HOOK_", ""), kind="hook")

        for fd in files:
            for hook, line in fd.hook_registers:
                G.add_node(hook, label=hook.replace("HOOK_", ""), kind="hook")
                G.add_node(fd.path, loc=fd.loc, label=_short_label(fd.path), kind="file")
                G.add_edge(fd.path, hook, kind="REGISTERS", line=line)

            for hook, line in fd.hook_invokes:
                G.add_node(hook, label=hook.replace("HOOK_", ""), kind="hook")
                G.add_node(fd.path, loc=fd.loc, label=_short_label(fd.path), kind="file")
                G.add_edge(fd.path, hook, kind="INVOKES", line=line)

        return G

    @staticmethod
    def _resolve_callee(callee: str, defined: Set[str],
                        bare_to_qname: Dict[str, str],
                        G: "nx.DiGraph") -> Optional[str]:
        if callee in G.nodes:
            return callee
        if "::" in callee and callee in defined:
            return callee
        # bare name lookup via pre-built dict (O(1))
        bare = callee.split("::")[-1]
        if bare in bare_to_qname:
            return bare_to_qname[bare]
        return None


# ---------------------------------------------------------------------------
# Community Detection
# ---------------------------------------------------------------------------

class CommunityDetector:
    """Run Leiden (or Louvain fallback) community detection on a NetworkX graph."""

    def __init__(self, resolution: float = 1.0):
        self.resolution = resolution

    def detect(self, G: "nx.DiGraph") -> Dict[str, int]:
        """Return {node: community_id} mapping."""
        if G.number_of_nodes() == 0:
            return {}
        UG = G.to_undirected()
        # Remove self-loops
        UG.remove_edges_from(list(nx.selfloop_edges(UG)))

        if HAS_LEIDEN:
            return self._leiden(UG)
        else:
            return self._louvain_nx(UG)

    def _leiden(self, UG: "nx.Graph") -> Dict[str, int]:
        nodes = list(UG.nodes())
        node_idx = {n: i for i, n in enumerate(nodes)}
        edges = [(node_idx[u], node_idx[v]) for u, v in UG.edges()]

        ig_graph = ig.Graph(n=len(nodes), edges=edges, directed=False)
        # Use RBConfigurationVertexPartition to support resolution_parameter
        partition = leidenalg.find_partition(
            ig_graph,
            leidenalg.RBConfigurationVertexPartition,
            n_iterations=-1,
            seed=42,
            resolution_parameter=self.resolution,
        )
        return {nodes[i]: cid for cid, members in enumerate(partition)
                for i in members}

    def _louvain_nx(self, UG: "nx.Graph") -> Dict[str, int]:
        communities = nx.community.greedy_modularity_communities(UG)
        result = {}
        for cid, members in enumerate(communities):
            for node in members:
                result[node] = cid
        return result

    def compute_levels(self, G: "nx.DiGraph") -> Dict[int, List[str]]:
        """
        Topological dependency levels via SCC condensation.
        Level 0 = no dependencies (sink SCCs — out-degree 0 in condensed graph).
        Higher levels depend on lower levels.
        Returns {level: [nodes]}.
        """
        if G.number_of_nodes() == 0:
            return {}
        try:
            condensed = nx.condensation(G)
        except Exception:
            return {0: list(G.nodes())}

        # BFS from sinks (out-degree 0 in condensed graph = nodes with no
        # outgoing dependencies = Level 0 / leaf nodes).
        topo_level: Dict[int, int] = {}  # scc_id → level
        out_deg = dict(condensed.out_degree())
        queue = deque(n for n in condensed.nodes() if out_deg[n] == 0)
        for n in queue:
            topo_level[n] = 0

        # Walk backwards (predecessors) to assign increasing levels
        while queue:
            current = queue.popleft()
            for pred in condensed.predecessors(current):
                new_level = topo_level[current] + 1
                if topo_level.get(pred, -1) < new_level:
                    topo_level[pred] = new_level
                    queue.append(pred)

        # Map SCC back to original nodes using correct NetworkX API
        levels: Dict[int, List[str]] = defaultdict(list)
        for scc_id in condensed.nodes():
            level = topo_level.get(scc_id, 0)
            members = condensed.nodes[scc_id].get("members", set())
            levels[level].extend(str(m) for m in members)

        return dict(levels)


# ---------------------------------------------------------------------------
# Reporter / Serialiser
# ---------------------------------------------------------------------------

class Reporter:
    """Serialise graphs + community results to JSON and text."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_graph(self, G: "nx.DiGraph", communities: Dict[str, int],
                   levels: Dict[int, List[str]], dim_name: str) -> dict:
        # Nodes
        nodes_out: Dict[str, dict] = {}
        for node, attrs in G.nodes(data=True):
            nodes_out[str(node)] = {k: v for k, v in attrs.items()
                                    if v is not None}

        # Edges
        edges_out = []
        for u, v, attrs in G.edges(data=True):
            edge = {"from": str(u), "to": str(v)}
            edge.update({k: v for k, v in attrs.items() if v is not None})
            edges_out.append(edge)

        # Community members
        comm_members: Dict[str, List[str]] = defaultdict(list)
        for node, cid in communities.items():
            comm_members[str(cid)].append(str(node))

        payload = {
            "graph_type": dim_name,
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "community_count": len(comm_members),
            "nodes": nodes_out,
            "edges": edges_out,
            "communities": {str(k): v for k, v in communities.items()},
            "levels": {str(k): v for k, v in sorted(levels.items())},
            "community_members": dict(comm_members),
        }

        out_path = self.output_dir / f"{dim_name}_graph.json"
        out_path.write_text(json.dumps(payload, indent=2, default=str))
        print(f"  [OK] {out_path} ({G.number_of_nodes()} nodes, "
              f"{G.number_of_edges()} edges, "
              f"{len(comm_members)} communities)")
        return payload

    def save_summary(self, all_results: Dict[str, dict]) -> None:
        summary: Dict[str, Any] = {}
        for dim, data in all_results.items():
            summary[dim] = {
                "node_count": data["node_count"],
                "edge_count": data["edge_count"],
                "community_count": data["community_count"],
                "communities": {
                    cid: members
                    for cid, members in data["community_members"].items()
                },
            }
        out = self.output_dir / "communities_summary.json"
        out.write_text(json.dumps(summary, indent=2, default=str))
        print(f"  [OK] {out}")

    def save_report(self, all_results: Dict[str, dict]) -> None:
        lines = ["TT-RSS PHP Dependency Graph Analysis Report",
                 "=" * 60, ""]
        for dim, data in all_results.items():
            lines.append(f"DIMENSION: {dim.upper()}")
            lines.append(f"  Nodes: {data['node_count']}  "
                         f"Edges: {data['edge_count']}  "
                         f"Communities: {data['community_count']}")
            lines.append("")

            # Community members
            lines.append("  Communities:")
            for cid, members in sorted(data["community_members"].items(),
                                       key=lambda x: -len(x[1])):
                lines.append(f"    [{cid}] ({len(members)} members): "
                             + ", ".join(sorted(members)[:10])
                             + (" ..." if len(members) > 10 else ""))
            lines.append("")

            # Levels
            lines.append("  Dependency Levels (0=leaf, higher=depends on lower):")
            for lvl, members in sorted(data["levels"].items(),
                                       key=lambda x: int(x[0])):
                lines.append(f"    Level {lvl} ({len(members)} nodes): "
                             + ", ".join(sorted(members)[:8])
                             + (" ..." if len(members) > 8 else ""))
            lines.append("")
            lines.append("-" * 60)
            lines.append("")

        out = self.output_dir / "report.txt"
        out.write_text("\n".join(lines))
        print(f"  [OK] {out}")


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _short_label(path: str) -> str:
    """Return a short human-readable label for a file path."""
    p = Path(path)
    parts = p.parts
    if len(parts) <= 2:
        return p.stem
    return "/".join([parts[-2], p.stem])


def collect_php_files(source_root: Path) -> List[Path]:
    """Recursively collect all .php files under source_root."""
    return sorted(source_root.rglob("*.php"))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build PHP dependency dimension graphs for TT-RSS migration analysis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--source",
        default="source-repos/ttrss-php/ttrss",
        help="Path to TT-RSS PHP source root (default: source-repos/ttrss-php/ttrss)",
    )
    parser.add_argument(
        "--output",
        default="tools/graph_analysis/output",
        help="Output directory for JSON + report files",
    )
    parser.add_argument(
        "--dims",
        default="include,call,db_table,class,hook",
        help="Comma-separated list of dimensions to build "
             "(include, call, db_table, class, hook)",
    )
    parser.add_argument(
        "--resolution",
        type=float,
        default=1.0,
        help="Leiden resolution parameter (default: 1.0)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print per-file progress",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not HAS_NX:
        print("[ERROR] networkx is required. Install with: pip install networkx",
              file=sys.stderr)
        sys.exit(1)

    source_root = Path(args.source).resolve()
    output_dir = Path(args.output).resolve()

    if not source_root.exists():
        print(f"[ERROR] Source root does not exist: {source_root}", file=sys.stderr)
        sys.exit(1)

    dims_requested = {d.strip() for d in args.dims.split(",")}
    valid_dims = {"include", "call", "db_table", "class", "hook"}
    unknown = dims_requested - valid_dims
    if unknown:
        print(f"[ERROR] Unknown dimensions: {unknown}. Valid: {valid_dims}",
              file=sys.stderr)
        sys.exit(1)

    print(f"Source root : {source_root}")
    print(f"Output dir  : {output_dir}")
    print(f"Dimensions  : {sorted(dims_requested)}")
    print(f"tree-sitter : {'available' if HAS_TREESITTER else 'UNAVAILABLE (regex fallback)'}")
    print(f"Leiden      : {'available' if HAS_LEIDEN else 'UNAVAILABLE (Louvain fallback)'}")
    print()

    # 1. Collect PHP files
    php_files = collect_php_files(source_root)
    print(f"Found {len(php_files)} PHP files — parsing...")

    # 2. Parse all files
    file_parser = PHPFileParser(source_root)
    all_file_data: List[PHPFileData] = []
    for i, fpath in enumerate(php_files, 1):
        if args.verbose:
            print(f"  [{i}/{len(php_files)}] {fpath.relative_to(source_root)}")
        fd = file_parser.parse_file(fpath)
        all_file_data.append(fd)

    print(f"Parsed {len(all_file_data)} files.\n")

    # 3. Build graphs + detect communities
    builder = GraphBuilder(source_root)
    detector = CommunityDetector(resolution=args.resolution)
    reporter = Reporter(output_dir)

    dim_builders = {
        "include":  builder.build_include_graph,
        "call":     builder.build_call_graph,
        "db_table": builder.build_db_table_graph,
        "class":    builder.build_class_graph,
        "hook":     builder.build_hook_graph,
    }

    all_results: Dict[str, dict] = {}

    for dim in sorted(dims_requested):
        print(f"Building [{dim}] graph...")
        G = dim_builders[dim](all_file_data)
        print(f"  {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

        print(f"  Running community detection...")
        communities = detector.detect(G)

        print(f"  Computing dependency levels...")
        levels = detector.compute_levels(G)

        result = reporter.save_graph(G, communities, levels, dim)
        all_results[dim] = result
        print()

    # 4. Write summary + report
    print("Writing summary + report...")
    reporter.save_summary(all_results)
    reporter.save_report(all_results)

    print("\nDone.")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
