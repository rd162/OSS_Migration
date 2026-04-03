# ADR-0014: Feed Parsing Library

- **Status**: proposed
- **Date proposed**: 2026-04-03
- **Deciders**: TBD

## Context

The PHP codebase uses a custom `FeedParser` class (`classes/feedparser.php`) built on PHP's `DOMDocument` XML parser. It supports:
- RSS 0.91, 0.92, 1.0 (RDF), 2.0
- Atom 1.0
- Content extraction from `content:encoded`, `description`, `summary`, `atom:content`
- Enclosure/media attachment parsing
- Feed metadata (title, link, language, last-modified)
- Custom `FeedItem` classes (`FeedItem_Atom`, `FeedItem_RSS`) with common interface

The PHP parser handles real-world feed quirks: malformed XML, mixed encodings, HTML entities in CDATA, missing required elements, and namespace variations. These edge cases represent years of accumulated fixes.

The Python replacement must parse the same feed formats with equivalent robustness for real-world feeds.

## Options

### A: feedparser (Universal Feed Parser)

Use `feedparser` (Mark Pilgrim's Universal Feed Parser), the de facto standard Python library for RSS/Atom parsing. Handles virtually all feed formats and edge cases.

- Parses RSS (all versions), Atom, RDF, CDF
- Extensive edge-case handling (20+ years of fixes)
- HTML sanitization built-in (can be disabled)
- Bozo detection for ill-formed feeds (parses anyway)
- Returns normalized dict structures regardless of feed format
- No async support (sync only)

### B: lxml + Custom Parser

Build a custom parser using `lxml.etree` (the Python equivalent of PHP's DOMDocument). Port the PHP `FeedParser` logic directly, using XPath for element extraction.

- Closest architectural match to PHP code
- Full control over parsing behavior
- Must reimplement all edge-case handling from scratch
- XPath-based extraction is powerful but verbose
- `lxml` is fast (C-based libxml2 binding)

### C: atoma

Use `atoma`, a modern, typed RSS/Atom parser. Returns dataclasses for feed items. Lighter than feedparser.

- Clean, typed API (dataclasses)
- Supports RSS 2.0, Atom 1.0, RSS 1.0, JSON Feed
- Less mature than feedparser (fewer edge-case fixes)
- No built-in HTML sanitization
- Smaller community and contributor base

## Trade-off Analysis

| Criterion | A: feedparser | B: lxml + Custom | C: atoma |
|-----------|--------------|-----------------|----------|
| Feed format coverage | Excellent (all versions) | Must implement each | Good (major formats) |
| Edge-case robustness | Excellent (20+ years) | Must reimplement | Moderate |
| Malformed XML tolerance | Excellent (bozo mode) | lxml strict by default | Moderate |
| API ergonomics | Good (normalized dicts) | Custom (full control) | Excellent (dataclasses) |
| HTML sanitization | Built-in | Manual (lxml.html.clean) | None |
| Performance | Good | Excellent (C-based) | Good |
| Maintenance / community | Active, large community | N/A (custom) | Small community |
| Migration effort | Low (use directly) | High (port all logic) | Low (use directly) |
| Type annotations | Partial | Custom | Full (dataclasses) |
| Enclosure/media support | Yes | Must implement | Yes |

## Preliminary Recommendation

**Option A (feedparser)** as the primary feed parsing library, supplemented by **lxml** for HTML content sanitization and any custom post-processing.

Rationale:
1. **feedparser** has 20+ years of edge-case fixes for real-world feeds — replicating this in a custom parser would take months and still miss cases
2. **Bozo detection** gracefully handles malformed XML that would crash strict parsers
3. **Normalized output** means the application code does not need to handle RSS-vs-Atom differences
4. **lxml** is still useful for HTML sanitization (`lxml.html.clean` or `bleach` + `lxml`) of feed content before storage/display

Architecture:
- `feedparser.parse(raw_xml)` for feed parsing
- `lxml.html.clean` (or `bleach`) for sanitizing HTML content from feed items
- Custom post-processing layer for TT-RSS-specific logic (score calculation, label matching, plugin hooks)

## Decision

**TBD**

## Consequences

- If Option A: feedparser's normalized output simplifies handler code (no RSS/Atom branching)
- If Option A: feedparser is sync-only; feed fetching (HTTP) can still be async, parsing happens after download
- If Option A: some feedparser quirks may differ from PHP parser behavior — integration tests needed
- If Option B: maximum control but months of edge-case discovery and fixing
- If Option C: modern API but risk of missing edge cases in production feeds
- All options: HTML sanitization is a separate concern (feed content must be cleaned before display)
