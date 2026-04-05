/**
 * TT-RSS Python — Vanilla-JS SPA (ADR-0017)
 * Visually faithful to the PHP TT-RSS Claro theme.
 *
 * Source: ttrss/js/app.js, ttrss/js/feedlist.js, ttrss/js/headlines.js
 *         ttrss/classes/api.php:API (protocol contract)
 * Adapted: PHP Dojo Toolkit frontend replaced by zero-dependency vanilla JS.
 *          Light cream/beige theme matching PHP claro skin.
 *          Hash routing #f=FEED_ID&c=CAT_ID matching PHP URL scheme.
 */

// ── Virtual feed definitions (order and icons matching PHP claro sidebar) ─────
// Source: ttrss/include/functions.php:getFeedTitle + ttrss/js/feedlist.js
const VFEEDS = [
  { id: -4, title: "All articles",      icon: "🗀",  cls: "vf-all"       },
  { id: -3, title: "Fresh articles",    icon: "⟳",  cls: "vf-fresh"     },
  { id: -1, title: "Starred articles",  icon: "★",  cls: "vf-starred"   },
  { id: -2, title: "Published articles",icon: "◎",  cls: "vf-published" },
  { id:  0, title: "Archived articles", icon: "☰",  cls: "vf-archived"  },
  { id: -6, title: "Recently read",     icon: "◷",  cls: "vf-recent"    },
];

// Source: ttrss/js/app.js — view mode constants
const VM = {
  ALL:       'all_articles',
  UNREAD:    'unread',
  STARRED:   'marked',
  PUBLISHED: 'published',
};

// ── State ─────────────────────────────────────────────────────────────────────
// Source: ttrss/js/app.js — global App object
const S = {
  view:         'login',
  seq:          1,
  user:         null,
  categories:   [],     // [{id, title, unread, order_id}]
  feeds:        [],     // [{id, title, unread, cat_id, has_icon, feed_url}]
  labels:       [],     // [{id, caption, fg_color, bg_color}]
  filters:      [],     // [{id, title, enabled, rules_summary}]
  catExpanded:  {},     // {cat_id: bool}  default: true
  selectedFeed: null,   // {id, title, unread}
  selectedCat:  null,
  headlines:    [],
  article:      null,
  modal:        null,   // null | 'subscribe' | 'settings'
  settingsTab:  'account', // 'account' | 'feeds' | 'categories' | 'filters' | 'opml'
  globalUnread: 0,
  loginError:   '',
  viewMode:     VM.ALL, // current headlines filter
  headlinesOffset: 0,
  headlinesEnd: false,
  loading:      false,
  subscribeUrl: '',
  subscribeStatus: '',
  actionsOpen:  false,
  // Tag editing state
  tagEditing:   false,
  tagInput:     '',
  opmlUrl:      '',
};

// ── API helper ────────────────────────────────────────────────────────────────
// Source: ttrss/api/index.php — all ops route through POST /api/
async function api(op, params = {}) {
  const resp = await fetch('/api/', {
    method:  'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ op, seq: S.seq++, ...params }),
  });
  const j = await resp.json();
  if (j.status !== 0) {
    const err = j.content?.error || 'UNKNOWN_ERROR';
    if (err === 'NOT_LOGGED_IN') { S.view = 'login'; render(); }
    throw Object.assign(new Error(err), { apiError: true });
  }
  return j.content;
}

// Backend RPC helper — POST /backend.php op=X method=Y (form-encoded)
// Source: ttrss/backend.php dispatch pattern
async function rpc(op, method, params = {}) {
  const fd = new FormData();
  fd.append('op', op);
  fd.append('method', method);
  for (const [k, v] of Object.entries(params)) fd.append(k, String(v));
  const resp = await fetch('/backend.php', { method: 'POST', credentials: 'include', body: fd });
  return resp.json();
}

