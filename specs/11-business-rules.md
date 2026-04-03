# 11 - Business Rules

Comprehensive business rules extracted from the TT-RSS PHP source. All file:line references are relative to `source-repos/ttrss-php/ttrss/`.

---

## 1. Article Deduplication

**Source:** `include/rssfuncs.php:550-766`

### GUID Construction (rssfuncs.php:550-553)

Priority chain for entry GUID:

1. `$item->get_id()` -- the feed-provided article ID (Atom `<id>`, RSS `<guid>`)
2. Fallback: `$item->get_link()` -- the article permalink
3. Fallback: `make_guid_from_title($item->get_title())` -- title with `[ "',.:;]` replaced by `-`, lowercased, tags stripped (rssfuncs.php:1401-1403)

If all three are empty/falsy, the article is **skipped** (`continue`, rssfuncs.php:556).

### Owner UID Prefixing (rssfuncs.php:558)

```
$entry_guid = "$owner_uid,$entry_guid";
```

Multi-user isolation: every GUID is prefixed with the feed owner's UID and a comma. Two users subscribing to the same feed get independent `ttrss_entries` rows.

### SHA1 Hashing (rssfuncs.php:560)

```
$entry_guid_hashed = 'SHA1:' . sha1($entry_guid)
```

The hashed GUID is stored in `ttrss_entries.guid`. Both the raw guid and the hashed form are checked during lookups. The GUID is truncated to 245 chars before hashing (rssfuncs.php:621).

### Content Hash (rssfuncs.php:707)

```
$content_hash = "SHA1:" . sha1($entry_content)
```

Stored in `ttrss_entries.content_hash`. Used to detect content changes on existing entries (rssfuncs.php:936: `$content_hash != $orig_content_hash`).

### Duplicate Detection Flow (rssfuncs.php:711-766)

1. **Check ttrss_entries** by GUID: `WHERE guid = '$entry_guid' OR guid = '$entry_guid_hashed'` (rssfuncs.php:711-712)
2. If not found: INSERT new entry into `ttrss_entries` with `$entry_guid_hashed` as stored guid (rssfuncs.php:720-750)
3. If found: UPDATE `date_updated = NOW()` to prevent purge-and-reinsert duplication (rssfuncs.php:762-763)
4. **Check ttrss_user_entries** for user-specific record (rssfuncs.php:832-834):
   - If `ALLOW_DUPLICATE_POSTS` pref is true: restrict to same feed (`feed_id = '$feed' OR feed_id IS NULL`)
   - If false (default): no feed restriction -- GUID-level global dedup per user

### PostgreSQL N-gram Title Similarity (rssfuncs.php:867-882)

Enabled only when:
- `DB_TYPE == "pgsql"` AND `_NGRAM_TITLE_DUPLICATE_THRESHOLD` is defined

```sql
SELECT COUNT(*) AS similar FROM ttrss_entries, ttrss_user_entries
WHERE ref_id = id
  AND updated >= NOW() - INTERVAL '7 day'
  AND similarity(title, '$entry_title') >= {_NGRAM_TITLE_DUPLICATE_THRESHOLD}
  AND owner_uid = $owner_uid
```

If `similar > 0`, the new article is marked as **read** (`unread = 'false'`). Uses PostgreSQL `pg_trgm` extension's `similarity()` function.

---

## 2. Filter Evaluation

**Source:** `include/functions2.php:1491-1563` (loading), `include/rssfuncs.php:1272-1348` (evaluation)

### Filter Loading (functions2.php:1491-1563)

```sql
SELECT * FROM ttrss_filters2
WHERE owner_uid = $owner_uid AND enabled = true
ORDER BY order_id, title
```

For each filter, rules are loaded with scope restriction:
- Rules match if: `(cat_id IS NULL AND cat_filter = false) OR cat_id IN ($check_cats)` AND `(feed_id IS NULL OR feed_id = '$feed_id')`
- `$check_cats` includes the feed's category AND all its parent categories (via `getParentCategories()`)
- Filters with zero rules or zero actions are **discarded** (functions2.php:1557)

Each filter produces a struct:
```python
{
    "match_any_rule": bool,   # from ttrss_filters2.match_any_rule
    "inverse": bool,          # from ttrss_filters2.inverse
    "rules": [{"reg_exp": str, "type": str, "inverse": bool}],
    "actions": [{"type": str, "param": str}]
}
```

### Rule Evaluation (rssfuncs.php:1272-1348)

For each filter, iterate over its rules:

**6 rule types** (rssfuncs.php:1288-1317), all regex, case-insensitive (`/regex/i`):

| Type | Field tested | Notes |
|------|-------------|-------|
| `title` | `$title` | |
| `content` | `$content` | `[\r\n\t]` stripped before matching |
| `both` | `$title` OR `$content` | Content has `[\r\n\t]` stripped |
| `link` | `$link` | |
| `author` | `$author` | |
| `tag` | each `$tag` in `$tags` | Match if ANY tag matches |

