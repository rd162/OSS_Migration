# 03 — Frontend Spec

## Overview

TT-RSS uses a **server-rendered SPA hybrid** pattern:
- Server generates HTML fragments (headlines, dialogs, toolbars) in PHP
- Client manages DOM and widget state via JavaScript
- All communication through `backend.php` AJAX calls
- No client-side templating — HTML comes from server

## JavaScript Libraries

| Library | Version | Purpose | Source |
|---------|---------|---------|--------|
| **Prototype.js** | ~1.7 | DOM manipulation, Ajax, class system | `ttrss/lib/scriptaculous/` |
| **Scriptaculous** | — | Visual effects (limited use) | `ttrss/lib/scriptaculous/` |
| **Dojo Toolkit** | ~1.8 | Widgets (dijit), data stores, tree | `ttrss/lib/dojo/`, `ttrss/lib/dojo-src/` |
| **dijit** | ~1.8 | UI widgets (Dialog, Tree, form controls) | `ttrss/lib/dijit/` |

## JavaScript File Inventory

| File | Purpose | Key Functions |
|------|---------|---------------|
| `ttrss/js/tt-rss.js` | Main app init & state | `init()`, `init_second_stage()`, `updateFeedList()`, `setActiveFeedId()`, `viewCurrentFeed()` |
| `ttrss/js/viewfeed.js` | Article/headline display | `viewfeed()`, `headlines_callback2()`, `cdmExpandArticle()`, `view()`, `loadMoreHeadlines()` |
| `ttrss/js/feedlist.js` | Feed sidebar management | `feedlist_init()`, `updateFeedList()`, `request_counters()`, `catchupFeed()` |
| `ttrss/js/functions.js` | Global utilities | `displayDlg()`, `editFeed()`, `exception_error()`, `quickAddFeed()`, CSRF injection |
| `ttrss/js/prefs.js` | Preferences UI | `updateFeedList()`, `editUser()`, `editFilter()`, `editLabel()` |
| `ttrss/js/FeedTree.js` | Feed tree widget | `fox.FeedTree` extends `dijit.Tree` |
| `ttrss/js/PrefFeedTree.js` | Pref feed tree | `fox.PrefFeedStore` extends `ItemFileWriteStore` |
| `ttrss/js/PrefFilterTree.js` | Filter tree widget | Filter management tree |
| `ttrss/js/PrefLabelTree.js` | Label tree widget | Label management tree |
| `ttrss/js/PluginHost.js` | Client-side plugin host | Plugin JS method dispatch |
| `ttrss/js/deprecated.js` | Backward compat shims | Legacy function wrappers |

All paths relative to `source-repos/ttrss-php/`.

## AJAX Communication Pattern

### Basic RPC Call (Prototype.js)

```javascript
new Ajax.Request("backend.php", {
    parameters: "?op=rpc&method=mark&id=" + id + "&mark=1",
    onComplete: function(transport) {
        handle_rpc_json(transport);
    }
});
```

### Form Data Post (Dojo)

```javascript
dojo.xhrPost({
    url: "backend.php",
    content: {
        op: "pref-feeds",
        method: "editSave",
        id: feed_id,
        title: title
    }
});
```

### Dialog Loading

```javascript
var dialog = new dijit.Dialog({
    id: "feedEditDlg",
    title: "Edit Feed",
    href: "backend.php?op=pref-feeds&method=editfeed&id=" + id
});
dialog.show();
// Server returns HTML with dojoType attributes
// dojo.parser.parse() initializes embedded widgets
```

### Tree Data Store

```javascript
var store = new dojo.data.ItemFileWriteStore({
    url: "backend.php?op=pref_feeds&method=getfeedtree&mode=2"
});
var tree = new fox.FeedTree({
    model: new fox.FeedStoreModel({ store: store }),
    onClick: function(item) { /* handle click */ }
});
```

## CSRF Token Injection

All AJAX requests auto-inject CSRF token via Prototype.js wrapper:

```javascript
// In functions.js:
Ajax.Base.prototype.initialize = Ajax.Base.prototype.initialize.wrap(
    function(callOriginal, options) {
        if (getInitParam("csrf_token") != undefined) {
            options.parameters["csrf_token"] = getInitParam("csrf_token");
        }
        return callOriginal(options);
    }
);
```

## Frontend → Backend Call Map