// Prefs REST helper
async function prefsRequest(method, path, body = null) {
  const opts = { method, credentials: 'include' };
  if (body instanceof FormData) {
    opts.body = body;
  } else if (body) {
    opts.headers = { 'Content-Type': 'application/json' };
    opts.body = JSON.stringify(body);
  }
  const resp = await fetch('/prefs' + path, opts);
  if (!resp.ok && resp.status !== 200) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

// ── Hash routing ──────────────────────────────────────────────────────────────
// Source: ttrss/js/app.js — hash-based feed navigation (#f=FEED_ID&c=CAT_ID)
function writeHash(feedId, catId = 0) {
  const tag = `#f=${feedId}&c=${catId ?? 0}`;
  if (location.hash !== tag) history.replaceState(null, '', tag);
}

function readHash() {
  const m = location.hash.match(/[#&]f=(-?\d+)/);
  return m ? parseInt(m[1]) : null;
}

// ── Render dispatcher ─────────────────────────────────────────────────────────
function render() {
  const root = document.getElementById('app');
  if (!root) return;
  const sbScroll = document.querySelector('.feedlist')?.scrollTop || 0;
  const hlScroll = document.querySelector('.headlines-list')?.scrollTop || 0;
  root.innerHTML = S.view === 'login' ? renderLogin() : renderApp();
  bind();
  if (S.view === 'app') {
    const sb = document.querySelector('.feedlist');
    const hl = document.querySelector('.headlines-list');
    if (sb) sb.scrollTop = sbScroll;
    if (hl) hl.scrollTop = hlScroll;
    renderArticleContent();
  }
}
// Aliases kept for callers — all route to full render (simplest, most reliable)
const renderSidebarOnly = render;
const renderHLOnly      = render;
const renderArticleOnly = render;

// ── Login ─────────────────────────────────────────────────────────────────────
// Source: ttrss/include/login_form.php — login form
function renderLogin() {
  return `
  <div class="login-wrap">
    <form class="login-box" id="login-form" autocomplete="on">
      <div class="login-logo">
        <span class="logo-icon">📰</span>
        <span>Tiny Tiny RSS</span>
      </div>
      ${S.loginError ? `<div class="login-error">${esc(S.loginError)}</div>` : ''}
      <label class="login-label">Login</label>
      <input id="login-user" name="username" type="text"
             class="login-input" placeholder="" autocomplete="username" required>
      <label class="login-label">Password</label>
      <input id="login-pass" name="password" type="password"
             class="login-input" placeholder="" autocomplete="current-password" required>
      <div class="login-actions">
        <button class="login-btn" type="submit">Log in</button>
      </div>
    </form>
  </div>`;
}

async function doLogin(user, pass) {
  S.loginError = '';
  try {
    // Source: ttrss/classes/api.php:API.login (lines 49-88)
    await api('login', { user, password: pass });
    S.view = 'app';
    render();
    await Promise.all([loadSidebar(), loadGlobalUnread()]);
  } catch (e) {
    S.loginError = e.message === 'LOGIN_ERROR'  ? 'Incorrect username or password.' :
                   e.message === 'API_DISABLED'  ? 'API access is disabled for this user.' :
                   e.message;
    render();
  }
}

// ── App shell ─────────────────────────────────────────────────────────────────
// Source: ttrss/js/app.js — three-panel layout
function renderApp() {
  return `
  <div class="app-wrap">
    <div class="sidebar-col">
      ${renderToolbar()}
      <div class="feedlist">${renderFeedlist()}</div>
    </div>
    <div class="headlines-col">
      ${renderHeadlinesHeader()}
      <div class="headlines-list">${renderHeadlinesList()}</div>
    </div>
    <div class="article-col" id="article-col">
      ${renderArticlePlaceholder()}
    </div>
  </div>
  ${S.modal ? renderModal() : ''}`;
}

// ── Sidebar toolbar (top of sidebar, PHP-style) ───────────────────────────────
// Source: ttrss/js/app.js — sidebar header controls
function renderToolbar() {
  return `
  <div class="sidebar-toolbar">
    <span class="app-title" title="Tiny Tiny RSS">
      📰 <span>tt-rss</span>
    </span>
    <span class="toolbar-right">
      <button class="tb-btn" data-action="refresh" title="Refresh">⟳</button>
      <button class="tb-btn" data-action="subscribe" title="Subscribe to feed">+</button>
    </span>
  </div>`;
}

// ── Feedlist sidebar ──────────────────────────────────────────────────────────
// Source: ttrss/js/feedlist.js — feed tree rendering
//         ttrss/classes/handler/default.php:Handler_Default._generate_feedlist()
function renderFeedlist() {
  let html = '';

  // ── Special virtual feeds ──────────────────────────────────────────────────
  // Source: ttrss/js/feedlist.js — SPECIAL section always shown first
  html += `<div class="cat-header">Special</div>`;
  html += `<div class="cat-feeds special-feeds">`;
  for (const vf of VFEEDS) {
    const sel = S.selectedFeed?.id === vf.id;
    html += `<div class="feed-item ${sel ? 'selected' : ''} ${vf.cls}"
                  data-action="sel-feed" data-fid="${vf.id}" data-cat="-1">
      <span class="feed-icon">${vf.icon}</span>
      <span class="feed-name">${vf.title}</span>
    </div>`;
  }
  html += `</div>`;

  // ── Labels ─────────────────────────────────────────────────────────────────
  // Source: ttrss/js/feedlist.js — labels section (cat_id=-2)
  if (S.labels.length) {
    const labelFeeds = S.feeds.filter(f => f.cat_id === -2);
    const expanded = S.catExpanded['labels'] !== false;
    html += renderCatHeader('labels', 'Labels', null, expanded);
    if (expanded) {
      html += `<div class="cat-feeds">`;
      for (const lf of labelFeeds) {
        const sel = S.selectedFeed?.id === lf.id;
        html += `<div class="feed-item ${sel ? 'selected' : ''} ${lf.unread ? 'unread' : ''}"
                      data-action="sel-feed" data-fid="${lf.id}" data-cat="-2">
          <span class="feed-icon label-dot" style="color:${lf.fg_color||'#999'};background:${lf.bg_color||'transparent'}">●</span>
          <span class="feed-name">${esc(lf.title)}</span>
          ${lf.unread ? `<span class="badge">${lf.unread}</span>` : ''}
        </div>`;
      }
      html += `</div>`;
    }
  }

  // ── User categories + feeds ────────────────────────────────────────────────
  // Source: ttrss/js/feedlist.js — user feed categories
  const bycat = {};
  for (const f of S.feeds) {
    if (f.id <= 0 || f.cat_id === -2) continue; // skip virtual (id<=0) + label feeds
    const k = f.cat_id > 0 ? f.cat_id : '__uncat__';
    (bycat[k] = bycat[k] || []).push(f);
  }

  for (const cat of S.categories) {
    const catFeeds = bycat[cat.id] || [];
    const expanded = S.catExpanded[cat.id] !== false;
    html += renderCatHeader(cat.id, cat.title, cat.unread, expanded);
    if (expanded) {
      html += `<div class="cat-feeds">`;
      for (const f of catFeeds) {
        html += renderRealFeedItem(f);
      }
      html += `</div>`;
    }
  }

  // ── Uncategorized feeds ────────────────────────────────────────────────────
  // Source: ttrss/js/feedlist.js — uncategorized feeds shown last
  const uncatFeeds = bycat['__uncat__'] || [];
  if (uncatFeeds.length) {
    const expanded = S.catExpanded['__uncat__'] !== false;
    html += renderCatHeader('__uncat__', 'Uncategorized', null, expanded);
    if (expanded) {
      html += `<div class="cat-feeds">`;
      for (const f of uncatFeeds) {
        html += renderRealFeedItem(f);
      }
      html += `</div>`;
    }
  }

  if (!S.feeds.length && !S.categories.length) {
    html += `<div class="feedlist-empty">No feeds. Click + to subscribe.</div>`;
  }

  // ── Footer ─────────────────────────────────────────────────────────────────
  html += `<div class="feedlist-footer">
    <a class="fl-link" data-action="settings">Preferences</a> ·
    <a class="fl-link" data-action="logout">Log out</a>
    <span class="fl-unread">${S.globalUnread > 0 ? S.globalUnread + ' unread' : ''}</span>
  </div>`;

  return html;
}

function renderCatHeader(catKey, title, unread, expanded) {
  return `<div class="cat-row ${expanded ? 'open' : 'closed'}"
               data-action="toggle-cat" data-cat="${catKey}">
    <span class="cat-arrow">${expanded ? '▼' : '▶'}</span>
    <span class="cat-title-text">${esc(title)}</span>
    ${unread ? `<span class="badge">${unread}</span>` : ''}
  </div>`;
}

function renderRealFeedItem(f) {
  const sel = S.selectedFeed?.id === f.id;
  return `<div class="feed-item ${sel ? 'selected' : ''} ${f.unread ? 'unread' : ''}"
               data-action="sel-feed" data-fid="${f.id}" data-cat="${f.cat_id || 0}">
    <span class="feed-icon feed-icon-real">◈</span>
    <span class="feed-name">${esc(f.title)}</span>
    ${f.unread ? `<span class="badge">${f.unread}</span>` : ''}
  </div>`;
}

// ── Headlines header (filter bar matching PHP) ────────────────────────────────
// Source: ttrss/js/headlines.js — filter/toolbar above article list
//         ttrss/classes/api.php — view_mode parameter
function renderHeadlinesHeader() {
  const feedTitle = S.selectedFeed?.title || 'No feed selected';
  const vm = S.viewMode;
  const vmLink = (mode, label) =>
    `<a class="vm-link ${vm === mode ? 'active' : ''}" data-action="set-vm" data-vm="${mode}">${label}</a>`;

  return `
  <div class="headlines-header">
    <div class="hh-left">
      <span class="hh-feed-title">${esc(feedTitle)}</span>
    </div>
    <div class="hh-right">
      <span class="hh-viewmodes">
        ${vmLink(VM.ALL, 'All')},
        ${vmLink(VM.UNREAD, 'Unread')},
        ${vmLink(VM.STARRED, 'Starred')},
        ${vmLink(VM.PUBLISHED, 'Published')}
      </span>
      <span class="hh-sep">|</span>
      <button class="hh-btn" data-action="catchup" title="Mark all as read">Mark as read</button>
      <span class="hh-sep">|</span>
      <div class="hh-actions-wrap">
        <button class="hh-btn" data-action="toggle-actions">Actions ▾</button>
        ${S.actionsOpen ? renderActionsMenu() : ''}
      </div>
    </div>
  </div>`;
}

function renderActionsMenu() {
  return `<div class="actions-menu">
    <div class="am-item" data-action="reload-feed">Refresh feed</div>
    <div class="am-item" data-action="subscribe">Subscribe to feed…</div>
    <div class="am-item" data-action="unsubscribe-current">Unsubscribe</div>
  </div>`;
}

// ── Headlines list ────────────────────────────────────────────────────────────
// Source: ttrss/js/headlines.js — article list rendering
function renderHeadlinesList() {
  if (!S.selectedFeed) {
    return `<div class="hl-empty">No feed selected.</div>`;
  }
  if (S.loading && !S.headlines.length) {
    return `<div class="hl-empty">Loading…</div>`;
  }
  if (!S.headlines.length) {
    return `<div class="hl-empty">No articles found to display.</div>`;
  }

  const items = S.headlines.map(h => {
    const sel = S.article?.id === h.id;
    const date = h.updated ? fmtDate(h.updated * 1000) : '';
    const excerpt = h.excerpt ? `<div class="hl-excerpt">${esc(h.excerpt)}</div>` : '';
    return `<div class="hl-item ${sel ? 'selected' : ''} ${h.unread ? 'unread' : 'read'}"
                 data-action="open-article" data-id="${h.id}">
      <div class="hl-row">
        <span class="hl-marker ${h.unread ? 'unread-dot' : ''}">●</span>
        <span class="hl-title">${esc(h.title || '(no title)')}</span>
        ${h.marked ? `<span class="hl-star">★</span>` : ''}
        <span class="hl-date">${date}</span>
      </div>
      ${excerpt}
      <div class="hl-meta">
        ${h.feed_title && h.feed_title !== S.selectedFeed?.title ? `<span class="hl-feed">${esc(h.feed_title)}</span>` : ''}
        ${h.author ? `<span class="hl-author">${esc(h.author)}</span>` : ''}
      </div>
    </div>`;
  });

  const more = S.headlinesEnd
    ? `<div class="hl-end">— End of feed —</div>`
    : `<button class="hl-more-btn" data-action="load-more">Load more…</button>`;

  return items.join('') + more;
}

// ── Article reading pane ──────────────────────────────────────────────────────
// Source: ttrss/js/article.js — article content rendering
function renderArticlePlaceholder() {
  if (!S.article) return `<div class="article-empty">← Select an article to read</div>`;
  return `<div id="article-inner"></div>`;
}

function renderArticleContent() {
  const col = document.getElementById('article-col');
  if (!col || !S.article) return;
  const a = S.article;
  const date = a.updated ? new Date(a.updated * 1000).toLocaleString() : '';
  const tags = Array.isArray(a.tags) ? a.tags : [];

  // Tags row — Source: ttrss/js/article.js + ttrss/classes/article.php:editArticleTags
  const tagsHtml = `
    <div class="ah-tags" id="ah-tags">
      ${tags.map(t => `<span class="tag-chip" data-action="del-tag" data-tag="${esc(t)}" title="Remove tag">${esc(t)} ✕</span>`).join('')}
      ${S.tagEditing
        ? `<input id="tag-input" class="tag-input" placeholder="tag1, tag2…" value="${esc(S.tagInput)}" autofocus>`
        : `<button class="tag-add-btn" data-action="start-tag-edit" title="Add tags">(+)</button>`
      }
    </div>`;

  // Source: ttrss/js/article.js — sandboxed iframe for XSS isolation (R08)
  // Use contentDocument.write() instead of srcdoc: avoids attribute-encoding issues
  // with large/complex HTML and is more reliable across browsers.
  col.innerHTML = `
    <div class="article-header">
      <div class="ah-title-row">
        <button class="ah-btn ${a.marked ? 'ah-star-on' : ''}" data-action="tog-star" data-id="${a.id}" title="${a.marked ? 'Unstar' : 'Star'}">★</button>
        <button class="ah-btn ${a.published ? 'ah-pub-on' : ''}" data-action="tog-pub" data-id="${a.id}" title="${a.published ? 'Unpublish' : 'Publish'}">◎</button>
        <button class="ah-btn ah-unread-btn" data-action="mark-unread" data-id="${a.id}" title="Mark as unread">●</button>
        <h1 class="ah-title"><a href="${esc(a.link||'#')}" target="_blank" rel="noopener">${esc(a.title||'(no title)')}</a></h1>
      </div>
      <div class="ah-meta">
        ${a.author ? `<span class="ah-author">${esc(a.author)}</span>` : ''}
        ${date ? `<span class="ah-date">${date}</span>` : ''}
        ${a.feed_title ? `<span class="ah-feed">${esc(a.feed_title)}</span>` : ''}
        <a class="ah-link" href="${esc(a.link||'#')}" target="_blank" rel="noopener">Open original ↗</a>
      </div>
      ${tagsHtml}
    </div>
    <iframe class="article-frame" id="article-iframe"
            sandbox="allow-same-origin allow-popups"
            title="Article content"></iframe>`;

  // Write article content via contentDocument.write() — no escaping needed,
  // works for arbitrarily large content, sandbox still applies.
  const iframe = document.getElementById('article-iframe');
  if (iframe) {
    const iDoc = iframe.contentDocument || iframe.contentWindow?.document;
    if (iDoc) {
      iDoc.open();
      iDoc.write(`<!doctype html><html><head>
        <meta charset="utf-8">
        <style>
          body{font-family:Georgia,serif;font-size:15px;line-height:1.7;
               max-width:680px;margin:0 auto;padding:20px 24px;color:#222;background:#fff}
          a{color:#2563eb} img{max-width:100%;height:auto;border-radius:3px}
          pre,code{background:#f5f5f5;padding:2px 5px;border-radius:3px;font-size:13px}
          blockquote{border-left:3px solid #ccc;margin:0;padding-left:14px;color:#555}
          h1,h2,h3{color:#111;margin-top:1.4em}
        </style>
      </head><body>${a.content || '<p><em>No content available.</em></p>'}</body></html>`);
      iDoc.close();
    }
  }

  // Bind tag input events after rendering into article-col (outside #app)
  _bindArticleColEvents(col);
}

// Bind events inside article-col (rendered outside #app, so needs separate binding)
function _bindArticleColEvents(col) {
  // Tag input — save on Enter or blur
  const tagInput = col.querySelector('#tag-input');
  if (tagInput) {
    tagInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); doSaveTags(); }
      if (e.key === 'Escape') { S.tagEditing = false; S.tagInput = ''; renderArticleContent(); }
    });
    tagInput.addEventListener('blur', () => {
      // Small delay to allow click on save button
      setTimeout(() => { if (S.tagEditing) doSaveTags(); }, 200);
    });
    tagInput.addEventListener('input', e => { S.tagInput = e.target.value; });
  }

  // Delegated click for article-col actions
  col.addEventListener('click', e => {
    const el = e.target.closest('[data-action]');
    if (!el) return;
    const a = el.dataset.action;

    if (a === 'tog-star') {
      const id = parseInt(el.dataset.id);
      if (!S.article || S.article.id !== id) return;
      const starred = !S.article.marked;
      api('updateArticle', { article_ids: String(id), field: 0, mode: starred ? 1 : 0 })
        .then(() => {
          S.article.marked = starred;
          const h = S.headlines.find(x => x.id === id);
          if (h) h.marked = starred;
          renderArticleContent();
          renderHLOnly();
        }).catch(console.error);
    }
    else if (a === 'tog-pub') {
      // Source: ttrss/classes/api.php:updateArticle field=1 (PUBLISHED)
      const id = parseInt(el.dataset.id);
      if (!S.article || S.article.id !== id) return;
      const pub = !S.article.published;
      api('updateArticle', { article_ids: String(id), field: 1, mode: pub ? 1 : 0 })
        .then(() => {
          S.article.published = pub;
          renderArticleContent();
        }).catch(console.error);
    }
    else if (a === 'mark-unread') {
      // Source: ttrss/classes/api.php:updateArticle field=2 (UNREAD) mode=1
      const id = parseInt(el.dataset.id);
      if (!S.article || S.article.id !== id) return;
      api('updateArticle', { article_ids: String(id), field: 2, mode: 1 })
        .then(() => {
          S.article.unread = true;
          const h = S.headlines.find(x => x.id === id);
          if (h) { h.unread = true; }
          S.globalUnread += 1;
          renderHLOnly();
          renderArticleContent();
        }).catch(console.error);
    }
    else if (a === 'start-tag-edit') {
      S.tagEditing = true;
      S.tagInput = (S.article?.tags || []).join(', ');
      renderArticleContent();
    }
    else if (a === 'del-tag') {
      const tag = el.dataset.tag;
      if (!S.article) return;
      const newTags = (S.article.tags || []).filter(t => t !== tag);
      doSaveTagList(newTags);
    }
  });
}