Forward slashes in `reg_exp` are escaped: `str_replace('/', '\/', $rule["reg_exp"])` (rssfuncs.php:1282).

Regex errors are suppressed with `@preg_match` (rssfuncs.php:1290).

**Rule inversion** (rssfuncs.php:1320): `if ($rule_inverse) $match = !$match`

**Rule combination** (rssfuncs.php:1322-1332):
- `match_any_rule = true` (OR mode): first matching rule sets `filter_match = true` and breaks
- `match_any_rule = false` (AND mode): all rules must match; first non-match sets `filter_match = false` and breaks

**Filter inversion** (rssfuncs.php:1335): `if ($inverse) $filter_match = !$filter_match`

### Action Processing (rssfuncs.php:1337-1344)

If filter matches, all its actions are appended to the result array.

**8 action types:**

| Action | Effect | Source |
|--------|--------|--------|
| `filter` | Article is **skipped entirely** (not inserted) | rssfuncs.php:823-826 |
| `catchup` | Article inserted as **read** (`unread = false`) | rssfuncs.php:845 |
| `mark` | Article **starred** (`marked = true`) | rssfuncs.php:853 |
| `publish` | Article **published** (`published = true`) | rssfuncs.php:859 |
| `score` | Score adjustment (additive, param is integer) | rssfuncs.php:1370-1379 |
| `label` | Assign label by caption (param is label caption) | rssfuncs.php:1391-1398 |
| `tag` | Add manual tags (param is CSV tag list) | rssfuncs.php:1026-1037 |
| `stop` | **Terminate filter processing immediately** -- no further filters evaluated | rssfuncs.php:1342 |

---

## 3. Scoring

**Source:** `include/rssfuncs.php:828, 1370-1379`

### Calculation (rssfuncs.php:1370-1379)

```python
score = sum(f["param"] for f in filters if f["type"] == "score")
```

All "score" actions from all matching filters are summed. `param` is cast to integer.

### Auto-action Thresholds (rssfuncs.php:845-857)

| Condition | Effect |
|-----------|--------|
| `score >= -500` AND no `catchup` filter | `unread = true` |
| `score < -500` OR `catchup` filter | `unread = false` (auto-read) |
| `score > 1000` OR `mark` filter | `marked = true` (auto-starred) |

### Display Score Icons (functions2.php:1565-1577)

| Score range | Icon | Semantic |
|-------------|------|----------|
| `> 100` | `score_high.png` | High |
| `> 0` (and <= 100) | `score_half_high.png` | Half-high |
| `< -100` | `score_low.png` | Low |
| `< 0` (and >= -100) | `score_half_low.png` | Half-low |
| `== 0` | `score_neutral.png` | Neutral |

---

## 4. Feed Update Scheduling

**Source:** `include/rssfuncs.php:60-130`

### Update Interval Resolution

Per-feed `ttrss_feeds.update_interval`:
- `-1` = **disabled** (never updated, but note: the exclusion is done via the user pref side, not directly; feeds with interval > 0 always qualify)
- `0` = use user's `DEFAULT_UPDATE_INTERVAL` pref (via `ttrss_user_prefs`)
- `> 0` = interval in **minutes**

User pref `DEFAULT_UPDATE_INTERVAL`:
- `-1` = user's feeds with `update_interval = 0` are **disabled**
- Other values = interval in minutes

### Stale Lock Detection (rssfuncs.php:110-114)

```sql
-- PostgreSQL:
ttrss_feeds.last_update_started IS NULL
OR ttrss_feeds.last_update_started < NOW() - INTERVAL '10 minutes'

-- MySQL:
ttrss_feeds.last_update_started IS NULL
OR ttrss_feeds.last_update_started < DATE_SUB(NOW(), INTERVAL 10 MINUTE)
```

A feed currently being updated by another process is excluded unless the lock is older than 10 minutes. **This is not atomic** -- race conditions are possible between the SELECT and the subsequent UPDATE of `last_update_started`.

### Login Activity Filter (rssfuncs.php:72-80)

```sql
-- PostgreSQL (when DAEMON_UPDATE_LOGIN_LIMIT > 0):
AND ttrss_users.last_login >= NOW() - INTERVAL '{DAEMON_UPDATE_LOGIN_LIMIT} days'

-- MySQL:
AND ttrss_users.last_login >= DATE_SUB(NOW(), INTERVAL {DAEMON_UPDATE_LOGIN_LIMIT} DAY)
```

Default: `DAEMON_UPDATE_LOGIN_LIMIT = 30` (rssfuncs.php:2). Disabled in `SINGLE_USER_MODE`.

### Full Scheduling Query (rssfuncs.php:120-130)

