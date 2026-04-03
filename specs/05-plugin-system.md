# 05 — Plugin System Spec

## Overview

TT-RSS implements a hook-based plugin architecture managed by a singleton `PluginHost`. Plugins extend the `Plugin` base class, register for hooks during initialization, and are invoked at specific lifecycle points throughout the application.

## Core Files

| File | Purpose |
|------|---------|
| `ttrss/classes/pluginhost.php` | Central plugin manager (singleton, ~400 lines) |
| `ttrss/classes/plugin.php` | Base plugin class |
| `ttrss/classes/pluginhandler.php` | HTTP request routing to plugin methods |
| `ttrss/classes/iauthmodule.php` | Authentication plugin interface |
| `ttrss/plugins/auth_internal/init.php` | Only built-in plugin |

All paths relative to `source-repos/ttrss-php/`.

## Hook Inventory (24 Hooks)

| ID | Constant | Trigger Location | Purpose |
|----|----------|-------------------|---------|
| 1 | `HOOK_ARTICLE_BUTTON` | feeds.php:723 | Add buttons to article UI |
| 2 | `HOOK_ARTICLE_FILTER` | rssfuncs.php:687 | Filter/modify articles during parsing |
| 3 | `HOOK_PREFS_TAB` | pref/*.php | Add preference tabs |
| 4 | `HOOK_PREFS_TAB_SECTION` | pref/*.php | Add sections within pref tabs |
| 5 | `HOOK_PREFS_TABS` | Reserved/unused |
| 6 | `HOOK_FEED_PARSED` | rssfuncs.php | Called when feed XML is parsed |
| 7 | `HOOK_UPDATE_TASK` | update.php:161,190 | Background update tasks |
| 8 | `HOOK_AUTH_USER` | functions.php:711 | User authentication |
| 9 | `HOOK_HOTKEY_MAP` | tt-rss.js | Define custom keyboard shortcuts |
| 10 | `HOOK_RENDER_ARTICLE` | feeds.php | Render article in normal view |
| 11 | `HOOK_RENDER_ARTICLE_CDM` | feeds.php:517 | Render article in combined mode |
| 12 | `HOOK_FEED_FETCHED` | rssfuncs.php:367 | After feed HTTP fetch |
| 13 | `HOOK_SANITIZE` | functions2.php | HTML content sanitization |
| 14 | `HOOK_RENDER_ARTICLE_API` | api.php:354,712 | Render for API responses |
| 15 | `HOOK_TOOLBAR_BUTTON` | index.php:213 | Main toolbar buttons |
| 16 | `HOOK_ACTION_ITEM` | index.php:252 | Action menu items |
| 17 | `HOOK_HEADLINE_TOOLBAR_BUTTON` | feeds.php:138 | Headline toolbar |
| 18 | `HOOK_HOTKEY_INFO` | functions2.php:110 | Hotkey help text |
| 19 | `HOOK_ARTICLE_LEFT_BUTTON` | feeds.php:686 | Left-side article buttons |
| 20 | `HOOK_PREFS_EDIT_FEED` | pref/feeds.php:748 | Feed edit dialog |
| 21 | `HOOK_PREFS_SAVE_FEED` | pref/feeds.php:981 | Feed save action |
| 22 | `HOOK_FETCH_FEED` | rssfuncs.php:270 | Custom feed fetching |
| 23 | `HOOK_QUERY_HEADLINES` | Multiple locations | Modify headline SQL queries |
| 24 | `HOOK_HOUSE_KEEPING` | handler/public.php:415 | Maintenance tasks |

## Plugin Lifecycle

### 1. Discovery
- Plugins located in `plugins/{PluginName}/init.php`
- Directory must contain `init.php` with class extending `Plugin`

### 2. Loading (three contexts)

```php
// System startup — load all configured plugins
init_plugins();  // functions2.php
→ PluginHost::getInstance()->load(PLUGINS, PluginHost::KIND_ALL);

// User login — load per-user plugins
load_user_plugins($owner_uid);  // functions.php
→ PluginHost::getInstance()->load($plugins, PluginHost::KIND_USER, $owner_uid);
→ PluginHost::getInstance()->load_data();  // Load stored config

// Feed update daemon — per-user context
// rssfuncs.php
→ $pluginhost->load(PLUGINS, PluginHost::KIND_ALL);
→ $pluginhost->load($user_plugins, PluginHost::KIND_USER, $owner_uid);
→ $pluginhost->load_data();
```

### 3. Initialization
Each plugin's `init($host)` method is called, where it registers hooks:

```php
class Auth_Internal extends Plugin implements IAuthModule {
    function init($host) {
        $host->add_hook($host::HOOK_AUTH_USER, $this);
    }
}
```

### 4. Hook Execution (two patterns)

```php
// Pattern 1: run_hooks() — fire and forget
PluginHost::getInstance()->run_hooks($type, $method, $args);

// Pattern 2: get_hooks() — direct iteration with return values
foreach (PluginHost::getInstance()->get_hooks($type) as $hook) {
    $result = $hook->hookMethodName($data);
}
```

## Plugin Classification

| Kind | Constant | Capabilities |
|------|----------|-------------|
| System | `KIND_SYSTEM` | Hooks + handlers + CLI commands + API methods |
| User | `KIND_USER` | Hooks only |
| All | `KIND_ALL` | Load both types |

### System Plugin Extras

```php
// Register custom HTTP handler
$host->add_handler($handler, $method, $sender);

// Register CLI command
$host->add_command($command, $description, $sender, $suffix, $arghelp);

// Register API method
$host->add_api_method($name, $sender);

// Register virtual feed
$host->add_feed($cat_id, $title, $icon, $sender);
```

## Plugin Configuration Storage

- **Table**: `ttrss_plugin_storage` (id, owner_uid, name, content)
- **Storage format**: Serialized PHP arrays
- **Per-plugin, per-user** isolation

```php
// Store data
$host->set($sender, $name, $value, $sync = true);

// Retrieve data
$host->get($sender, $name, $default = false);

// Get all plugin data
$host->get_all($sender);

// Clear all plugin data
$host->clear_data($sender);
```

Plugin identified by `get_class($sender)` — class name is the key.

## Plugin Base Class

```php
class Plugin {
    function init($host) {}                    // Called during loading
    function about() { return array(); }       // [version, name, description, author, is_system]
    function get_js() { return ""; }           // JavaScript to inject
    function get_prefs_js() { return ""; }     // Preferences JS to inject
    function api_version() { return 1; }       // Must return >= API_VERSION_COMPAT (1)
}
```

## Auth Plugin Interface (IAuthModule)

```php
interface IAuthModule {
    function authenticate($login, $password);
    // Returns user_id on success, false on failure
}
```

## PluginHost Singleton

```php
class PluginHost {
    const API_VERSION = 2;

    private static $instance;
    static function getInstance() { ... }

    // Hook management
    function add_hook($type, $sender) { ... }
    function del_hook($type, $sender) { ... }
    function get_hooks($type) { ... }
    function run_hooks($type, $method, $args) { ... }

    // Handler registration
    function add_handler($handler, $method, $sender) { ... }
    function lookup_handler($handler, $method) { ... }

    // Command registration
    function add_command($command, $description, $sender) { ... }
    function lookup_command($command) { ... }
    function run_commands($args) { ... }

    // Plugin query
    function get_plugin($name) { ... }
    function get_plugins() { ... }
    function get_plugin_names() { ... }
}
```

## Built-in Plugin: auth_internal

The only included plugin. Handles internal database authentication:
- Registered hook: `HOOK_AUTH_USER`
- Implements `IAuthModule` interface
- Handles password hashing (SHA1/SHA256 with salt)
- Supports OTP (TOTP two-factor auth)
- Marked as system plugin (`is_system = true`)

## PluginHandler HTTP Routing

`PluginHandler` (extends Handler_Protected) routes HTTP requests to plugin methods:

```
URL: backend.php?op=pluginhandler&plugin=MyPlugin&method=doSomething
→ Loads MyPlugin instance
→ Calls MyPlugin->doSomething()
```

## Python Migration Notes

- **Plugin system**: Python equivalent could use:
  - `pluggy` library (pytest-style hooks)
  - `stevedore` (OpenStack plugin loader)
  - Custom hook system with `importlib` and entry points
- **Hook pattern**: Maps well to Python signal/event systems (Django signals, blinker)
- **Plugin storage**: SQLAlchemy JSON column or dedicated table
- **Discovery**: Python namespace packages or `importlib.metadata` entry points
- **Configuration**: Replace PHP serialization with JSON
- **Priority**: Plugin system is a cross-cutting concern — design it early, migrate plugins last