async function doSaveTags() {
  const raw = S.tagInput.trim();
  const newTags = raw ? raw.split(',').map(t => t.trim()).filter(Boolean) : [];
  await doSaveTagList(newTags);
}

async function doSaveTagList(tags) {
  if (!S.article) return;
  const id = S.article.id;
  S.tagEditing = false;
  S.tagInput = '';
  try {
    // Source: ttrss/classes/article.php:Article::editArticleTags
    await rpc('article', 'settags', { id, tags: tags.join(',') });
    S.article.tags = tags;
    renderArticleContent();
  } catch (e) {
    alert('Error saving tags: ' + e.message);
  }
}

// ── Modals ────────────────────────────────────────────────────────────────────
function renderModal() {
  if (S.modal === 'subscribe') return renderSubscribeModal();
  if (S.modal === 'settings')  return renderSettingsModal();
  return '';
}

// Source: ttrss/js/prefs.js — subscribe dialog
function renderSubscribeModal() {
  return `
  <div class="modal-bg" id="modal-overlay">
    <div class="modal-dlg">
      <div class="modal-title">
        <span>Subscribe to feed</span>
        <button class="modal-close" data-action="close-modal">✕</button>
      </div>
      <div class="modal-body">
        <label>Feed URL or website address:</label>
        <input id="sub-url" type="url" class="modal-input"
               placeholder="https://example.com/feed.xml"
               value="${esc(S.subscribeUrl)}">
        ${S.subscribeStatus ? `<p class="sub-status">${esc(S.subscribeStatus)}</p>` : ''}
      </div>
      <div class="modal-btns">
        <button class="btn-ok" data-action="do-subscribe">Subscribe</button>
        <button class="btn-cancel modal-cancel" data-action="close-modal">Cancel</button>
      </div>
    </div>
  </div>`;
}