```sql
SELECT DISTINCT ttrss_feeds.feed_url, ttrss_feeds.last_updated
FROM ttrss_feeds, ttrss_users, ttrss_user_prefs
WHERE
    ttrss_feeds.owner_uid = ttrss_users.id
    AND ttrss_user_prefs.profile IS NULL
    AND ttrss_users.id = ttrss_user_prefs.owner_uid
    AND ttrss_user_prefs.pref_name = 'DEFAULT_UPDATE_INTERVAL'
    {$login_thresh_qpart}
    {$update_limit_qpart}
    {$updstart_thresh_qpart}
ORDER BY last_updated
LIMIT {$limit}
```

Feeds are selected by `feed_url` (not feed ID) to enable cache sharing across users subscribing to the same URL.

### Pre-update Lock (rssfuncs.php:154-156)

Before processing, all selected feeds get their lock timestamp updated atomically:
```sql
UPDATE ttrss_feeds SET last_update_started = NOW()
WHERE feed_url IN ({quoted_urls})
```

---

## 5. View Modes

**Source:** `include/functions2.php:461-491, 634-636`

### SQL WHERE Clauses

| View mode | SQL WHERE clause | Notes |
|-----------|-----------------|-------|
| `adaptive` | `unread = true AND` (if feed has unread > 0, else no filter) | For search: no filter. For feed -1 (starred): no filter. Checks `getFeedUnread()` + child category unread (functions2.php:461-475) |
| `marked` | `marked = true AND` | (functions2.php:477-478) |
| `has_note` | `(note IS NOT NULL AND note != '') AND` | (functions2.php:481-482) |
| `published` | `published = true AND` | (functions2.php:485-486) |
| `unread` | `unread = true AND` | Except when feed == -6 (Recently Read) (functions2.php:489-490) |
| `unread_first` | No WHERE filter; adds `unread DESC` to ORDER BY | (functions2.php:634-636) |

Default ORDER BY: `score DESC, date_entered DESC, updated DESC` (functions2.php:632).

---

## 6. Article Purging

**Source:** `include/functions.php:209-291`

### Purge Interval Resolution (functions.php:293-310)

1. Feed-specific: `ttrss_feeds.purge_interval`
2. If 0: user pref `PURGE_OLD_DAYS`
3. If -1 or 0 after resolution: **no purge** (functions.php:224-229)

### FORCE_ARTICLE_PURGE Override (functions.php:233-239)

If `FORCE_ARTICLE_PURGE != 0`:
- `purge_unread = true` (overrides user pref)
- `purge_interval = FORCE_ARTICLE_PURGE` (overrides per-feed/user interval)

### Purge Protection Rules

- **Starred articles are NEVER purged**: `marked = false` is always in the DELETE WHERE clause (functions.php:250, 257-263, 273-279)
- **Unread article protection**: controlled by `PURGE_UNREAD_ARTICLES` user pref (functions.php:234-235)
  - If false (default): adds `unread = false AND` to WHERE clause
  - If true: unread articles can be purged
  - Overridden to true when `FORCE_ARTICLE_PURGE != 0`

### Purge SQL (functions.php:257-279)

```sql
-- PostgreSQL (8.1+):
DELETE FROM ttrss_user_entries
USING ttrss_entries
WHERE ttrss_entries.id = ref_id
  AND marked = false
  AND feed_id = '$feed_id'
  AND {$query_limit}  -- "unread = false AND" if unread protection enabled
  AND ttrss_entries.date_updated < NOW() - INTERVAL '$purge_interval days'

-- MySQL:
DELETE FROM ttrss_user_entries
USING ttrss_user_entries, ttrss_entries
WHERE ttrss_entries.id = ref_id
  AND marked = false
  AND feed_id = '$feed_id'
  AND {$query_limit}
  AND ttrss_entries.date_updated < DATE_SUB(NOW(), INTERVAL $purge_interval DAY)
```

### Post-purge Actions (functions.php:284)

Counter cache is updated: `ccache_update($feed_id, $owner_uid)`.

### Orphan Cleanup (functions.php:312-322)

Separate function `purge_orphans()`:
```sql
DELETE FROM ttrss_entries
WHERE (SELECT COUNT(int_id) FROM ttrss_user_entries WHERE ref_id = id) = 0
```

Called during housekeeping (rssfuncs.php:1423), NOT during individual feed purges.

---

## 7. Catchup Operation

**Source:** `include/functions.php:1094-1237`

### Time Modes (functions.php:1104-1128)

| Mode | SQL date filter |
|------|----------------|
| `1day` | `date_entered < NOW() - INTERVAL '1 day'` |
| `1week` | `date_entered < NOW() - INTERVAL '1 week'` |
| `2week` | `date_entered < NOW() - INTERVAL '2 week'` |
| `all` (default) | `true` (no date restriction) |

### Feed Type Dispatch

All catchup sets `unread = false, last_read = NOW()`.