| Frontend Action | JS Function | Backend Endpoint | Handler Method |
|----------------|-------------|-----------------|----------------|
| App init | `init()` | `rpc/sanityCheck` | RPC::sanitycheck |
| Load feed | `viewfeed(id)` | `feeds/view` | Feeds::view |
| View article | `view(id)` | `article/view` | Article::view |
| Star article | click handler | `rpc/mark` | RPC::mark |
| Publish article | click handler | `rpc/publ` | RPC::publ |
| Delete article | click handler | `rpc/delete` | RPC::delete |
| Mark feed read | `catchupFeed(id)` | `rpc/catchupFeed` | RPC::catchupFeed |
| Get counters | `request_counters()` | `rpc/getAllCounters` | RPC::getAllCounters |
| Edit feed | `editFeed(id)` | `pref-feeds/editfeed` | Pref_Feeds::editfeed |
| Save feed | dialog execute | `pref-feeds/editSave` | Pref_Feeds::editSave |
| Add feed | `quickAddFeed()` | `feeds/quickAddFeed` | Feeds::quickAddFeed |
| Edit tags | `editArticleTags(id)` | `article/editArticleTags` | Article::editArticleTags |
| Search | search form | `feeds/search` | Feeds::search |
| Edit filter | `editFilter(id)` | `pref-filters/edit` | Pref_Filters::edit |
| Edit label | label click | `pref-labels/edit` | Pref_Labels::edit |
| Preferences | prefs tab | `pref-prefs/index` | Pref_Prefs::index |
| User mgmt | admin panel | `pref-users/edit` | Pref_Users::edit |
| Feed tree | pref init | `pref-feeds/getfeedtree` | Pref_Feeds::getfeedtree |
| Infinite scroll | scroll handler | `feeds/view` (skip=N) | Feeds::view |

## Server-Side HTML Rendering

The backend renders HTML fragments that the frontend injects:

### Headlines (Feeds::format_headlines_list)
```php
// Server builds HTML rows:
$content .= "<div id='RROW-$id' class='$classes'>";
$content .= "  <div class='hlContent'>";
$content .= "    <a href='#'>" . htmlspecialchars($title) . "</a>";
$content .= "  </div>";
$content .= "</div>";
// Returns as JSON: {"headlines": {"content": "...HTML..."}}
```

### Dialog Content (various Pref_* handlers)
```php
// Server returns HTML with Dojo widget declarations:
// <input dojoType="dijit.form.TextBox" name="feed_url" value="...">
// Frontend calls dojo.parser.parse() to initialize widgets
```

## CSS Files

| File | Purpose |
|------|---------|
| `ttrss/css/tt-rss.css` | Main application styles |
| `ttrss/css/layout.css` | Page layout (panels, sidebars) |
| `ttrss/css/cdm.css` | Combined display mode styles |
| `ttrss/css/prefs.css` | Preferences panel styles |
| `ttrss/css/utility.css` | Utility classes |
| `ttrss/css/zoom.css` | Article zoom view |
| `ttrss/css/dijit.css` | Dojo widget overrides |

## Dijit Widgets Used

| Widget | Usage |
|--------|-------|
| `dijit.Dialog` | Modal dialogs (feed editor, filter editor, tag editor) |
| `dijit.Tree` | Feed tree in sidebar (extended as fox.FeedTree) |
| `dijit.form.TextBox` | Text inputs in forms |
| `dijit.form.CheckBox` | Boolean settings |
| `dijit.form.Select` | Dropdown selects |
| `dijit.form.Button` | Action buttons |
| `dijit.form.FilteringSelect` | Autocomplete selects |
| `dijit.layout.TabContainer` | Preference tabs |
| `dijit.layout.ContentPane` | Main content panels |
| `dijit.layout.BorderContainer` | Page layout (sidebar + content) |
| `dojo.data.ItemFileWriteStore` | Client-side data stores for trees |

## Custom Dojo Extensions

| Class | Extends | Purpose |
|-------|---------|---------|
| `fox.FeedTree` | `dijit.Tree` | Feed list with unread counts, drag-drop |
| `fox.FeedStoreModel` | `dijit.tree.ForestStoreModel` | Feed tree data model |
| `fox.PrefFeedStore` | `dojo.data.ItemFileWriteStore` | Preference feed data |
| `fox.PrefFilterStore` | `dojo.data.ItemFileWriteStore` | Filter tree data |
| `fox.PrefLabelStore` | `dojo.data.ItemFileWriteStore` | Label tree data |

## Keyboard Shortcuts (Hotkeys)

Defined via `HOOK_HOTKEY_MAP` / `HOOK_HOTKEY_INFO` plugin hooks.
Default hotkeys handled in `tt-rss.js` and `viewfeed.js`.

## Initialization Params

Server passes config to JS via `init_params` global variable:
- `csrf_token` — CSRF protection token
- `icons_url` — Feed icon base URL
- `label_base_index` — Label ID offset (-1024)
- `theme` — Current UI theme
- `num_feeds` — Feed count
- Various boolean flags for feature detection

## Python Migration Notes

- **Frontend strategy**: The frontend is the most complex migration decision
  - **Option A**: Keep existing JS frontend, build Python backend with identical JSON API
  - **Option B**: Rewrite frontend with modern framework (React, Vue, htmx)
  - **Option C**: Use htmx/HTMX for server-rendered approach (closest to current pattern)
- **Recommendation for Phase 1**: Option A (preserve frontend, migrate backend only)
  - This allows incremental migration and verifiable behavior parity
  - Frontend migration can be Phase 2
- **Server-rendered HTML**: Flask/Jinja2 or Django templates can produce identical HTML fragments
- **Dojo/Prototype**: Both libraries are legacy; eventual frontend rewrite is advisable