// Source: ttrss/js/prefs.js — preferences/settings dialog (ADR-0019: simplified modal pattern)
function renderSettingsModal() {
  const tab = S.settingsTab;
  const tabs = [
    ['account',    'Account'],
    ['feeds',      'Feeds'],
    ['categories', 'Categories'],
    ['filters',    'Filters'],
    ['opml',       'OPML'],
  ];

  return `
  <div class="modal-bg" id="modal-overlay">
    <div class="modal-dlg modal-wide">
      <div class="modal-title">
        <span>Preferences</span>
        <button class="modal-close" data-action="close-modal">✕</button>
      </div>
      <div class="modal-tabs">
        ${tabs.map(([t, label]) =>
          `<button class="modal-tab ${tab === t ? 'active' : ''}" data-action="settings-tab" data-tab="${t}">${label}</button>`
        ).join('')}
      </div>
      <div class="modal-body">
        ${tab === 'account'    ? renderSettingsAccount()    : ''}
        ${tab === 'feeds'      ? renderSettingsFeeds()      : ''}
        ${tab === 'categories' ? renderSettingsCategories() : ''}
        ${tab === 'filters'    ? renderSettingsFilters()    : ''}
        ${tab === 'opml'       ? renderSettingsOPML()       : ''}
      </div>
      <div class="modal-btns">
        <button class="btn-cancel" data-action="close-modal">Close</button>
      </div>
    </div>
  </div>`;
}