**Category view** (`$cat_view = true`, functions.php:1131-1159):
- `feed > 0`: Gets child categories via `getChildCategories()`, marks all feeds in those categories
- `feed == 0`: Uncategorized feeds (`cat_id IS NULL`)
- `feed == -2` (Labels category): Uses `ttrss_user_labels2` join

**Feed view** (`$cat_view = false`, functions.php:1161-1224):
- `feed > 0`: Single feed catchup
- `feed == -1` (Starred): `marked = true`
- `feed == -2` (Published): `published = true`
- `feed == -3` (Fresh): `date_entered > NOW() - INTERVAL '$intl hour'` where `$intl = FRESH_ARTICLE_MAX_AGE` pref
- `feed == -4` (All): No additional filter
- `feed < LABEL_BASE_INDEX` (Label): Joins `ttrss_user_labels2` with `label_id`

**Tag catchup** (non-numeric feed, functions.php:1228-1234): Joins `ttrss_tags` by `tag_name`.

**Max ID parameter**: Not used in this implementation (parameter exists in signature but not in WHERE clauses -- the `$max_id` parameter at functions.php:1094 is referenced elsewhere in the API layer).

### Post-catchup Cache Update (functions.php:1226)

```python
ccache_update(feed, owner_uid, cat_view)
```

---

## 8. Special Feed IDs

**Source:** `include/functions.php:5-6`, `include/functions2.php:554-630`

### Constants (functions.php:5-6)

```python
LABEL_BASE_INDEX = -1024
PLUGIN_FEED_BASE_INDEX = -128
```

### Virtual Feed ID Map

| ID | Name | Query strategy (functions2.php) |
|----|------|-------------------------------|
| `-1` | Starred | `marked = true` (line 560-561). Order: `last_marked DESC, date_entered DESC, updated DESC` |
| `-2` | Published | `published = true` (line 572). Order: `last_published DESC, date_entered DESC, updated DESC` |
| `-2` (cat_view) | Labels category | Joins `ttrss_labels2, ttrss_user_labels2` (line 583-586) |
| `-3` | Fresh | `unread = true AND score >= 0 AND date_entered > NOW() - INTERVAL '$intl hour'` where `$intl = FRESH_ARTICLE_MAX_AGE` pref (line 601-610) |
| `-4` | All Articles | `true` (no restriction) (line 613-616) |
| `-6` | Recently Read | `unread = false AND last_read IS NOT NULL`. Order: `last_read DESC` (line 589-595) |
| `0` (no cat_view) | Archive | `feed_id IS NULL` (line 554-555). `allow_archived = true` |
| `0` (cat_view) | Uncategorized | `cat_id IS NULL AND feed_id IS NOT NULL` (line 557-558) |
| `<= LABEL_BASE_INDEX` | Labels | `label_id = feed_to_label_id($feed)` with `ttrss_labels2, ttrss_user_labels2` join (line 617-626) |

### Feed-specific (feed > 0)

- No cat_view: `feed_id = '$feed'` (line 552)
- Cat_view with children: `cat_id IN ($subcats)` (line 538-539)
- Cat_view without children: `cat_id = '$feed'` (line 542)

---

## 9. Label System

**Source:** `include/labels.php`, `include/functions2.php:2400-2406`

### ID Conversion Formulas (functions2.php:2400-2406)

```python
def label_to_feed_id(label_id):
    return LABEL_BASE_INDEX - 1 - abs(label_id)
    # e.g., label_id=1 -> -1024 - 1 - 1 = -1026

def feed_to_label_id(feed_id):
    return LABEL_BASE_INDEX - 1 + abs(feed_id)
    # e.g., feed_id=-1026 -> -1024 - 1 + 1026 = 1
```

Label removal also uses this formula to compute the access key's feed_id: `ext_id = LABEL_BASE_INDEX - 1 - $id` (labels.php:162).

### Label Cache (labels.php:14-57)

Stored as JSON in `ttrss_user_entries.label_cache`.

Cache read flow:
1. Query `label_cache` from `ttrss_user_entries WHERE ref_id = '$id' AND owner_uid = $owner_uid`
2. If `label_cache` exists and is valid JSON:
   - If `{"no-labels": 1}` sentinel: return empty array
   - Otherwise: return decoded array (each element: `[feed_id, caption, fg_color, bg_color]`)
3. If cache miss: query `ttrss_labels2 JOIN ttrss_user_labels2`

Cache write (labels.php:84-97):
- If labels found: store as JSON array of `[feed_id, caption, fg_color, bg_color]`
- If no labels: store `{"no-labels": 1}` sentinel
- Cache is cleared (`label_cache = ''`) on any label add/remove operation

### Label Creation (labels.php:177-198)

- Duplicate check: `SELECT id FROM ttrss_labels2 WHERE caption = '$caption' AND owner_uid = $owner_uid`
- No-op if duplicate exists
- INSERT with optional `fg_color` and `bg_color`

