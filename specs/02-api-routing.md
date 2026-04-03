# 02 — API & Request Routing Spec

## Entry Points

| Entry Point | Purpose | Auth Required |
|-------------|---------|---------------|
| `ttrss/index.php` | Web UI (HTML + JS bootstrap) | Yes |
| `ttrss/backend.php` | AJAX RPC dispatcher | Yes (most methods) |
| `ttrss/api/index.php` | REST API (JSON) | Yes (session or API key) |
| `ttrss/public.php` | Public feeds, login | No |
| `ttrss/opml.php` | OPML import/export | Yes |
| `ttrss/update.php` | CLI update tool | N/A (CLI) |
| `ttrss/update_daemon2.php` | Background daemon | N/A (process) |
| `ttrss/register.php` | User registration | No |
| `ttrss/image.php` | Cached image proxy | No |
| `ttrss/prefs.php` | Preferences UI | Yes |

All paths relative to `source-repos/ttrss-php/`.

## Backend.php Dispatch (Primary AJAX endpoint)

### Routing Logic

```
1. Read $op = $_REQUEST["op"]           → handler class name
2. Read $method = $_REQUEST["method"]   → handler method (fallback: $_REQUEST["subop"])
3. Convert hyphens: "pref-feeds" → "Pref_Feeds"
4. Check PluginHost for override: lookup_handler($op, $method)
5. Instantiate: new $op($_REQUEST)
6. Validate CSRF: unless handler->csrf_ignore($method) returns true
7. Execute: handler->before($method) → handler->$method() → handler->after()
8. Output: JSON (Content-Type: text/json), gzipped if ENABLE_GZIP_OUTPUT
```

### Handler → Method Mapping

| op | Class | Key Methods |
|----|-------|-------------|
| `rpc` | RPC | sanityCheck, mark, publ, delete, archive, getAllCounters, catchupSelected, catchupFeed, setpref, addfeed, quickAddCat |
| `feeds` | Feeds | view, catchupAll, search, quickAddFeed, feedBrowser |
| `article` | Article | view, redirect, editArticleTags, setArticleTags, setScore, assigntolabel, removefromlabel, completeTags |
| `pref-feeds` | Pref_Feeds | getfeedtree, editfeed, editSave, batchEditSave, remove, addCat, removeCat, rescore |
| `pref-filters` | Pref_Filters | edit, newfilter, save, remove, testFilter |
| `pref-labels` | Pref_Labels | edit, save, remove, colorset |
| `pref-prefs` | Pref_Prefs | index, saveconfig, changepassword, changeemail, editPrefProfiles |
| `pref-users` | Pref_Users | edit, save, remove, resetPass (admin only) |
| `pref-system` | Pref_System | index, clearLog |
| `dlg` | Dlg | Various dialog content methods |
| `opml` | Opml | import, export |
| `backend` | Backend | System operations |

### CSRF-Exempt Methods

| Handler | Exempt Methods |
|---------|---------------|
| RPC | sanitycheck, completelabels |
| Feeds | index, feedbrowser, quickaddfeed, search |
| Article | redirect, editarticletags |

## REST API (api/index.php)

### Authentication

```json
// Login request:
{"op": "login", "user": "admin", "password": "secret"}

// Login response:
{"seq": 0, "status": 0, "content": {"session_id": "abc123", "api_level": 8}}

// Authenticated request:
{"op": "getFeeds", "sid": "abc123", "cat_id": -3}
```

### API Level: 8

### Response Format

```json
{
    "seq": 0,           // Request sequence number
    "status": 0,        // 0 = OK, 1 = ERR
    "content": { ... }  // Method-specific payload
}
```

### API Methods

| Method | Purpose | Key Parameters |
|--------|---------|----------------|
| `login` | Authenticate | user, password |
| `logout` | End session | sid |
| `isLoggedIn` | Check session | sid |
| `getVersion` | App version | — |
| `getApiLevel` | API version (8) | — |
| `getUnread` | Total unread count | — |
| `getCounters` | All feed counters | output_mode |
| `getFeeds` | Feed list | cat_id, unread_only, limit, offset, include_nested |
| `getCategories` | Category list | unread_only, enable_nested, include_empty |
| `getHeadlines` | Article list | feed_id, limit, skip, filter, is_cat, show_excerpt, view_mode, since_id, order_by |
| `updateArticle` | Update article state | article_ids, mode, field, data |
| `getArticle` | Full article content | article_id |
| `getConfig` | System config | — |
| `updateFeed` | Trigger feed update | feed_id |
| `catchupFeed` | Mark feed read | feed_id, is_cat |
| `getLabels` | User labels | — |
| `setArticleLabel` | Add/remove label | article_ids, label_id, assign |
| `shareToPublished` | Publish article | title, url, content |
| `subscribeToFeed` | Add feed | feed_url, category_id, login, password |
| `unsubscribeFeed` | Remove feed | feed_id |
| `getFeedTree` | Full feed tree | include_empty |

## RPC Endpoints Detail

### Feeds::view (Main headline loading)

**Request**: `backend.php?op=feeds&method=view&feed=5&view_mode=adaptive&order_by=default&skip=0`

**Response**:
```json
{
    "headlines": {
        "id": 5,
        "is_cat": false,
        "content": "<div id='RROW-123' class='...'>...server-rendered HTML...</div>",
        "toolbar": "<div>...toolbar HTML...</div>"
    },
    "headlines-info": {
        "count": 30,
        "vgroup_last_feed": null,
        "disable_cache": false
    },
    "counters": [{"id": 5, "kind": "feed", "counter": 10, "error": "", "updated": "1h"}],
    "runtime-info": {"daemon_is_running": true, ...}
}
```

### RPC::getAllCounters

**Request**: `backend.php?op=rpc&method=getAllCounters&seq=5`

**Response**: Array of counter objects for all feeds/categories/labels/special feeds.

### RPC::mark / publ / delete / archive

**Request**: `backend.php?op=rpc&method=mark&id=123&mark=1`

**Response**: `{"message": "UPDATE_COUNTERS"}`

## Public Endpoints (Handler_Public)

Accessible without authentication:

| Method | Purpose |
|--------|---------|
| `globalUpdateFeeds` | Trigger feed update via HTTP |
| `rss` | Generate RSS/Atom feed for published/labeled articles |
| `getUnread` | Get unread count (with access key) |
| `getProfiles` | List user profiles |
| `share` | Share article to published |
| `fbexport` | Feed browser export |
| `logout` | Logout |
| `pubsub` | PubSubHubbub callback |

## Python Migration Notes

- **Recommended framework**: Flask (lightweight, matches TT-RSS simplicity) or FastAPI (modern, async)
- **Routing**: Flask blueprints map cleanly to handler classes
- **RPC pattern**: Could be preserved as-is or modernized to REST
- **API v2**: Consider OpenAPI spec generation
- **CSRF**: Use Flask-WTF or framework-native CSRF
- **Response format**: Preserve JSON contract for frontend compatibility during migration