// ── Settings tabs ─────────────────────────────────────────────────────────────

function renderSettingsAccount() {
  return `
    <div class="pref-section">
      <h3>Account</h3>
      <p>Logged in as <strong>${esc(S.user||'')}</strong></p>
    </div>
    <div class="pref-section">
      <h3>Feed Update Interval</h3>
      <p>Default update interval for new feeds:</p>
      <div class="pref-row">
        <select id="update-interval-sel" class="pref-select">
          <option value="15">15 minutes</option>
          <option value="30" selected>30 minutes</option>
          <option value="60">60 minutes</option>
          <option value="120">2 hours</option>
          <option value="0">Disabled</option>
        </select>
        <button class="btn-ok" data-action="save-update-interval">Save</button>
      </div>
    </div>`;
}

function renderSettingsFeeds() {
  const realFeeds = S.feeds.filter(f => f.id > 0);
  // Build options for category select
  const catOptions = [
    `<option value="0">Uncategorized</option>`,
    ...S.categories.map(c => `<option value="${c.id}">${esc(c.title)}</option>`),
  ].join('');

  return `
    <div class="pref-section">
      <h3>Subscribed feeds (${realFeeds.length})</h3>
      ${realFeeds.length ? `
        <div class="feeds-mgr">
          ${realFeeds.map(f => `
            <div class="feed-mgr-row" data-fid="${f.id}">
              <span class="fmr-title">${esc(f.title)}</span>
              <select class="fmr-cat-sel pref-select-sm" data-action="assign-cat" data-fid="${f.id}">
                ${S.categories.map(c =>
                  `<option value="${c.id}" ${f.cat_id === c.id ? 'selected' : ''}>${esc(c.title)}</option>`
                ).join('')}
                <option value="0" ${!f.cat_id || f.cat_id <= 0 ? 'selected' : ''}>Uncategorized</option>
              </select>
              <button class="btn-danger-sm" data-action="unsub-feed" data-fid="${f.id}">Remove</button>
            </div>`).join('')}
        </div>` : `<p class="muted">No feeds subscribed yet.</p>`}
      <button class="btn-ok" style="margin-top:10px" data-action="subscribe">+ Subscribe to new feed</button>
    </div>`;
}

function renderSettingsCategories() {
  return `
    <div class="pref-section">
      <h3>Categories</h3>
      ${S.categories.length ? `
        <div class="cat-mgr">
          ${S.categories.map(c => `
            <div class="cat-mgr-row">
              <span class="cat-mgr-title">${esc(c.title)}</span>
              <button class="btn-danger-sm" data-action="del-cat" data-cat-id="${c.id}" title="Delete category">✕</button>
            </div>`).join('')}
        </div>` : `<p class="muted">No categories yet.</p>`}
      <div class="add-cat-form">
        <input id="new-cat-title" class="modal-input-sm" placeholder="New category name…" type="text">
        <button class="btn-ok" data-action="add-cat">Add category</button>
      </div>
    </div>`;
}

function renderSettingsFilters() {
  return `
    <div class="pref-section">
      <h3>Filters</h3>
      ${S.filters.length ? `
        <div class="filter-mgr">
          ${S.filters.map(f => `
            <div class="filter-mgr-row">
              <span class="filter-mgr-title ${f.enabled ? '' : 'filter-disabled'}">${esc(f.title || f.rules_summary || '(untitled)')}</span>
              <button class="btn-danger-sm" data-action="del-filter" data-filter-id="${f.id}" title="Delete filter">✕</button>
            </div>`).join('')}
        </div>` : `<p class="muted">No filters yet.</p>`}
    </div>
    <div class="pref-section">
      <h3>Create filter</h3>
      <div class="filter-form">
        <div class="filter-form-row">
          <label>Match type:</label>
          <select id="filter-type" class="pref-select-sm">
            <option value="1">Title</option>
            <option value="4">Content</option>
            <option value="8">Title or Content</option>
            <option value="2">Link</option>
            <option value="3">Author</option>
          </select>
        </div>
        <div class="filter-form-row">
          <label>Pattern (regex):</label>
          <input id="filter-regexp" class="modal-input-sm" placeholder="e.g. Google|Apple" type="text">
        </div>
        <div class="filter-form-row">
          <label>Action:</label>
          <select id="filter-action" class="pref-select-sm">
            <option value="7">Add tag</option>
            <option value="4">Mark as read</option>
            <option value="6">Delete article</option>
            <option value="5">Publish article</option>
          </select>
        </div>
        <div class="filter-form-row" id="filter-param-row">
          <label>Tag name:</label>
          <input id="filter-param" class="modal-input-sm" placeholder="tag name" type="text">
        </div>
        <button class="btn-ok" data-action="create-filter">Create filter</button>
        <span class="filter-status" id="filter-status"></span>
      </div>
    </div>`;
}

