#!/usr/bin/env python3
"""strict_function_audit.py — Strict PHP→Python coverage audit via tree-sitter.

Differences from exact_function_audit.py:
  1.  Parses PHP source DIRECTLY with tree-sitter — not from pre-built call_graph.json.
      Every PHP function/method gets its exact START and END line from the AST,
      not from "next function's start" approximation.
  2.  Enhanced Source-comment parser that handles ALL real-world formats found in
      the codebase:
        # Source: file.php:ClassName::method        (standard)
        # Source: file.php:func1 / func2            (slash-separated aliases)
        # Source: file.php:123-456 — funcname       (line-range + em-dash name)
        # Source: file.php:123 — funcname           (single-line + em-dash name)
        Source: file.php (func1/func2, lines X-Y)  (parenthetical in docstring)
        + ClassName::func (lines X-Y)              (addendum continuation line)
  3.  File-specific matching ONLY — no global bare-name fallback.
      A function named "edit" in pref/labels.php can only be matched by a comment
      that explicitly references pref/labels.php, not any Source comment that
      anywhere names "edit".
  4.  When Python cites a line range for a PHP file, the audit checks whether
      that range overlaps the function's EXACT boundary from tree-sitter, and
      reports discrepancies (cited range extends beyond function end, etc.).

Usage:
    python tools/graph_analysis/strict_function_audit.py \\
        --php-dir  source-repos/ttrss-php/ttrss \\
        --python-dir target-repos/ttrss-python/ttrss \\
        [--levels-json tools/graph_analysis/output/function_levels.json] \\
        [--max-level 10]

Output:
    tools/graph_analysis/output/strict_audit.txt
    tools/graph_analysis/output/strict_audit.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# tree-sitter
# ---------------------------------------------------------------------------
try:
    import tree_sitter_php as tsPHP
    from tree_sitter import Language, Parser as TsParser
    _PHP_LANGUAGE = Language(tsPHP.language_php())
    _TS_AVAILABLE = True
except Exception as _e:
    _TS_AVAILABLE = False
    print(f"[FATAL] tree-sitter-php unavailable: {_e}", file=sys.stderr)
    print("        pip install tree-sitter tree-sitter-php", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Elimination lists (kept in sync with exact_function_audit.py)
# ---------------------------------------------------------------------------
THIRD_PARTY_PREFIXES: Set[str] = {
    "QRcode", "QR", "PHPMailer", "SMTP", "SphinxClient",
    "gettext_reader", "FileReader", "Text_LanguageDetect",
    "MiniTemplator", "Mobile_Detect", "floIcon", "jimIcon",
    "HOTP", "OTP", "TOTP", "Minifier", "FrameFiller",
    "Db_Mysql", "Db_Mysqli", "Publisher", "Subscriber", "Base32",
    "CachedFileReader", "StringReader", "StreamReader",
    "QRrs", "QRmask", "QRencode", "QRsplit", "QRrawcode",
    "QRimage", "qrstr", "QRspec", "phpmailerException", "Db_Pgsql",
    "ttrss/lib/",
    "ttrss/update_daemon2.php", "ttrss/update.php",
    "FeedParser", "FeedItem", "FeedItem_Atom", "FeedItem_RSS",
    "FeedItem_Common", "FeedEnclosure",
    "LanguageDetect",
    "ttrss/include/colors.php",
}

ELIMINATED_BARE: Set[str] = {
    # PHP UI helpers replaced by Jinja2 templates
    "print_select", "print_select_hash", "print_radio",
    "print_feed_cat_select", "print_feed_select", "print_label_select",
    "render_login_form", "print_checkpoint", "print_error",
    "print_warning", "print_notice",
    "stylesheet_tag", "javascript_tag", "get_minified_js",
    "T_js_decl", "T_sprintf",
    "implements_interface", "check_for_update", "startup_gettext",
    "init_js_translations",
    "print_user_stylesheet", "calculate_dep_timestamp", "get_score_pic",
    "format_warning", "format_notice", "format_error",
    # PHP-only runtime helpers
    "stripslashes_deep", "gzdecode", "trim_array",
    "file_is_locked", "make_lockfile", "make_stampfile",
    "sql_random_function", "db_escape_string", "get_pgsql_version",
    "sql_bool_to_bool", "bool_to_sql_bool", "checkbox_to_sql_bool",
    "define_default", "truncate_string", "get_random_bytes",
    "_debug", "_debug_suppress",
    # DB adapters — SQLAlchemy replaces
    "escape_string", "query", "fetch_assoc", "num_rows", "fetch_result",
    "close", "affected_rows", "last_error", "reconnect",
    # PHP session callbacks
    "session_read", "session_write", "session_destroy",
    "ttrss_open", "ttrss_close",
    # PHP magic methods
    "__autoload", "__construct", "__clone", "__destruct",
    # PHP image/color processing
    "_color_pack", "_color_unpack", "_resolve_htmlcolor",
    "calculate_avg_color", "colorPalette", "hsl2rgb",
    "_color_hsl2rgb", "_color_hue2rgb", "_color_rgb2hsl",
    # DbUpdater → Alembic
    "getSchemaLines", "getSchemaVersion", "isUpdateRequired", "performUpdateTo",
    # Db_Stmt → SQLAlchemy Result
    "fetch", "rowCount",
    # Logger → structlog
    "log_error", "log", "get",
    # Handler base → Flask blueprints
    "after", "csrf_ignore",
    # PluginHandler → Flask routing
    "catchall",
    # Plugin base → pluggy hookimpl
    "about", "api_version", "get_js", "get_prefs_js",
    # Auth_Base → auth module
    "find_user_by_login", "auto_create_user",
    # PHP bootstrap → Flask factory
    "connect",
    # PHP error handlers → Flask/structlog
    "ttrss_error_handler", "ttrss_fatal_handler",
    # sanity_check → Docker healthcheck
    "make_self_url_path", "initial_sanity_check",
    # Email → utils/mail.py wraps directly
    "quickMail",
    # Plugin init → hookimpl
    "init",
    # Install wizard
    "index",
    # Sphinx search
    "sphinx_search",
    # Format helpers (Jinja2 replaces)
    "format_tags_string", "format_article_labels", "format_article_note",
    "format_inline_player", "get_score_pic",
    # PHP-only string utilities
    "read_stdin", "tmpdirname",
    # URL helpers inlined in Python
    "get_self_url_prefix", "build_url", "fix_url",
    # PHP-only encryption wrapper
    "encrypt_password",
    # PHP-only feed icon helper
    "feed_has_icon",
    # PHP legacy plugin init
    "init_plugins",
    # PHP-only gettext helpers
    "get_translations",
    # SSL cert
    "get_ssl_certificate_id",
    # DB quote — SQLAlchemy handles parameterisation
    "quote",
    # backend.php entry-point helpers
    "loading", "display_main_help", "help",
    # Dlg HTML generators
    "before", "pubOPMLUrl", "explainError", "printTagCloud", "printTagSelect",
    "generatedFeed", "newVersion",
    # Backend.digestTest → tasks/digest.py::send_digest_test
    "digestTest",
    # opml entry points
    "opml_notice",
    # Feeds HTML generators — Jinja2
    "format_headline_subtoolbar", "format_headlines_list", "catchupAll",
    "generate_dashboard_feed", "generate_error_feed", "quickAddFeed",
    "feedBrowser", "search",
    # Article HTML generators
    "redirect", "view", "setScore",
    # RPC frontend helpers
    "setpanelmode", "updaterandomfeed", "getlinktitlebyid",
    # Tag validation
    "tag_is_valid", "sanitize_tag",
    # URL probers
    "is_html", "url_is_html", "validate_feed_url",
    # PHP libxml error formatter
    "format_libxml_error",
    # save_email_address
    "save_email_address",
    # Pref_Prefs helpers
    "getShortDesc", "getHelpText", "getSectionName",
    # HTML dialog generators
    "editfeeds", "batch_edit_cbox",
    "newrule", "newaction",
    "customizeCSS", "toggleAdvanced", "getHelp",
    # PHP-specific accessors
    "get_dbh", "run_hooks", "load_all",
    # Session callbacks
    "ttrss_read", "ttrss_write", "ttrss_destroy", "ttrss_gc",
    "session_get_schema_version",
    # URL/utility helpers
    "make_password", "validate_csrf", "sanity_check",
    "getFeedIcon", "geturl", "convertUrlQuery",
    "expire_lock_files", "cache_images",
    "add_feed_url",
    # Entry-point pseudo-functions
    "housekeepingTask",
    # PHP HTML helpers
    "printRuleName", "printActionName",
    # Top-level script bodies (PHP includes, not real functions — qname = file path)
    "ttrss/include/functions.php",
    "ttrss/include/rssfuncs.php",
}

# PHP files where every function is intentionally eliminated/replaced
ELIMINATED_FILES: Set[str] = {
    "ttrss/include/login_form.php",
    "ttrss/include/sanity_check.php",
    "ttrss/include/sanity_config.php",
    "ttrss/include/version.php",
    "ttrss/include/autoload.php",
    "ttrss/include/errorhandler.php",
    "ttrss/include/db.php",
    "ttrss/classes/idb.php",
    "ttrss/classes/db/pgsql.php",
    "ttrss/classes/db/mysql.php",
    "ttrss/classes/db/mysqli.php",
    "ttrss/classes/db/pdo.php",
    "ttrss/classes/db/stmt.php",
    "ttrss/classes/ihandler.php",
    "ttrss/classes/iauthmodule.php",
    "ttrss/classes/handler.php",
    "ttrss/classes/handler/protected.php",
    "ttrss/classes/plugin.php",
    "ttrss/classes/pluginhandler.php",
    "ttrss/classes/feedparser.php",
    "ttrss/classes/feeditem.php",
    "ttrss/classes/feeditem/common.php",
    "ttrss/classes/feeditem/atom.php",
    "ttrss/classes/feeditem/rss.php",
    "ttrss/classes/feedenclosure.php",
    "ttrss/classes/auth/base.php",
    "ttrss/classes/logger.php",
    "ttrss/classes/logger/sql.php",
    "ttrss/classes/logger/syslog.php",
    "ttrss/classes/dbupdater.php",
    "ttrss/classes/db/prefs.php",
    "ttrss/install/index.php",
    "ttrss/errors.php",
    "ttrss/opml.php",
    "ttrss/api/index.php",
    "ttrss/public.php",
    "ttrss/register.php",
    # image.php — script body only, no function definitions
    "ttrss/image.php",
}


# ---------------------------------------------------------------------------
# PHP AST extraction — exact start + end lines
# ---------------------------------------------------------------------------

@dataclass
class PHPFunc:
    qname: str
    file: str          # relative to source root, e.g. "ttrss/classes/api.php"
    start_line: int    # 1-based, from tree-sitter start_point
    end_line: int      # 1-based, from tree-sitter end_point (exact)
    bare: str = field(init=False)

    def __post_init__(self) -> None:
        self.bare = self.qname.rsplit("::", 1)[1] if "::" in self.qname else self.qname


def _node_text(node, src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _child_by_type(node, type_name: str):
    for child in node.children:
        if child.type == type_name:
            return child
    return None


def extract_php_functions(php_file: Path, source_root: Path) -> List[PHPFunc]:
    """Parse a PHP file with tree-sitter and return all function/method definitions
    with exact start and end line numbers."""
    rel = str(php_file.relative_to(source_root))
    src = php_file.read_bytes()
    parser = TsParser(_PHP_LANGUAGE)
    try:
        tree = parser.parse(src)
    except Exception as exc:
        print(f"[WARN] tree-sitter parse error in {rel}: {exc}", file=sys.stderr)
        return []

    results: List[PHPFunc] = []
    _walk_ast(tree.root_node, src, rel, results, class_stack=[])
    return results


def _walk_ast(node, src: bytes, rel_file: str, out: List[PHPFunc],
              class_stack: List[str]) -> None:
    ntype = node.type

    if ntype == "class_declaration":
        name_node = _child_by_type(node, "name")
        if name_node:
            cls = _node_text(name_node, src)
            class_stack.append(cls)
            body = _child_by_type(node, "declaration_list")
            if body:
                for child in body.children:
                    _walk_ast(child, src, rel_file, out, class_stack)
            class_stack.pop()
        return

    if ntype in ("function_definition", "function_declaration"):
        name_node = _child_by_type(node, "name")
        if name_node:
            fname = _node_text(name_node, src)
            if class_stack:
                qname = f"{class_stack[-1]}::{fname}"
            else:
                qname = f"{rel_file}::{fname}"
            start = node.start_point[0] + 1
            end = node.end_point[0] + 1
            out.append(PHPFunc(qname=qname, file=rel_file, start_line=start, end_line=end))
        # recurse into function body for nested closures (uncommon in TT-RSS)
        for child in node.children:
            _walk_ast(child, src, rel_file, out, class_stack)
        return

    if ntype == "method_declaration":
        name_node = _child_by_type(node, "name")
        if name_node:
            mname = _node_text(name_node, src)
            cls = class_stack[-1] if class_stack else "__global__"
            qname = f"{cls}::{mname}"
            start = node.start_point[0] + 1
            end = node.end_point[0] + 1
            out.append(PHPFunc(qname=qname, file=rel_file, start_line=start, end_line=end))
        return

    for child in node.children:
        _walk_ast(child, src, rel_file, out, class_stack)


# ---------------------------------------------------------------------------
# Python Source-comment parsing — enhanced
# ---------------------------------------------------------------------------

# Primary Source: line pattern (also matches Eliminated: lines)
_TREF_PATTERN = re.compile(
    r"(?:#\s*)?(?:Source|Inferred from|Adapted from|Migrated from|Based on|PHP source|Eliminated):\s*"
    r"(?P<path>(?:ttrss/)?[\w./-]+\.php)"
    r"(?::(?P<rest>[^\n]+))?",
    re.IGNORECASE,
)

# Addendum line: "+  ClassName::method (lines X-Y)" following a Source: line
_ADDENDUM_PATTERN = re.compile(
    r"\+\s+"
    r"(?:(?P<cls>[A-Za-z_]\w*)(?:::|\.))?"
    r"(?P<fn>[A-Za-z_]\w*)"
    r"(?:\s+\(?lines?\s*(?P<start>\d+)\s*[-–]\s*(?P<end>\d+)\)?)?"
)

# Parenthetical function list: "file.php (func1/func2, lines X-Y)"
_PAREN_FUNCS_PATTERN = re.compile(
    r"(?P<path>(?:ttrss/)?[\w./-]+\.php)\s*\("
    r"(?P<names>[A-Za-z_][\w/]*)"
    r"(?:,\s*lines?\s*(?P<start>\d+)\s*[-–]\s*(?P<end>\d+))?"
    r"\)",
    re.IGNORECASE,
)

# Function name after em-dash or pipe: "123 — funcname" or "123 | funcname"
_EMDASH_NAME_RE = re.compile(
    r"(?:[-–—]|[|])\s*(?P<fn>[A-Za-z_]\w*)"
)

# Method/function name at start of rest-part
_METHOD_RE = re.compile(
    r"^(?:(?P<cls>[A-Za-z_]\w*)(?:::|\.))?"
    r"(?P<fn>[A-Za-z_]\w*)"
    r"(?:\s|$|\()"
)

# Slash-separated aliases in rest part: "func1 (line X) / func2 (line Y)"
_SLASH_SPLIT_RE = re.compile(r"\s*/\s*")

# Line number(s)
_LINE_RE = re.compile(r"^(?:lines?\s*)?(\d+)(?:\s*[-–]\s*(\d+))?")


@dataclass
class TraceRef:
    php_file: str
    fn_names: Set[str]                  # bare lowercase names from this file
    line_ranges: List[Tuple[int, int]]  # (start, end) inclusive, from Source comment


def _resolve_path(raw: str, short_to_full: Dict[str, str]) -> str:
    if raw.startswith("ttrss/"):
        return raw
    return short_to_full.get(raw, raw)


def _parse_rest(rest: str) -> Tuple[Set[str], List[Tuple[int, int]]]:
    """Parse the part after 'file.php:' and extract function names and line ranges."""
    fn_names: Set[str] = set()
    line_ranges: List[Tuple[int, int]] = []

    if not rest:
        return fn_names, line_ranges

    # Split on slashes to get multiple aliases: "func1 (line X) / func2 (line Y)"
    segments = _SLASH_SPLIT_RE.split(rest)
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue

        # Check for line number first (digit start)
        lm = _LINE_RE.match(seg.lstrip("([ "))
        if lm and seg.lstrip("([ ")[0].isdigit():
            start = int(lm.group(1))
            end = int(lm.group(2)) if lm.group(2) else start
            line_ranges.append((start, end))
            # Also look for a name after em-dash/pipe following line number
            emdash_m = _EMDASH_NAME_RE.search(seg)
            if emdash_m:
                fn_names.add(emdash_m.group("fn").lower())
        else:
            # Try function/method name
            mm = _METHOD_RE.match(seg)
            if mm:
                fn = mm.group("fn")
                fn_names.add(fn.lower())
                if mm.group("cls"):
                    fn_names.add((mm.group("cls") + "::" + fn).lower())
            # Also look for em-dash name after initial part
            emdash_m = _EMDASH_NAME_RE.search(seg)
            if emdash_m:
                fn_names.add(emdash_m.group("fn").lower())
            # Also look for line ranges within this segment
            for lmatch in re.finditer(r"\b(?:lines?\s+)?(\d+)\s*[-–]\s*(\d+)\b", seg):
                line_ranges.append((int(lmatch.group(1)), int(lmatch.group(2))))
            for lmatch in re.finditer(r"\bline\s+(\d+)\b", seg, re.IGNORECASE):
                n = int(lmatch.group(1))
                line_ranges.append((n, n))

    return fn_names, line_ranges


def scan_python_file(
    py_path: Path,
    short_to_full: Dict[str, str],
) -> List[TraceRef]:
    """Extract all traceability references from a Python file (enhanced parser)."""
    try:
        text = py_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = text.splitlines()
    refs: List[TraceRef] = []
    prev_was_source = False  # track for addendum lines

    for i, line in enumerate(lines):
        stripped = line.strip()

        # --- Primary Source: line ---
        source_hit = any(kw in stripped for kw in (
            "Source:", "Inferred", "Adapted from", "Migrated from",
            "Based on", "PHP source:", "Eliminated:",
        ))

        if source_hit:
            # Try primary pattern
            for m in _TREF_PATTERN.finditer(stripped):
                raw_path = m.group("path").strip()
                php_file = _resolve_path(raw_path, short_to_full)
                rest = (m.group("rest") or "").strip()
                fn_names, line_ranges = _parse_rest(rest)
                refs.append(TraceRef(php_file=php_file, fn_names=fn_names,
                                     line_ranges=line_ranges))
            prev_was_source = True

            # Also try parenthetical pattern (docstring module-level)
            for pm in _PAREN_FUNCS_PATTERN.finditer(stripped):
                raw_path = pm.group("path")
                php_file = _resolve_path(raw_path, short_to_full)
                names_raw = pm.group("names")
                fn_names: Set[str] = set()
                for n in re.split(r"[/,]", names_raw):
                    n = n.strip()
                    if n and re.match(r"^[A-Za-z_]\w*$", n):
                        fn_names.add(n.lower())
                line_ranges: List[Tuple[int, int]] = []
                if pm.group("start") and pm.group("end"):
                    line_ranges.append((int(pm.group("start")), int(pm.group("end"))))
                if fn_names or line_ranges:
                    refs.append(TraceRef(php_file=php_file, fn_names=fn_names,
                                         line_ranges=line_ranges))

        elif prev_was_source:
            # Look for addendum "+  ClassName::method" continuation lines
            am = _ADDENDUM_PATTERN.search(stripped)
            if am:
                fn = am.group("fn")
                cls = am.group("cls")
                # Find the most recent Source ref's php_file
                if refs:
                    php_file = refs[-1].php_file
                    refs[-1].fn_names.add(fn.lower())
                    if cls:
                        refs[-1].fn_names.add((cls + "::" + fn).lower())
                    if am.group("start") and am.group("end"):
                        refs[-1].line_ranges.append(
                            (int(am.group("start")), int(am.group("end")))
                        )
            else:
                prev_was_source = False
        else:
            prev_was_source = False

        # Also try parenthetical for any line (module docstrings, non-Source lines)
        if not source_hit:
            for pm in _PAREN_FUNCS_PATTERN.finditer(stripped):
                raw_path = pm.group("path")
                if not raw_path:
                    continue
                php_file = _resolve_path(raw_path, short_to_full)
                names_raw = pm.group("names") or ""
                fn_names2: Set[str] = set()
                for n in re.split(r"[/,]", names_raw):
                    n = n.strip()
                    if n and re.match(r"^[A-Za-z_]\w*$", n):
                        fn_names2.add(n.lower())
                line_ranges2: List[Tuple[int, int]] = []
                if pm.group("start") and pm.group("end"):
                    line_ranges2.append((int(pm.group("start")), int(pm.group("end"))))
                if fn_names2 or line_ranges2:
                    refs.append(TraceRef(php_file=php_file, fn_names=fn_names2,
                                         line_ranges=line_ranges2))

    return refs


def collect_all_refs(
    python_dir: Path,
    short_to_full: Dict[str, str],
) -> Tuple[Dict[str, Set[str]], Dict[str, List[Tuple[int, int]]], Set[str]]:
    """Collect all Python traceability refs.

    Returns:
        explicit_names[php_file] = set of lowercase bare/qualified fn names
        line_refs[php_file]      = list of (start, end) line ranges cited
        file_mentioned           = set of php_files mentioned at all
    """
    explicit_names: Dict[str, Set[str]] = defaultdict(set)
    line_refs: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    file_mentioned: Set[str] = set()

    for py_file in sorted(python_dir.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        for ref in scan_python_file(py_file, short_to_full):
            file_mentioned.add(ref.php_file)
            explicit_names[ref.php_file].update(ref.fn_names)
            line_refs[ref.php_file].extend(ref.line_ranges)

    return explicit_names, line_refs, file_mentioned


# ---------------------------------------------------------------------------
# Main audit
# ---------------------------------------------------------------------------

def _is_third_party(file_path: str, qname: str) -> bool:
    for prefix in THIRD_PARTY_PREFIXES:
        if file_path.startswith(prefix) or qname.startswith(prefix):
            return True
        if "/" in prefix:
            norm = prefix if prefix.endswith("/") else prefix + "/"
            if file_path.startswith(norm):
                return True
    return False


def run_audit(php_dir: Path, python_dir: Path,
              levels_json: Optional[Path], max_level: int) -> None:
    # -----------------------------------------------------------------------
    # 1. Extract all PHP functions via tree-sitter (exact start+end lines)
    # -----------------------------------------------------------------------
    php_functions: List[PHPFunc] = []
    php_files_found: Set[str] = set()

    for php_file in sorted(php_dir.rglob("*.php")):
        rel = str(php_file.relative_to(php_dir.parent))  # e.g. "ttrss/classes/api.php"
        if "/lib/" in rel:
            continue  # skip third-party lib/
        php_files_found.add(rel)
        fns = extract_php_functions(php_file, php_dir.parent)
        php_functions.extend(fns)

    print(f"[INFO] PHP files scanned: {len(php_files_found)}", file=sys.stderr)
    print(f"[INFO] PHP functions found (raw): {len(php_functions)}", file=sys.stderr)

    # -----------------------------------------------------------------------
    # 2. Load optional function levels (for level filter)
    # -----------------------------------------------------------------------
    func_levels: Dict[str, int] = {}
    if levels_json and levels_json.exists():
        func_levels = json.loads(levels_json.read_text())

    # Build short-name → full-path mapping (for resolving short Source comment paths)
    short_to_full: Dict[str, str] = {}
    for rel in php_files_found:
        short_to_full[Path(rel).name] = rel

    # -----------------------------------------------------------------------
    # 3. Collect all Python traceability refs
    # -----------------------------------------------------------------------
    explicit_names, line_refs, file_mentioned = collect_all_refs(python_dir, short_to_full)

    # Resolve line-range refs → add the function's bare name to explicit_names
    # (build a line → qname index from the PHP functions themselves)
    by_file_sorted: Dict[str, List[PHPFunc]] = defaultdict(list)
    for fn in php_functions:
        by_file_sorted[fn.file].append(fn)
    for funcs in by_file_sorted.values():
        funcs.sort(key=lambda f: f.start_line)

    def qname_for_line_exact(php_file: str, line: int) -> Optional[str]:
        funcs = by_file_sorted.get(php_file, [])
        best = None
        for fn in funcs:
            if fn.start_line <= line <= fn.end_line:
                return fn.qname
            if fn.start_line <= line:
                best = fn.qname
        return best

    for php_file, ranges in line_refs.items():
        for (start, end) in ranges:
            for check_line in {start, end, (start + end) // 2}:
                qn = qname_for_line_exact(php_file, check_line)
                if qn:
                    bare = qn.rsplit("::", 1)[-1] if "::" in qn else qn
                    explicit_names[php_file].add(bare.lower())
                    explicit_names[php_file].add(qn.lower())

    # -----------------------------------------------------------------------
    # 4. Audit each PHP function — file-specific matching only
    # -----------------------------------------------------------------------
    total_in_scope = 0
    total_exact = 0
    total_eliminated_bare = 0
    total_file_eliminated = 0
    total_skipped_level = 0
    total_third_party = 0
    total_file_level_only = 0
    total_missing = 0

    all_file_level_only: List[dict] = []
    all_missing: List[dict] = []

    # Line-range boundary check: cite ranges vs actual PHP boundaries
    boundary_mismatches: List[dict] = []

    for fn in php_functions:
        if _is_third_party(fn.file, fn.qname):
            total_third_party += 1
            continue

        if fn.file in ELIMINATED_FILES:
            total_file_eliminated += 1
            continue

        bare_lower = fn.bare.lower()
        qname_lower = fn.qname.lower()

        if bare_lower in {e.lower() for e in ELIMINATED_BARE}:
            total_eliminated_bare += 1
            continue
        # Also check full qname (for "ttrss/include/functions.php" style entries)
        if qname_lower in {e.lower() for e in ELIMINATED_BARE}:
            total_eliminated_bare += 1
            continue

        # Level filter (if levels are available)
        level = func_levels.get(fn.qname, func_levels.get(bare_lower, 99))
        if level > max_level:
            total_skipped_level += 1
            continue

        total_in_scope += 1

        # --- File-specific matching ONLY ---
        fn_names_for_file = explicit_names.get(fn.file, set())

        # Name match: bare name or Class::bare in this file's refs
        found_exact = bare_lower in fn_names_for_file
        if not found_exact:
            found_exact = qname_lower in fn_names_for_file
        if not found_exact and "::" in fn.qname:
            cls = fn.qname.split("::")[0]
            found_exact = (cls + "::" + fn.bare).lower() in fn_names_for_file

        if found_exact:
            total_exact += 1
            # Optionally: check cited line ranges against exact PHP boundary
            # Only flag tight citations (< 150 lines wide) that extend > 5 lines past fn end.
            # Wide ranges (e.g. "lines 1-523") are whole-file citations and are fine.
            ranges_for_file = line_refs.get(fn.file, [])
            for (cstart, cend) in ranges_for_file:
                cited_width = cend - cstart
                if cited_width >= 150:
                    continue  # whole-file or large-block citation, not a per-function cite
                # Check overlap with function
                if not (cend < fn.start_line or cstart > fn.end_line):
                    if cend > fn.end_line + 5:
                        boundary_mismatches.append({
                            "php_file": fn.file,
                            "qname": fn.qname,
                            "fn_start": fn.start_line,
                            "fn_end": fn.end_line,
                            "cited_start": cstart,
                            "cited_end": cend,
                            "issue": (f"cited end {cend} > fn end {fn.end_line}"
                                      f" by {cend - fn.end_line} lines"),
                        })
            continue

        # File mentioned but function not explicitly named
        if fn.file in file_mentioned:
            total_file_level_only += 1
            all_file_level_only.append({
                "php_file": fn.file, "qname": fn.qname,
                "start_line": fn.start_line, "end_line": fn.end_line, "level": level,
            })
        else:
            total_missing += 1
            all_missing.append({
                "php_file": fn.file, "qname": fn.qname,
                "start_line": fn.start_line, "end_line": fn.end_line, "level": level,
            })

    # -----------------------------------------------------------------------
    # 5. Report
    # -----------------------------------------------------------------------
    out_lines: List[str] = []
    w = out_lines.append

    w("=" * 72)
    w("  STRICT PHP→PYTHON COVERAGE AUDIT  (tree-sitter, file-specific only)")
    w("=" * 72)
    w("")
    w("METHODOLOGY")
    w("  - PHP functions: parsed DIRECTLY by tree-sitter (exact start+end lines)")
    w("  - Python refs:   enhanced regex covering all real-world Source formats")
    w("  - Matching:      file-specific ONLY (no global bare-name fallback)")
    w("")
    w("SUMMARY")
    w(f"  PHP files scanned (non-lib):                          {len(php_files_found)}")
    w(f"  PHP functions found (raw, all):                       {len(php_functions)}")
    w(f"  ─────────────────────────────────────────────────────")
    w(f"  In-scope (non-3rd-party, non-eliminated, level ≤ {max_level}): {total_in_scope}")
    w(f"  Exact match (file-specific name or line-range):       {total_exact}")
    w(f"  Eliminated (ELIMINATED_BARE list):                    {total_eliminated_bare}")
    w(f"  File-eliminated (whole file dropped):                 {total_file_eliminated}")
    w(f"  File-level only (file mentioned, fn not named):       {total_file_level_only}")
    w(f"  Missing (NO traceability):                            {total_missing}")
    w(f"  Skipped (level > {max_level}):                               {total_skipped_level}")
    w(f"  Skipped (third-party / lib):                          {total_third_party}")
    w("")
    # Total audited = everything not third-party and not file-eliminated
    total_audited = (total_in_scope + total_eliminated_bare
                     + total_skipped_level)
    covered = total_exact + total_eliminated_bare
    w(f"  Exact+Eliminated coverage:     {covered}/{total_audited}"
      f" = {100*covered/max(total_audited,1):.1f}%  (of in-scope+eliminated)")
    w(f"  Strict exact-only coverage:    {total_exact}/{total_in_scope}"
      f" = {100*total_exact/max(total_in_scope,1):.1f}%  (no elimination credit)")
    w("")

    if boundary_mismatches:
        w("=" * 72)
        w(f"  CITED LINE RANGE EXTENDS BEYOND FUNCTION END ({len(boundary_mismatches)})")
        w("  (Comment may be citing more lines than the PHP function body contains)")
        w("=" * 72)
        for item in boundary_mismatches[:30]:
            w(f"  {item['qname']}")
            w(f"    PHP fn:   lines {item['fn_start']}-{item['fn_end']}")
            w(f"    Cited:    lines {item['cited_start']}-{item['cited_end']}  ({item['issue']})")
        if len(boundary_mismatches) > 30:
            w(f"  ... and {len(boundary_mismatches) - 30} more")
        w("")

    if all_file_level_only:
        w("=" * 72)
        w(f"  FILE-LEVEL ONLY ({total_file_level_only}) — file cited but function not named")
        w("=" * 72)
        current_file = None
        for item in sorted(all_file_level_only,
                           key=lambda x: (x["php_file"], x["start_line"])):
            if item["php_file"] != current_file:
                current_file = item["php_file"]
                w(f"\n  [{current_file}]")
            w(f"    L{item['level']:02d}  lines {item['start_line']:4d}-{item['end_line']:4d}"
              f"  {item['qname']}")
        w("")

    if all_missing:
        w("=" * 72)
        w(f"  COMPLETELY MISSING ({total_missing}) — no traceability whatsoever")
        w("=" * 72)
        current_file = None
        for item in sorted(all_missing,
                           key=lambda x: (x["php_file"], x["start_line"])):
            if item["php_file"] != current_file:
                current_file = item["php_file"]
                w(f"\n  [{current_file}]")
            w(f"    L{item['level']:02d}  lines {item['start_line']:4d}-{item['end_line']:4d}"
              f"  {item['qname']}")
        w("")

    if not all_file_level_only and not all_missing:
        w("  All in-scope functions are exactly covered or eliminated.")
        w("")

    report = "\n".join(out_lines)
    print(report)

    out_dir = Path("tools/graph_analysis/output")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "strict_audit.txt").write_text(report)
    (out_dir / "strict_audit.json").write_text(json.dumps({
        "summary": {
            "php_files_scanned": len(php_files_found),
            "php_functions_raw": len(php_functions),
            "in_scope": total_in_scope,
            "exact": total_exact,
            "eliminated_bare": total_eliminated_bare,
            "file_eliminated": total_file_eliminated,
            "file_level_only": total_file_level_only,
            "missing": total_missing,
            "skipped_level": total_skipped_level,
            "third_party": total_third_party,
        },
        "boundary_mismatches": boundary_mismatches,
        "file_level_only": all_file_level_only,
        "missing": all_missing,
    }, indent=2))

    print(f"\nFull report: tools/graph_analysis/output/strict_audit.txt",
          file=sys.stderr)
    print(f"JSON report: tools/graph_analysis/output/strict_audit.json",
          file=sys.stderr)

    if total_missing > 0 or total_file_level_only > 0:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Strict PHP→Python coverage audit via tree-sitter"
    )
    parser.add_argument("--php-dir", default="source-repos/ttrss-php/ttrss",
                        help="PHP source root (default: source-repos/ttrss-php/ttrss)")
    parser.add_argument("--python-dir", default="target-repos/ttrss-python/ttrss",
                        help="Python target root")
    parser.add_argument("--levels-json",
                        default="tools/graph_analysis/output/function_levels.json",
                        help="function_levels.json from call graph (for level filter)")
    parser.add_argument("--max-level", type=int, default=10,
                        help="Skip functions with level > N (default 10)")
    args = parser.parse_args()

    levels_path = Path(args.levels_json) if args.levels_json else None
    run_audit(
        php_dir=Path(args.php_dir),
        python_dir=Path(args.python_dir),
        levels_json=levels_path,
        max_level=args.max_level,
    )
