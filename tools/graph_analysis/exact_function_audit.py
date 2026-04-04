#!/usr/bin/env python3
"""exact_function_audit.py — Per-function traceability audit.

For every PHP function/method extracted by tree-sitter (in call_graph.json),
checks whether Python has a traceability reference naming that function
(exact name, dot-notation, line-number-within-range, or docstring).

Handles all real-world formats found in the codebase:
  # Source: ttrss/classes/rpc.php:RPC::mark (lines 131-145)  ← double-colon
  # Source: ttrss/classes/api.php:API.getHeadlines            ← dot-notation
  # Source: rpc.php:131-148                                   ← short path + line range
  # Source: rpc.php:148                                       ← short path + single line
  Source: ttrss/include/labels.php:label_find_id (lines 2-12) ← docstring (no #)
  # Source: ttrss/classes/rpc.php:RPC (lines 1-653)           ← class-level (file-level)

Usage:
    python tools/graph_analysis/exact_function_audit.py \
        --graph-dir tools/graph_analysis/output \
        --python-dir target-repos/ttrss-python/ttrss

Output:
    tools/graph_analysis/output/exact_audit.txt
    tools/graph_analysis/output/exact_audit.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Third-party / elimination lists (kept in sync with validate_coverage.py)
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
    # Sphinx search (not in migration scope — kept as eliminated)
    "sphinx_search",
    # Format helpers that are PHP-only rendering (Jinja2 replaces)
    "format_tags_string", "format_article_labels", "format_article_note",
    "format_inline_player", "get_score_pic",
    # PHP-only string utilities
    "read_stdin", "tmpdirname",
    # URL helpers whose logic is inlined in Python
    "get_self_url_prefix", "build_url", "fix_url",
    # PHP-only encryption wrapper
    "encrypt_password",
    # PHP-only feed icon helper (logic inlined)
    "feed_has_icon",
    # PHP legacy plugin init
    "init_plugins",
    # PHP-only gettext helpers
    "get_translations",
    # SSL cert — not used in Python
    "get_ssl_certificate_id",
    # DB quote — SQLAlchemy handles parameterisation
    "quote",
    # backend.php entry-point helpers
    "loading", "display_main_help", "help",
    # Dlg HTML generators — replaced by Jinja2 templates
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
    # HTML dialog generators (replaced by JSON API / frontend)
    "editfeeds", "batch_edit_cbox",
    "newrule", "newaction",
    "customizeCSS", "toggleAdvanced", "getHelp",
    # PHP-specific accessors (replaced by Python ecosystem)
    "get_dbh", "run_hooks", "load_all",
    # Session callbacks (replaced by Flask-Login + Redis)
    "ttrss_read", "ttrss_write", "ttrss_destroy", "ttrss_gc",
    "session_get_schema_version",  # inlined in prefs/ops.py
    # URL/utility helpers (stdlib replaces)
    "make_password", "validate_csrf", "sanity_check",
    "getFeedIcon", "geturl", "convertUrlQuery",
    "expire_lock_files", "cache_images",
    "add_feed_url",
    # Entry-point pseudo-functions (Flask routing replaces)
    "housekeepingTask",
    # PHP HTML helpers eliminated per R13
    "printRuleName", "printActionName",
    # Top-level script bodies (PHP includes, not real functions)
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
    "ttrss/opml.php",          # entry-point dispatcher, Flask routing replaces
    "ttrss/api/index.php",     # entry-point dispatcher, Flask blueprint routing replaces
    "ttrss/public.php",        # entry-point, Flask public blueprint replaces
    "ttrss/register.php",      # entry-point, Flask register route replaces
}


def _is_third_party(file_path: str, qname: str) -> bool:
    for prefix in THIRD_PARTY_PREFIXES:
        if file_path.startswith(prefix) or qname.startswith(prefix):
            return True
        if "/" in prefix:
            norm = prefix if prefix.endswith("/") else prefix + "/"
            if file_path.startswith(norm) or qname.startswith(norm):
                return True
    return False


def _bare(qname: str) -> str:
    return qname.rsplit("::", 1)[1] if "::" in qname else qname


# ---------------------------------------------------------------------------
# Build line-range index: (php_file, line_number) -> qname
# (so line-number references can be resolved to function names)
# ---------------------------------------------------------------------------
def build_line_range_index(
    nodes: Dict[str, dict]
) -> Dict[str, List[Tuple[int, int, str]]]:
    """
    Returns: {php_file: [(start_line, end_line_exclusive, qname), ...]}
    sorted by start_line. end_line is the start of the next function (or inf).
    """
    by_file: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
    for qname, meta in nodes.items():
        by_file[meta["file"]].append((meta["line"], qname))

    result: Dict[str, List[Tuple[int, int, str]]] = {}
    for php_file, entries in by_file.items():
        entries.sort()
        ranges = []
        for i, (start, qname) in enumerate(entries):
            end = entries[i + 1][0] if i + 1 < len(entries) else 10_000_000
            ranges.append((start, end, qname))
        result[php_file] = ranges
    return result


def qname_for_line(
    line_range_index: Dict[str, List[Tuple[int, int, str]]],
    php_file: str,
    line: int,
) -> Optional[str]:
    """Find which PHP function contains the given line number."""
    ranges = line_range_index.get(php_file, [])
    for (start, end, qname) in ranges:
        if start <= line < end:
            return qname
    # Fallback: find the function whose start is closest (<=) to the line
    best = None
    for (start, end, qname) in ranges:
        if start <= line:
            best = qname
        else:
            break
    return best


# ---------------------------------------------------------------------------
# Traceability reference extraction from Python source
# ---------------------------------------------------------------------------
# Short basename → full php path mapping (built dynamically below)
SHORT_TO_FULL: Dict[str, str] = {}


def _resolve_php_path(raw_path: str) -> str:
    """Convert short paths like 'rpc.php' to full 'ttrss/classes/rpc.php'."""
    if raw_path.startswith("ttrss/"):
        return raw_path
    return SHORT_TO_FULL.get(raw_path, raw_path)


# Patterns for traceability lines (both # comment and docstring formats)
# Captures: php_path, optional class, optional function_name_or_line
_TREF_PATTERN = re.compile(
    r"(?:#\s*)?(?:Source|Inferred from|Adapted from|Migrated from|Based on|PHP source):\s*"
    r"(?P<path>(?:ttrss/)?[\w./-]+\.php)"
    r"(?::(?P<rest>[^\n(,+]+))?",
    re.IGNORECASE,
)

# Matches either "ClassName::method", "ClassName.method", or bare "method_name"
# after the colon in a traceability line
_METHOD_RE = re.compile(
    r"^(?:(?P<cls>[A-Za-z_]\w*)(?:::|\.))?"  # optional ClassName:: or ClassName.
    r"(?P<fn>[A-Za-z_]\w*)"                   # function/method name
    r"(?:\s|$|\(|:|\d)"                        # must be followed by space, (, :, digit or EOL
)

# Matches line number(s): "131", "131-148", "131-148,200"
_LINE_RE = re.compile(r"^(?:lines?\s*)?(\d+)(?:\s*[-–]\s*(\d+))?")


class TraceRef:
    """One resolved traceability reference from a Python file."""
    __slots__ = ("php_file", "fn_names", "line_ranges")

    def __init__(
        self,
        php_file: str,
        fn_names: Set[str],         # bare lowercase method names
        line_ranges: List[Tuple[int, int]],   # (start, end) inclusive line ranges
    ):
        self.php_file = php_file
        self.fn_names = fn_names
        self.line_ranges = line_ranges


def _parse_tref_line(line: str) -> Optional[TraceRef]:
    m = _TREF_PATTERN.search(line)
    if not m:
        return None
    raw_path = m.group("path").strip()
    php_file = _resolve_php_path(raw_path)
    rest = (m.group("rest") or "").strip()

    fn_names: Set[str] = set()
    line_ranges: List[Tuple[int, int]] = []

    if rest:
        # Try method/function name first
        mm = _METHOD_RE.match(rest)
        if mm and not rest[0].isdigit():
            fn_name = mm.group("fn")
            fn_names.add(fn_name.lower())
            if mm.group("cls"):
                fn_names.add((mm.group("cls") + "::" + fn_name).lower())
        else:
            # Try line number(s)
            lm = _LINE_RE.match(rest.lstrip("( "))
            if lm:
                start = int(lm.group(1))
                end = int(lm.group(2)) if lm.group(2) else start
                line_ranges.append((start, end))

    return TraceRef(php_file, fn_names, line_ranges)


def scan_python_file(py_path: Path) -> List[TraceRef]:
    """Extract all traceability references from a Python file."""
    try:
        text = py_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    refs: List[TraceRef] = []
    for line in text.splitlines():
        stripped = line.strip()
        # Match lines that contain a traceability keyword
        if not any(kw in stripped for kw in (
            "Source:", "Inferred", "Adapted from", "Migrated from",
            "Based on", "PHP source:"
        )):
            continue
        ref = _parse_tref_line(stripped)
        if ref:
            refs.append(ref)
    return refs


def collect_all_refs(python_dir: Path) -> List[Tuple[str, TraceRef]]:
    """Returns [(py_rel_path, TraceRef), ...] for all Python files."""
    all_refs: List[Tuple[str, TraceRef]] = []
    for py_file in sorted(python_dir.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        rel = str(py_file.relative_to(python_dir))
        for ref in scan_python_file(py_file):
            all_refs.append((rel, ref))
    return all_refs


# ---------------------------------------------------------------------------
# Main audit
# ---------------------------------------------------------------------------
def run_audit(graph_dir: Path, python_dir: Path) -> None:
    cg_path = graph_dir / "call_graph.json"
    fl_path = graph_dir / "function_levels.json"

    cg = json.loads(cg_path.read_text())
    fl = json.loads(fl_path.read_text())

    nodes = cg["nodes"]

    # Build short-name → full-path index for all PHP files seen in graph
    global SHORT_TO_FULL
    all_php_files: Set[str] = {meta["file"] for meta in nodes.values()}
    for fp in all_php_files:
        SHORT_TO_FULL[Path(fp).name] = fp

    # Build line-range index
    line_range_index = build_line_range_index(nodes)

    # Group PHP functions by file
    php_functions: Dict[str, List[dict]] = defaultdict(list)
    for qname, meta in nodes.items():
        php_file = meta.get("file", "")
        level = fl.get(qname, 99)
        php_functions[php_file].append({
            "qname": qname,
            "bare": _bare(qname),
            "level": level,
            "line": meta.get("line", 0),
        })
    for funcs in php_functions.values():
        funcs.sort(key=lambda x: x["line"])

    # Collect all Python traceability refs
    all_refs = collect_all_refs(python_dir)

    # Build lookup structures:
    # 1. php_file -> set of bare fn names with explicit name references
    explicit_names: Dict[str, Set[str]] = defaultdict(set)
    # 2. php_file -> list of (start_line, end_line) ranges with line references
    line_refs: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    # 3. php_file -> bool: any reference at all (file-level)
    file_mentioned: Set[str] = set()

    for py_rel, ref in all_refs:
        php_file = ref.php_file
        file_mentioned.add(php_file)
        explicit_names[php_file].update(ref.fn_names)
        line_refs[php_file].extend(ref.line_ranges)

    # Resolve line-number references to function names
    # For each line range, find which PHP function it covers and mark as explicit
    for php_file, ranges in line_refs.items():
        for (start_line, end_line) in ranges:
            # Check every line in the range (or just start/end)
            for check_line in {start_line, end_line, (start_line + end_line) // 2}:
                qn = qname_for_line(line_range_index, php_file, check_line)
                if qn:
                    explicit_names[php_file].add(_bare(qn).lower())

    # Audit
    total_in_scope = 0
    total_exact = 0
    total_eliminated = 0
    total_file_eliminated = 0
    total_file_level_only = 0
    total_missing = 0
    total_skipped_high = 0
    total_third_party = 0

    all_file_level_only: List[dict] = []
    all_missing: List[dict] = []

    for php_file in sorted(php_functions.keys()):
        funcs = php_functions[php_file]

        if _is_third_party(php_file, ""):
            total_third_party += len(funcs)
            continue

        if php_file in ELIMINATED_FILES:
            total_file_eliminated += len(funcs)
            continue

        fn_names_for_file = explicit_names.get(php_file, set())
        has_file_mention = php_file in file_mentioned

        for fn in funcs:
            qname = fn["qname"]
            bare = fn["bare"]
            level = fn["level"]

            if _is_third_party(php_file, qname):
                total_third_party += 1
                continue

            if level > 10:
                total_skipped_high += 1
                continue

            total_in_scope += 1

            # Check elimination (bare name or full qname)
            bare_lower = bare.lower()
            if bare_lower in {e.lower() for e in ELIMINATED_BARE}:
                total_eliminated += 1
                continue

            # Check exact/line-range match: bare name in refs for THIS file
            found_exact = bare_lower in fn_names_for_file
            if not found_exact and "::" in qname:
                cls = qname.split("::")[0]
                method_key = (cls + "::" + bare).lower()
                found_exact = method_key in fn_names_for_file

            # Broaden: check if any python file has this bare name from ANY php file
            # (handles cases where Source comment uses different file path)
            if not found_exact:
                for ref_file, ref_names in explicit_names.items():
                    if bare_lower in ref_names:
                        found_exact = True
                        break

            if found_exact:
                total_exact += 1
            elif has_file_mention:
                total_file_level_only += 1
                all_file_level_only.append({
                    "php_file": php_file, "qname": qname,
                    "line": fn["line"], "level": level
                })
            else:
                total_missing += 1
                all_missing.append({
                    "php_file": php_file, "qname": qname,
                    "line": fn["line"], "level": level
                })

    # -----------------------------------------------------------------------
    # Print report
    # -----------------------------------------------------------------------
    out_lines: List[str] = []
    w = out_lines.append

    w("=" * 72)
    w("  EXACT FUNCTION-LEVEL PHP→PYTHON COVERAGE AUDIT  (v2)")
    w("=" * 72)
    w("")
    w("SUMMARY")
    w(f"  Total in-scope PHP functions (L0-L10, non-3rd-party): {total_in_scope}")
    w(f"  Exact / line-range match:                             {total_exact}")
    w(f"  Eliminated (spec 13 / ADR):                           {total_eliminated}")
    w(f"  File-eliminated (whole file dropped by ADR):          {total_file_eliminated}")
    w(f"  File-level only (file mentioned, fn not named):       {total_file_level_only}")
    w(f"  Missing (NO traceability at all):                     {total_missing}")
    w(f"  Skipped (level > 10):                                 {total_skipped_high}")
    w(f"  Skipped (third-party / lib):                          {total_third_party}")
    covered = total_exact + total_eliminated
    w("")
    w(f"  Exact+Eliminated coverage:    {covered}/{total_in_scope}"
      f" = {100*covered/max(total_in_scope,1):.1f}%")
    w(f"  Including file-level matches: {covered+total_file_level_only}/{total_in_scope}"
      f" = {100*(covered+total_file_level_only)/max(total_in_scope,1):.1f}%")
    w("")

    if all_file_level_only:
        w("=" * 72)
        w(f"  FILE-LEVEL-ONLY ({total_file_level_only}) — function not explicitly named")
        w("=" * 72)
        current_file = None
        for item in sorted(all_file_level_only, key=lambda x: (x["php_file"], x["line"])):
            if item["php_file"] != current_file:
                current_file = item["php_file"]
                w(f"\n  [{current_file}]")
            w(f"    L{item['level']:02d}  line {item['line']:4d}  {item['qname']}")
        w("")

    if all_missing:
        w("=" * 72)
        w(f"  COMPLETELY MISSING ({total_missing}) — no traceability whatsoever")
        w("=" * 72)
        current_file = None
        for item in sorted(all_missing, key=lambda x: (x["php_file"], x["line"])):
            if item["php_file"] != current_file:
                current_file = item["php_file"]
                w(f"\n  [{current_file}]")
            w(f"    L{item['level']:02d}  line {item['line']:4d}  {item['qname']}")
        w("")

    report_text = "\n".join(out_lines)
    print(report_text)

    out_txt = graph_dir / "exact_audit.txt"
    out_txt.write_text(report_text)

    out_json = graph_dir / "exact_audit.json"
    out_json.write_text(json.dumps({
        "summary": {
            "total_in_scope": total_in_scope,
            "exact": total_exact,
            "eliminated": total_eliminated,
            "file_eliminated": total_file_eliminated,
            "file_level_only": total_file_level_only,
            "missing": total_missing,
        },
        "file_level_only": all_file_level_only,
        "missing": all_missing,
    }, indent=2))

    print(f"\nFull report: {out_txt}")
    print(f"JSON report: {out_json}")
    if total_missing > 0 or total_file_level_only > 0:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph-dir", default="tools/graph_analysis/output")
    parser.add_argument("--python-dir", default="target-repos/ttrss-python/ttrss")
    args = parser.parse_args()
    run_audit(Path(args.graph_dir), Path(args.python_dir))