---

## 10. Counter Cache

**Source:** `include/ccache.php`

### Cache Tables

- `ttrss_counters_cache` -- per-feed unread counts
- `ttrss_cat_counters_cache` -- per-category unread counts

### Validity Window (ccache.php:72-76)

```sql
-- PostgreSQL:
updated > NOW() - INTERVAL '15 minutes'
-- MySQL:
updated > DATE_SUB(NOW(), INTERVAL 15 MINUTE)
```

Note: The 15-minute validity check is defined but the current `ccache_find()` implementation returns the cached value regardless of age (the `$date_qpart` variable is constructed but not used in the SELECT query at line 78-80). The cache is updated on-demand when stale.

### Cache Update Logic (ccache.php:94-191)

**Feed counter** (`$is_cat = false`):
- Calls `getFeedArticles($feed_id, false, true, $owner_uid)` to get actual unread count
- Upserts into `ttrss_counters_cache`

**Category counter** (`$is_cat = true`):
- First recursively updates all child feed counters (unless `$pcat_fast`)
- Then: `SELECT SUM(value) FROM ttrss_counters_cache, ttrss_feeds WHERE id = feed_id AND cat_id = '$feed_id'`
- Category 0 (uncategorized): `cat_id IS NULL`

### Cascading Updates (ccache.php:169-188)

When a feed counter changes (`$prev_unread != $unread`):
- If `$update_pcat = true`: looks up feed's `cat_id` and calls `ccache_update($cat_id, $owner_uid, true, true, true)` (the `pcat_fast` flag avoids re-updating all child feeds)

### Label Trigger (ccache.php:110-113)

If `$feed_id < 0` (label): calls `ccache_update_all($owner_uid)` which updates ALL feed and category counters for the user.

### Triggers

Counter cache is updated after:
- Article purge (functions.php:284)
- Catchup operation (functions.php:1226)
- Feed update (implicitly via article insertion)
- Label changes (via `ccache_update_all`)

---

## 11. Session Validation

**Source:** `include/sessions.php:39-102`

### Validation Checks (in order, sessions.php:39-101)

1. **SINGLE_USER_MODE**: If true, session is always valid (line 40)
2. **Version match**: `VERSION_STATIC != $_SESSION["version"]` -> invalid (line 42)
3. **IP address check**: Based on `SESSION_CHECK_ADDRESS` setting (lines 44-63)
4. **Schema version**: `$_SESSION["ref_schema_version"] != session_get_schema_version(true)` -> invalid (line 65)
5. **User-Agent**: `sha1($_SERVER['HTTP_USER_AGENT']) != $_SESSION["user_agent"]` -> invalid (line 71)
6. **User exists**: Query `ttrss_users WHERE id = $_SESSION["uid"]`; if 0 rows -> invalid (line 77-86)
7. **Password hash**: `$pwd_hash != $_SESSION["pwd_hash"]` -> invalid (line 91)

### IP Matching Algorithm (sessions.php:46-57)

`SESSION_CHECK_ADDRESS` values:

| Value | Behavior | Example (IP: 192.168.1.100) |
|-------|----------|---------------------------|
| `0` | No IP check (`$check_ip = ''`) | -- |
| `1` | Match first 3 octets | `192.168.1.` |
| `2` | Match first 2 octets | `192.168.` |
| `3` | Exact IP match (default, full `$check_ip` used) | `192.168.1.100` |

Match check: `strpos($_SERVER['REMOTE_ADDR'], $check_ip) !== 0` (line 59).

### Session Storage (sessions.php:109-137)

- Read: `base64_decode()` of `data` column from `ttrss_sessions` (line 123)
- Write: `base64_encode($data)` before storing (line 131)
- Session name: `ttrss_sid` (or custom `TTRSS_SESSION_NAME`), with `_ssl` suffix for HTTPS (line 13-16)
- GC probability: 75% (line 20)
- Expiry: `max(SESSION_COOKIE_LIFETIME, 86400)` seconds (line 12)

---

## 12. PubSubHubbub

**Source:** `include/rssfuncs.php:494-540`

### State Machine

Stored in `ttrss_feeds.pubsub_state`:

| Value | State |
|-------|-------|
| `0` | Not subscribed (default) |
| `1` | Subscription pending |
| `2` | Active subscription |

### Subscription Flow (rssfuncs.php:494-540)

Triggered when `pubsub_state != 2` AND `PUBSUBHUBBUB_ENABLED` is true:

1. Extract hub URL from feed's `<link rel="hub">` (rssfuncs.php:500-506)
2. Extract self URL from feed's `<link rel="self">` (fallback: `$fetch_url`) (rssfuncs.php:511-520)
3. Prerequisites: `$feed_hub_url` AND `$feed_self_url` AND `curl_init` exists AND no `open_basedir` (rssfuncs.php:524-525)
4. Build callback URL (rssfuncs.php:529-530):
   ```
   {SELF_URL_PREFIX}/public.php?op=pubsub&id=$feed
   ```