function renderSettingsOPML() {
  return `
    <div class="pref-section">
      <h3>Export OPML</h3>
      <p>Download all your feed subscriptions as an OPML file.</p>
      <button class="btn-ok" data-action="opml-export">Export OPML…</button>
      ${S.opmlUrl ? `<p class="muted" style="margin-top:6px">
        <a href="${esc(S.opmlUrl)}" target="_blank">Download link</a> (copy and save)
      </p>` : ''}
    </div>
    <div class="pref-section">
      <h3>Import OPML</h3>
      <p>Import feed subscriptions from an OPML file.</p>
      <div class="opml-import-form">
        <input id="opml-file" type="file" accept=".opml,.xml" class="opml-file-input">
        <button class="btn-ok" data-action="opml-import">Import</button>
        <span class="filter-status" id="opml-status"></span>
      </div>
    </div>`;
}

// ── Data loaders ──────────────────────────────────────────────────────────────
async function loadSidebar() {
  try {
    // Source: ttrss/classes/api.php:getCategories + getFeeds
    const [cats, feeds, labels] = await Promise.all([
      api('getCategories', { include_empty: true }),
      api('getFeeds', { cat_id: -4, include_nested: false }),
      api('getLabels'),
    ]);
    S.categories = (cats || []).filter(c => c.id > 0).sort((a,b) => (a.order_id||0)-(b.order_id||0));
    S.feeds      = feeds  || [];
    S.labels     = labels || [];
    renderSidebarOnly();  // only sidebar changed, don't rebuild headlines/article
  } catch (e) {
    console.error('loadSidebar', e);
  }
}

async function loadGlobalUnread() {
  try {
    // Source: ttrss/include/functions.php:getGlobalUnread
    const r = await api('getUnread');
    S.globalUnread = parseInt(r.unread) || 0;
    const badge = document.querySelector('.fl-unread');
    if (badge) badge.textContent = S.globalUnread > 0 ? S.globalUnread + ' unread' : '';
  } catch (_) {}
}

async function loadFilters() {
  try {
    const data = await prefsRequest('GET', '/filters');
    S.filters = data.filters || [];
  } catch (_) {
    S.filters = [];
  }
}

async function loadHeadlines(feedId, reset = true) {
  if (reset) {
    S.headlines = [];
    S.headlinesOffset = 0;
    S.headlinesEnd = false;
    S.article = null;
  }
  S.loading = true;
  renderHLOnly();   // show loading state in headlines panel only
  try {
    const LIMIT = 30;
    // Source: ttrss/classes/api.php:API.getHeadlines
    const items = await api('getHeadlines', {
      feed_id:        feedId,
      limit:          LIMIT,
      offset:         S.headlinesOffset,
      show_content:   false,
      view_mode:      S.viewMode,
      order_by:       'date_reverse',
      include_attachments: false,
    });
    const hs = items || [];
    S.headlines      = reset ? hs : [...S.headlines, ...hs];
    S.headlinesOffset += hs.length;
    S.headlinesEnd    = hs.length < LIMIT;
  } catch (e) {
    console.error('loadHeadlines', e);
  }
  S.loading = false;
  renderHLOnly();   // render results without touching sidebar or article
}

async function openArticle(id) {
  try {
    // Source: ttrss/classes/api.php:API.getArticle
    const items = await api('getArticle', { article_id: id });
    if (!items?.length) return;
    S.article = items[0];
    S.tagEditing = false;
    S.tagInput = '';
    renderArticleOnly();  // open article pane without rebuilding sidebar or list
    // Mark read — Source: api.php:updateArticle field=2 (UNREAD), mode=0
    if (S.article.unread) {
      api('updateArticle', { article_ids: String(id), field: 2, mode: 0 })
        .then(() => {
          const h = S.headlines.find(x => x.id === id);
          if (h) { h.unread = false; renderHLOnly(); }  // update unread dot only
          S.globalUnread = Math.max(0, S.globalUnread - 1);
          const badge = document.querySelector('.fl-unread');
          if (badge) badge.textContent = S.globalUnread > 0 ? S.globalUnread + ' unread' : '';
          if (S.selectedFeed) S.selectedFeed.unread = Math.max(0, (S.selectedFeed.unread||1)-1);
        }).catch(()=>{});
    }
  } catch (e) {
    console.error('openArticle', e);
  }
}

async function doSubscribe() {
  const url = document.getElementById('sub-url')?.value?.trim();
  if (!url) return;
  S.subscribeUrl = url;
  S.subscribeStatus = 'Subscribing…';
  render();
  try {
    // Source: ttrss/classes/api.php:API.subscribeToFeed
    const r   = await api('subscribeToFeed', { feed_url: url });
    const code = r?.status?.code ?? r?.code ?? -1;
    S.subscribeStatus = code === 1 ? '✓ Subscribed!' :
                        code === 0 ? 'Already subscribed.' :
                        `Done (code ${code}).`;
    S.subscribeUrl = '';
    await loadSidebar();
    await loadGlobalUnread();
  } catch (e) {
    S.subscribeStatus = 'Error: ' + e.message;
  }
  render();
}

// ── Settings action helpers ───────────────────────────────────────────────────

