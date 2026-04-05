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
  feeds:        [],     // [{id, title, unread, cat_id, has_icon}]
  labels:       [],     // [{id, caption, fg_color, bg_color}]
  catExpanded:  {},     // {cat_id: bool}  default: true
  selectedFeed: null,   // {id, title, unread}
  selectedCat:  null,
  headlines:    [],
  article:      null,
  modal:        null,   // null | 'subscribe' | 'settings'
  globalUnread: 0,
  loginError:   '',
  viewMode:     VM.ALL, // current headlines filter
  headlinesOffset: 0,
  headlinesEnd: false,
  loading:      false,
  subscribeUrl: '',
  subscribeStatus: '',
  actionsOpen:  false,
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

  // Source: ttrss/js/article.js — sandboxed iframe for XSS isolation (R08)
  // Use contentDocument.write() instead of srcdoc: avoids attribute-encoding issues
  // with large/complex HTML and is more reliable across browsers.
  col.innerHTML = `
    <div class="article-header">
      <div class="ah-title-row">
        <button class="ah-btn ${a.marked ? 'ah-star-on' : ''}" data-action="tog-star" data-id="${a.id}" title="${a.marked ? 'Unstar' : 'Star'}">★</button>
        <h1 class="ah-title"><a href="${esc(a.link||'#')}" target="_blank" rel="noopener">${esc(a.title||'(no title)')}</a></h1>
      </div>
      <div class="ah-meta">
        ${a.author ? `<span class="ah-author">${esc(a.author)}</span>` : ''}
        ${date ? `<span class="ah-date">${date}</span>` : ''}
        ${a.feed_title ? `<span class="ah-feed">${esc(a.feed_title)}</span>` : ''}
        <a class="ah-link" href="${esc(a.link||'#')}" target="_blank" rel="noopener">Open original ↗</a>
      </div>
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

// Source: ttrss/js/prefs.js — preferences/settings dialog
function renderSettingsModal() {
  const realFeeds = S.feeds.filter(f => f.id > 0);
  return `
  <div class="modal-bg" id="modal-overlay">
    <div class="modal-dlg modal-wide">
      <div class="modal-title">
        <span>Preferences</span>
        <button class="modal-close" data-action="close-modal">✕</button>
      </div>
      <div class="modal-body">
        <div class="pref-section">
          <h3>Account</h3>
          <p>Logged in as <strong>${esc(S.user||'')}</strong></p>
        </div>
        <div class="pref-section">
          <h3>Subscribed feeds (${realFeeds.length})</h3>
          ${realFeeds.length ? `
            <div class="feeds-mgr">
              ${realFeeds.map(f => `
                <div class="feed-mgr-row">
                  <span class="fmr-title">${esc(f.title)}</span>
                  <span class="fmr-url">${esc(f.feed_url||'')}</span>
                  <button class="btn-danger-sm" data-action="unsub-feed" data-fid="${f.id}">Remove</button>
                </div>`).join('')}
            </div>` : `<p class="muted">No feeds subscribed yet.</p>`}
          <button class="btn-ok" style="margin-top:10px" data-action="subscribe">+ Subscribe to new feed</button>
        </div>
      </div>
      <div class="modal-btns">
        <button class="btn-cancel" data-action="close-modal">Close</button>
      </div>
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
    if (e.target === e.currentTarget) { S.modal = null; S.subscribeStatus = ''; render(); }
  });

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
                           globalUnread:0, selectedFeed:null, labels:[], user:null });
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
      S.modal = 'settings'; S.actionsOpen = false; render();
    }
    else if (a === 'close-modal') {
      S.modal = null; S.subscribeStatus = ''; render();
    }
    else if (a === 'do-subscribe') {
      doSubscribe();
    }
    else if (a === 'unsub-feed') {
      const fid = parseInt(el.dataset.fid);
      api('unsubscribeFeed', { feed_id: fid })
        .then(() => {
          if (S.selectedFeed?.id === fid) { S.selectedFeed = null; S.headlines = []; S.article = null; }
          loadSidebar();
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
      if (S.selectedFeed) loadHeadlines(S.selectedFeed.id);
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
    else if (a === 'tog-star') {
      const id = parseInt(el.dataset.id);
      if (!S.article || S.article.id !== id) return;
      const starred = !S.article.marked;
      // Source: ttrss/classes/api.php:updateArticle field=0 (MARKED)
      api('updateArticle', { article_ids: String(id), field: 0, mode: starred ? 1 : 0 })
        .then(() => {
          S.article.marked = starred;
          const h = S.headlines.find(x => x.id === id);
          if (h) h.marked = starred;
          renderArticleOnly();  // only update star button in article header
          renderHLOnly();       // update star indicator in headline list
        }).catch(console.error);
    }
  });
}

// Escape key closes modals / actions menu
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    if (S.modal)        { S.modal = null; S.subscribeStatus = ''; render(); }
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