5. Create subscriber and call `subscribe($feed_self_url)` via `lib/pubsubhubbub/subscriber.php` (rssfuncs.php:532-534)
6. Set `pubsub_state = 1` (pending) in DB (rssfuncs.php:538-539)

State transitions:
- `0 -> 1`: After subscribe request sent
- `1 -> 2`: Set by callback handler in `public.php` upon hub verification
- `2 -> 0`: Not implemented (no unsubscribe mechanism)

---

## 13. Feed Credential Encryption

**Source:** `include/crypt.php`

### Encryption (crypt.php:22-35)

```python
key = SHA256(FEED_CRYPT_KEY)   # raw binary output (32 bytes)
iv = random_bytes(16)          # MCRYPT_RIJNDAEL_128 block size
ciphertext = AES-128-CBC(key, iv, plaintext)  # PKCS padding implicit
output = base64(iv) + ":" + base64(ciphertext)
```

Algorithm: `MCRYPT_RIJNDAEL_128` with `MCRYPT_MODE_CBC` (AES-128-CBC).

Key derivation: `hash('SHA256', FEED_CRYPT_KEY, true)` -- raw binary SHA-256 of the config constant.

### Decryption (crypt.php:2-20)

```python
parts = input.split(":")
if len(parts) != 2: return False
iv = base64_decode(parts[0])
ciphertext = base64_decode(parts[1])
key = SHA256(FEED_CRYPT_KEY)  # raw binary
plaintext = AES-128-CBC-decrypt(key, iv, ciphertext)
return rtrim(plaintext)       # strip null padding
```

### Usage (rssfuncs.php:241-243)

Decryption is triggered when `ttrss_feeds.auth_pass_encrypted` is true. The `auth_pass` field contains the `base64(IV):base64(ciphertext)` string.

---

## 14. User Access Levels

**Source:** `backend.php:102-105`

### Level Map

| Level | Name | Description |
|-------|------|-------------|
| `0` | User | Default subscriber level (register.php:281) |
| `5` | Power User | No specific gates found in source -- intermediate level |
| `10` | Administrator | Full access |

### Admin Gates

All check `$_SESSION["access_level"] >= 10`:
- `classes/pref/system.php:7` -- System preferences
- `classes/pref/users.php:5` -- User management
- `classes/handler/public.php:892` -- OPML global import
- `prefs.php:130` -- Admin preferences tab
- `include/functions2.php:1000` -- Version update check

### SINGLE_USER_MODE

When enabled, access level is forced to 10 (functions.php:754): `$_SESSION["access_level"] = 10`.

---

## 15. Category Nesting

**Source:** `include/functions2.php:364-390`

### Data Model

`ttrss_feed_categories` table with self-referencing `parent_cat` column.

### Traversal Functions

**getParentCategories** (functions2.php:364-376):
```python
def getParentCategories(cat, owner_uid):
    rv = []
    rows = query("SELECT parent_cat FROM ttrss_feed_categories
                   WHERE id = '$cat' AND parent_cat IS NOT NULL AND owner_uid = $owner_uid")
    for row in rows:
        rv.append(row["parent_cat"])
        rv.extend(getParentCategories(row["parent_cat"], owner_uid))
    return rv
```

**getChildCategories** (functions2.php:378-390):
```python
def getChildCategories(cat, owner_uid):
    rv = []
    rows = query("SELECT id FROM ttrss_feed_categories
                   WHERE parent_cat = '$cat' AND owner_uid = $owner_uid")
    for row in rows:
        rv.append(row["id"])
        rv.extend(getChildCategories(row["id"], owner_uid))
    return rv
```

**No depth limit.** Recursive with no cycle detection. A circular reference in `parent_cat` would cause infinite recursion and stack overflow.

---

## 16. Edge Cases

### Feed Redirect (functions.php:352-399)

cURL follows redirects (`CURLOPT_FOLLOWLOCATION = true`, `CURLOPT_MAXREDIRS = 20`) but `feed_url` in `ttrss_feeds` is **NOT updated** to the redirected URL. The `site_url` IS updated from feed metadata (rssfuncs.php:471-473).

### Invalid XML (rssfuncs.php:375-378)

Feed data is passed to `FeedParser` which uses SimplePie internally. Errors are captured via `$rss->error()` and `$rss->errors()` (rssfuncs.php:1128-1138). Error message is stored in `ttrss_feeds.last_error` (truncated to 245 chars).

Encoding normalization: gzip decompression attempted if cURL was not used (rssfuncs.php:305-309). Feed data is trimmed (rssfuncs.php:311).

### Plugin Storage (pluginhost.php:272)

```php
$this->storage[$line["name"]] = unserialize($line["content"]);
```