async function doAddCategory() {
  const input = document.getElementById('new-cat-title');
  const title = input?.value?.trim();
  if (!title) return;
  try {
    // Source: ttrss/classes/pref/feeds.php:Pref_Feeds::addCat
    const fd = new FormData();
    fd.append('cat', title);
    await fetch('/prefs/feeds/categories/add', { method: 'POST', credentials: 'include', body: fd });
    await loadSidebar();
    // Keep settings modal open on categories tab
    S.modal = 'settings';
    S.settingsTab = 'categories';
    render();
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

async function doDeleteCategory(catId) {
  if (!confirm('Delete this category? Feeds will move to Uncategorized.')) return;
  try {
    // Source: ttrss/classes/pref/feeds.php:Pref_Feeds::removeCat
    await fetch(`/prefs/feeds/categories/${catId}`, { method: 'DELETE', credentials: 'include' });
    await loadSidebar();
    S.modal = 'settings';
    S.settingsTab = 'categories';
    render();
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

async function doAssignFeedCategory(feedId, catId) {
  try {
    // Source: ttrss/classes/pref/feeds.php:Pref_Feeds::categorize_feeds
    const fd = new FormData();
    fd.append('feed_ids[]', feedId);
    fd.append('cat_id', catId);
    await fetch('/prefs/feeds/categorize', { method: 'POST', credentials: 'include', body: fd });
    // Update local feed cat_id immediately for responsive UI
    const f = S.feeds.find(x => x.id === feedId);
    if (f) f.cat_id = parseInt(catId) || null;
    await loadSidebar();
  } catch (e) {
    console.error('assign cat', e);
  }
}

async function doCreateFilter() {
  const regexp  = document.getElementById('filter-regexp')?.value?.trim();
  const ftype   = document.getElementById('filter-type')?.value || '1';
  const action  = document.getElementById('filter-action')?.value || '7';
  const param   = document.getElementById('filter-param')?.value?.trim() || '';
  const statusEl = document.getElementById('filter-status');

  if (!regexp) { if (statusEl) statusEl.textContent = 'Pattern required.'; return; }

  try {
    const fd = new FormData();
    fd.append('enabled', 'true');
    fd.append('match_any_rule', 'false');
    fd.append('inverse', 'false');
    // Rule JSON — Source: ttrss/classes/pref/filters.php:saveRulesAndActions
    fd.append('rule', JSON.stringify({ reg_exp: regexp, filter_type: parseInt(ftype), feed_id: '' }));
    // Action JSON
    fd.append('action', JSON.stringify({ action_id: parseInt(action), action_param: param }));

    await fetch('/prefs/filters', { method: 'POST', credentials: 'include', body: fd });
    if (statusEl) statusEl.textContent = '✓ Filter created.';
    await loadFilters();
    // Refresh filter list in the same tab
    const body = document.querySelector('.modal-body');
    if (body) body.innerHTML = renderSettingsFilters();
  } catch (e) {
    if (statusEl) statusEl.textContent = 'Error: ' + e.message;
  }
}

async function doDeleteFilter(filterId) {
  if (!confirm('Delete this filter?')) return;
  try {
    await fetch(`/prefs/filters/${filterId}`, { method: 'DELETE', credentials: 'include' });
    await loadFilters();
    const body = document.querySelector('.modal-body');
    if (body) body.innerHTML = renderSettingsFilters();
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

async function doOPMLExport() {
  try {
    // Source: ttrss/classes/dlg.php:Dlg::pubOPMLUrl
    const fd = new FormData();
    fd.append('op', 'dlg');
    fd.append('method', 'pubopmlurl');
    const resp = await fetch('/backend.php', { method: 'POST', credentials: 'include', body: fd });
    const data = await resp.json();
    if (data.url) {
      S.opmlUrl = data.url;
      window.open(data.url, '_blank');
      // Refresh OPML tab to show the URL
      const body = document.querySelector('.modal-body');
      if (body) body.innerHTML = renderSettingsOPML();
    }
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

async function doOPMLImport() {
  const fileInput = document.getElementById('opml-file');
  const statusEl = document.getElementById('opml-status');
  if (!fileInput?.files?.length) {
    if (statusEl) statusEl.textContent = 'Please select a file.';
    return;
  }
  const fd = new FormData();
  fd.append('op', 'dlg');
  fd.append('method', 'importopml');
  fd.append('opml_file', fileInput.files[0]);
  try {
    const resp = await fetch('/backend.php', { method: 'POST', credentials: 'include', body: fd });
    const data = await resp.json();
    if (data.status === 'OK') {
      if (statusEl) statusEl.textContent = `✓ Imported ${data.imported} feed(s).`;
      await loadSidebar();
    } else {
      if (statusEl) statusEl.textContent = 'Error: ' + (data.error || 'unknown');
    }
  } catch (e) {
    if (statusEl) statusEl.textContent = 'Error: ' + e.message;
  }
}

// ── Event binding ─────────────────────────────────────────────────────────────
// bind() is called once on full render. Delegated click handler on root covers
// all panels — partial updates to inner panels don't need re-binding.
let _rootBound = false;
function bind() {
  const root = document.getElementById('app');
  if (!root) return;

  // Login form
  root.querySelector('#login-form')?.addEventListener('submit', e => {
    e.preventDefault();
    const u = root.querySelector('#login-user')?.value?.trim();
    const p = root.querySelector('#login-pass')?.value;
    if (u && p) doLogin(u, p);
  });

  // Subscribe URL input
  root.querySelector('#sub-url')?.addEventListener('input', e => {
    S.subscribeUrl = e.target.value;
  });

  // Modal overlay background click
  root.querySelector('#modal-overlay')?.addEventListener('click', e => {
    if (e.target === e.currentTarget) { S.modal = null; S.subscribeStatus = ''; S.opmlUrl = ''; render(); }
  });

  // Filter action select → show/hide param row
  const filterActionSel = root.querySelector('#filter-action');
  if (filterActionSel) {
    const updateParamRow = () => {
      const paramRow = root.querySelector('#filter-param-row');
      const actionLabel = paramRow?.querySelector('label');
      if (!paramRow) return;
      const action = filterActionSel.value;
      // Only tag action needs a param
      paramRow.style.display = action === '7' ? '' : 'none';
    };
    filterActionSel.addEventListener('change', updateParamRow);
    updateParamRow();
  }

  // Delegated click handler — attach once; survives partial panel updates
  if (_rootBound) return;
  _rootBound = true;
  root.addEventListener('click', e => {
    const el = e.target.closest('[data-action]');
    if (!el) return;
    const a = el.dataset.action;

    if (a === 'logout') {
      api('logout').catch(()=>{}).finally(()=>{
        Object.assign(S, { view:'login', feeds:[], categories:[], headlines:[], article:null,
                           globalUnread:0, selectedFeed:null, labels:[], user:null,
                           filters:[], modal:null, opmlUrl:'' });
        _rootBound = false;
        render();
      });
    }
    else if (a === 'refresh') {
      loadSidebar(); loadGlobalUnread();
      if (S.selectedFeed) loadHeadlines(S.selectedFeed.id);
    }
    else if (a === 'subscribe') {
      S.modal = 'subscribe'; S.subscribeStatus = ''; S.actionsOpen = false; render();
    }
    else if (a === 'settings') {
      loadFilters().then(() => {
        S.modal = 'settings'; S.actionsOpen = false; render();
      });
    }
    else if (a === 'close-modal') {
      S.modal = null; S.subscribeStatus = ''; S.opmlUrl = ''; render();
    }
    else if (a === 'do-subscribe') {
      doSubscribe();
    }
    else if (a === 'settings-tab') {
      S.settingsTab = el.dataset.tab;
      render();
    }
    else if (a === 'unsub-feed') {
      const fid = parseInt(el.dataset.fid);
      api('unsubscribeFeed', { feed_id: fid })
        .then(() => {
          if (S.selectedFeed?.id === fid) { S.selectedFeed = null; S.headlines = []; S.article = null; }
          loadSidebar().then(() => { S.modal = 'settings'; S.settingsTab = 'feeds'; render(); });
        }).catch(e => alert('Unsubscribe failed: ' + e.message));
    }
    else if (a === 'unsubscribe-current') {
      S.actionsOpen = false;
      if (!S.selectedFeed || S.selectedFeed.id < 0) return render();
      if (!confirm(`Unsubscribe from "${S.selectedFeed.title}"?`)) return;
      api('unsubscribeFeed', { feed_id: S.selectedFeed.id })
        .then(() => {
          S.selectedFeed = null; S.headlines = []; S.article = null;
          loadSidebar();
        }).catch(e => alert('Error: ' + e.message));
    }
    else if (a === 'assign-cat') {
      // Handled by change event on select — skip click
    }
    else if (a === 'add-cat') {
      doAddCategory();
    }
    else if (a === 'del-cat') {
      doDeleteCategory(parseInt(el.dataset.catId));
    }
    else if (a === 'save-update-interval') {
      const sel = document.getElementById('update-interval-sel');
      if (sel) {
        // Source: ttrss/classes/rpc.php:RPC::setpref
        rpc('rpc', 'setpref', { key: 'DEFAULT_UPDATE_INTERVAL', value: sel.value })
          .catch(console.error);
      }
    }
    else if (a === 'create-filter') {
      doCreateFilter();
    }
    else if (a === 'del-filter') {
      doDeleteFilter(parseInt(el.dataset.filterId));
    }
    else if (a === 'opml-export') {
      doOPMLExport();
    }
    else if (a === 'opml-import') {
      doOPMLImport();
    }
    else if (a === 'toggle-cat') {
      const k = el.dataset.cat;
      S.catExpanded[k] = !(S.catExpanded[k] !== false);
      renderSidebarOnly();
    }
    else if (a === 'sel-feed') {
      const fid = parseInt(el.dataset.fid);
      const catId = el.dataset.cat;
      const vf = VFEEDS.find(v => v.id === fid);
      S.selectedFeed = vf
        ? { ...vf }
        : S.feeds.find(f => f.id === fid) || { id: fid, title: String(fid) };
      S.article = null;
      S.actionsOpen = false;
      writeHash(fid, catId);
      loadHeadlines(fid);
    }
    else if (a === 'reload-feed') {
      S.actionsOpen = false;
      if (S.selectedFeed) {
        // Force update then reload headlines
        if (S.selectedFeed.id > 0) {
          api('updateFeed', { feed_id: S.selectedFeed.id }).catch(()=>{});
        }
        loadHeadlines(S.selectedFeed.id);
      }
    }
    else if (a === 'catchup') {
      if (!S.selectedFeed) return;
      S.actionsOpen = false;
      // Source: ttrss/classes/api.php:API.catchupFeed
      api('catchupFeed', { feed_id: S.selectedFeed.id })
        .then(() => {
          S.headlines.forEach(h => h.unread = false);
          if (S.selectedFeed) S.selectedFeed.unread = 0;
          renderHLOnly(); renderSidebarOnly(); loadGlobalUnread();
        }).catch(e => alert('Error: ' + e.message));
    }
    else if (a === 'toggle-actions') {
      S.actionsOpen = !S.actionsOpen; renderHLOnly();
    }
    else if (a === 'set-vm') {
      S.viewMode = el.dataset.vm;
      if (S.selectedFeed) loadHeadlines(S.selectedFeed.id);
      else renderHLOnly();
    }
    else if (a === 'open-article') {
      openArticle(parseInt(el.dataset.id));
    }
    else if (a === 'load-more') {
      if (S.selectedFeed && !S.headlinesEnd) loadHeadlines(S.selectedFeed.id, false);
    }
  });

  // Category select change (assign feed to category) — delegated on root
  root.addEventListener('change', e => {
    const el = e.target;
    if (el.dataset.action === 'assign-cat') {
      const fid = parseInt(el.dataset.fid);
      const catId = parseInt(el.value) || 0;
      doAssignFeedCategory(fid, catId);
    }
  });
}

// Escape key closes modals / actions menu
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    if (S.tagEditing) { S.tagEditing = false; S.tagInput = ''; renderArticleContent(); }
    else if (S.modal) { S.modal = null; S.subscribeStatus = ''; S.opmlUrl = ''; render(); }
    else if (S.actionsOpen) { S.actionsOpen = false; render(); }
  }
});

// Hash change navigation
window.addEventListener('hashchange', () => {
  const fid = readHash();
  if (fid !== null && S.view === 'app') {
    const vf = VFEEDS.find(v => v.id === fid);
    const rf = S.feeds.find(f => f.id === fid);
    if (vf || rf) {
      S.selectedFeed = vf ? { ...vf } : { ...rf };
      S.article = null;
      loadHeadlines(fid);
    }
  }
});

// ── Utilities ─────────────────────────────────────────────────────────────────
function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/"/g,'&quot;');
}
function fmtDate(ms) {
  const d = new Date(ms);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' });
  }
  return d.toLocaleDateString([], { month:'short', day:'numeric' });
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────
// Source: ttrss/index.php — app entry point
(async () => {
  try {
    // Source: ttrss/classes/api.php:API.isLoggedIn
    const r = await api('isLoggedIn');
    if (r?.status === true) {
      S.view = 'app';
      render();
      const fid = readHash();
      await Promise.all([loadSidebar(), loadGlobalUnread()]);
      if (fid !== null) {
        const vf = VFEEDS.find(v => v.id === fid);
        if (vf) { S.selectedFeed = { ...vf }; loadHeadlines(fid); }
      }
    } else {
      render();
    }
  } catch (_) {
    render();
  }
})();