Uses PHP `unserialize()` with **no error handling** and no class allowlist. Corrupt or malicious serialized data will cause warnings/errors silently.

### Orphaned Entries

When a feed is deleted, `ttrss_user_entries` rows are removed (FK cascade), but `ttrss_entries` rows persist. They are only cleaned by `purge_orphans()` during periodic housekeeping (rssfuncs.php:1423), which runs:
```sql
DELETE FROM ttrss_entries
WHERE (SELECT COUNT(int_id) FROM ttrss_user_entries WHERE ref_id = id) = 0
```

### Race Condition in Feed Locking (rssfuncs.php:110-156)

The 10-minute stale lock check is a SELECT followed by a separate UPDATE. Between the two operations, another process can select the same feed. The pre-update bulk `SET last_update_started = NOW()` (rssfuncs.php:154) mitigates but does not eliminate the race.

### Timestamp Clamping (rssfuncs.php:570-571)

Article timestamps in the future or equal to -1 or falsy are clamped to `time()` (current time):
```php
if ($entry_timestamp == -1 || !$entry_timestamp || $entry_timestamp > time()) {
    $entry_timestamp = time();
}
```

---

## 17. Search

**Source:** `include/functions2.php:260-361, 1997-2028`

### Sphinx Integration (functions2.php:1997-2028)

Enabled when `SPHINX_ENABLED` constant is true.

Configuration:
- Server: `SPHINX_SERVER` (host:port pair)
- Index: `SPHINX_INDEX`
- Connect timeout: 1 second
- Field weights: `title=70`, `content=30`, `feed_title=20`
- Match mode: `SPH_MATCH_EXTENDED2`
- Ranking mode: `SPH_RANK_PROXIMITY_BM25`
- Limit: 1000 max matches, default 30 returned
- Filter: `owner_uid = $_SESSION['uid']`

Returns array of `ref_id` values, used as `WHERE ref_id IN ($ids)`.

### SQL Fallback Search (functions2.php:260-361)

Keyword parsing: `str_getcsv($search, " ")` -- CSV parser with space delimiter (supports quoted phrases).

**Prefix operators:**
- `-` prefix: NOT (negation)
- `@` prefix: Date search (converts to `SUBSTRING(updated,1,LENGTH('$k')) = '$k'`)

**Field-specific search commands** (colon syntax):

| Command | SQL generated |
|---------|--------------|
| `title:term` | `LOWER(ttrss_entries.title) LIKE '%term%'` |
| `author:term` | `LOWER(author) LIKE '%term%'` |
| `note:true` | `note IS NOT NULL AND note != ''` |
| `note:false` | `note IS NULL OR note = ''` |
| `note:term` | `LOWER(note) LIKE '%term%'` |
| `star:true` | `marked = true` |
| `star:false` | `marked = false` |
| `pub:true` | `published = true` |
| `pub:false` | `published = false` |
| (default) | `UPPER(ttrss_entries.title) LIKE UPPER('%$k%') OR UPPER(ttrss_entries.content) LIKE UPPER('%$k%')` |

All keywords are joined with `AND` (functions2.php:359).

---

## 18. Email Digest

**Source:** `include/digest.php`

### Trigger Conditions (digest.php:9-74)

User selection:
```sql
SELECT id, email FROM ttrss_users
WHERE email != ''
  AND (last_digest_sent IS NULL OR last_digest_sent < NOW() - INTERVAL '1 days')
```

Additional checks per user:
1. `DIGEST_ENABLE` pref must be true (digest.php:29)
2. Current time must be within 2 hours (7200 seconds) **after** `DIGEST_PREFERRED_TIME` pref (digest.php:33-34):
   ```python
   preferred_ts = strtotime(DIGEST_PREFERRED_TIME)  # e.g., "08:00"
   time() >= preferred_ts and time() - preferred_ts <= 7200
   ```

Processing limits: max 15 users per batch, max 1000 headlines per digest (digest.php:13-14).

### Content Selection (digest.php:107-128)

```sql
SELECT ttrss_entries.title, ttrss_feeds.title AS feed_title,
       COALESCE(ttrss_feed_categories.title, 'Uncategorized') AS cat_title,
       date_updated, ttrss_user_entries.ref_id, link, score, content,
       SUBSTRING(last_updated,1,19) AS last_updated
FROM ttrss_user_entries, ttrss_entries, ttrss_feeds
LEFT JOIN ttrss_feed_categories ON (cat_id = ttrss_feed_categories.id)
WHERE ref_id = ttrss_entries.id
  AND feed_id = ttrss_feeds.id
  AND include_in_digest = true
  AND date_updated > NOW() - INTERVAL '$days days'
  AND owner_uid = $user_id
  AND unread = true
  AND score >= 0
ORDER BY ttrss_feed_categories.title, ttrss_feeds.title, score DESC, date_updated DESC
LIMIT $limit
```

Key filters: `include_in_digest = true`, `unread = true`, `score >= 0`.

### Templates (digest.php:87-88)

- HTML: `templates/digest_template_html.txt`
- Plain text: `templates/digest_template.txt`

Template variables: `CUR_DATE`, `CUR_TIME`, `FEED_TITLE`, `ARTICLE_TITLE`, `ARTICLE_LINK`, `ARTICLE_UPDATED`, `ARTICLE_EXCERPT` (300-char truncated, tags stripped).

### Auto-catchup (digest.php:38, 61-63)

If `DIGEST_CATCHUP` pref is true AND email sent successfully: `catchupArticlesById($affected_ids, 0, $line["id"])` marks all digest articles as read.

### Post-send (digest.php:69-70)

```sql
UPDATE ttrss_users SET last_digest_sent = NOW() WHERE id = {user_id}
```

---

## 19. OPML Import/Export

**Source:** `classes/opml.php`

### Export (opml.php:108-249)

Structure:
```xml
<opml version="1.0">
  <head><dateCreated>...</dateCreated><title>Tiny Tiny RSS Feed Export</title></head>
  <body>
    <!-- Feed outlines, recursively by category -->
    <outline text="tt-rss-prefs" schema-version="{SCHEMA_VERSION}">
      <outline pref-name="..." value="..."/>
    </outline>
    <outline text="tt-rss-labels" schema-version="{SCHEMA_VERSION}">
      <outline label-name="..." label-fg-color="..." label-bg-color="..."/>
    </outline>
    <outline text="tt-rss-filters" schema-version="{SCHEMA_VERSION}">
      <outline filter-type="2"><![CDATA[{json}]]></outline>
    </outline>
  </body>
</opml>
```

Settings/labels/filters only exported when `$include_settings = true` (opml.php:131).

Feed export: `<outline type="rss" text="$title" xmlUrl="$url" htmlUrl="$site_url"/>` (opml.php:100).

Private feed hiding: optional `$hide_private_feeds` flag excludes feeds where `private IS true OR auth_login != '' OR auth_pass != ''` (opml.php:61-64).

### Import (opml.php:254-399)

**Auto-created category**: `add_feed_category("Imported feeds")` called before import (opml.php:35).

**Feed duplicate detection** (opml.php:266-268):
```sql
SELECT id FROM ttrss_feeds
WHERE feed_url = '$feed_url' AND owner_uid = '$owner_uid'
```
If found: skip (report "Duplicate feed"). If not found: INSERT.

**Special sections** recognized by `text` attribute (opml.php:399):
- `tt-rss-prefs`: Imports user preferences via `set_pref()`
- `tt-rss-labels`: Imports labels via `label_create()` with dedup by `label_find_id()`
- `tt-rss-filters`: Imports filters as JSON (`filter-type="2"`), decodes and inserts into `ttrss_filters2`, `ttrss_filters2_rules`, `ttrss_filters2_actions`

**Category import** (opml.php:388-399): Recursively processes nested `<outline>` elements. Categories not matching special section names are treated as feed categories.

---

## 20. Registration

**Source:** `register.php`

### Fields (register.php:220-238)

- `login` -- desired username (lowercased, trimmed)
- `email` -- email address
- `turing_test` -- CAPTCHA answer to "How much is two plus two"

### CAPTCHA Validation (register.php:260)

```php
if ($test == "four" || $test == "4")
```

Only accepts the literal strings `"four"` or `"4"`.

### Registration Flow (register.php:260-341)

1. Validate CAPTCHA
2. Check username uniqueness: `SELECT id FROM ttrss_users WHERE login = '$login'`
3. Generate random password: `make_password()`
4. Generate salt: `substr(bin2hex(get_random_bytes(125)), 0, 250)` -- 250-char hex string
5. Hash password: `encrypt_password($password, $salt, true)` -> `"MODE2:" . hash('sha256', $salt . $pass)` (functions2.php:1483)
6. INSERT user:
   ```sql
   INSERT INTO ttrss_users (login, pwd_hash, access_level, last_login, email, created, salt)
   VALUES ('$login', '$pwd_hash', 0, null, '$email', NOW(), '$salt')
   ```
   - `access_level = 0` (subscriber)
   - `last_login = null`
7. Call `initialize_user($new_uid)` to set up default prefs
8. Email temporary password to user
9. Notify admin at `REG_NOTIFY_ADDRESS`

### Auto-cleanup (register.php:62-68)

Runs on every page load of register.php:
```sql
DELETE FROM ttrss_users
WHERE last_login IS NULL
  AND created < NOW() - INTERVAL '1 day'
  AND access_level = 0
```

Users who never logged in within 24 hours of account creation are automatically deleted.

### Registration Limits

- `ENABLE_REGISTRATION` must be true (register.php:192)
- `REG_MAX_USERS` if > 0: `COUNT(*) FROM ttrss_users` must be below limit (register.php:203-208)
