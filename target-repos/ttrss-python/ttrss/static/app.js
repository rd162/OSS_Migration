/**
 * TT-RSS Python — Vanilla-JS SPA (ADR-0017)
 *
 * Source: ttrss/js/app.js (top-level application bootstrap)
 *         ttrss/classes/api.php:API (protocol contract)
 * Adapted: PHP Dojo Toolkit frontend replaced by zero-dependency vanilla JS.
 *          State lives in a plain object; re-render is full innerHTML replacement.
 *          Article content is isolated in <iframe srcdoc> to prevent XSS (R08).
 * New: no PHP frontend equivalent; implements TT-RSS API level 8 client.
 */

// ── State ────────────────────────────────────────────────────────────────────
// Source: ttrss/js/app.js — global App object
const S = {
  view: 'login',       // 'login' | 'app'
  seq: 1,
  user: null,
  categories: [],      // [{id, title, unread}]
  feeds: [],           // [{id, title, unread, cat_id, has_icon}]
  catExpanded: {},     // {cat_id: bool}
  selectedFeed: null,  // feed object
  headlines: [],       // [{id, title, author, updated, unread, marked, feed_title}]
  article: null,       // full article object from getArticle
  modal: null,         // null | 'settings' | 'subscribe'
  globalUnread: 0,
  loginError: '',
  headlinesOffset: 0,
  headlinesEnd: false,
  loading: false,
  subscribeUrl: '',
  subscribeStatus: '',
};

// ── API helper ────────────────────────────────────────────────────────────────
// Source: ttrss/api/index.php — all ops route through POST /api/
async function api(op, params = {}) {
  const resp = await fetch('/api/', {
    method: 'POST',
    credentials: 'include',    // R08: HttpOnly session cookie sent automatically
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ op, seq: S.seq++, ...params }),
  });
  const j = await resp.json();
  if (j.status !== 0) {
    const err = j.content?.error || 'UNKNOWN_ERROR';
    if (err === 'NOT_LOGGED_IN') { S.view = 'login'; render(); }
    throw Object.assign(new Error(err), { apiError: true, op });
  }
  return j.content;
}

// ── Render dispatcher ─────────────────────────────────────────────────────────
function render() {
  const root = document.getElementById('app');
  if (!root) return;
  const sidebarScroll = document.querySelector('.sidebar')?.scrollTop || 0;
  const listScroll    = document.querySelector('.article-list')?.scrollTop || 0;
  root.innerHTML = S.view === 'login' ? renderLogin() : renderApp();
  bind();
  if (S.view === 'app') {
    const sb = document.querySelector('.sidebar');
    const al = document.querySelector('.article-list');
    if (sb) sb.scrollTop = sidebarScroll;
    if (al) al.scrollTop = listScroll;
    renderArticleContent();
  }
}

// ── Login ─────────────────────────────────────────────────────────────────────
// Source: ttrss/classes/handler/login.php:Handler_Login (login form rendering)
function renderLogin() {
  return `
  <div class="login-wrap">
    <div class="login-box">
      <div class="login-logo">🗞 Tiny Tiny RSS</div>
      ${S.loginError ? `<div class="login-error">${esc(S.loginError)}</div>` : ''}
      <form id="login-form" autocomplete="on">
        <input id="login-user" name="username" type="text"
               placeholder="Username" autocomplete="username" required>
        <input id="login-pass" name="password" type="password"
               placeholder="Password" autocomplete="current-password" required>
        <button type="submit">Sign in</button>
      </form>
    </div>
  </div>`;
}

async function doLogin(user, pass) {
  try {
    S.loginError = '';
    // Source: ttrss/classes/api.php:API.login (lines 49-88)
    await api('login', { user, password: pass });
    S.view = 'app';
    S.loginError = '';
    render();
    await loadSidebar();
    await loadGlobalUnread();
  } catch (e) {
    S.loginError = e.message === 'LOGIN_ERROR' ? 'Invalid username or password.'
                 : e.message === 'API_DISABLED' ? 'API access disabled for this account.'
                 : e.message;
    render();
  }
}

// ── App shell ─────────────────────────────────────────────────────────────────
function renderApp() {
  return `
  ${renderHeader()}
  <div class="layout">
    <div class="sidebar">${renderSidebar()}</div>
    <div class="article-list">${renderArticleList()}</div>
    <div class="reading-pane" id="reading-pane">${renderReadingPanePlaceholder()}</div>
  </div>
  ${S.modal ? renderModal() : ''}`;
}

// ── Header ────────────────────────────────────────────────────────────────────
// Source: ttrss/templates/header.html + ttrss/js/app.js (toolbar)
function renderHeader() {
  return `
  <header class="topbar">
    <div class="topbar-left">
      <span class="logo">🗞 Tiny Tiny RSS</span>
    </div>
    <div class="topbar-center">
      <button class="btn-icon" data-action="refresh" title="Refresh counters">⟳</button>
      <span class="unread-badge" title="Global unread">${S.globalUnread || ''}</span>
    </div>
    <div class="topbar-right">
      <button class="btn-text" data-action="subscribe">+ Subscribe</button>
      <button class="btn-icon" data-action="settings" title="Settings">⚙</button>
      <button class="btn-text" data-action="logout">Sign out</button>
    </div>
  </header>`;
}

// ── Sidebar ───────────────────────────────────────────────────────────────────
// Source: ttrss/js/feedlist.js (feed list component)
//         ttrss/classes/handler/default.php:Handler_Default._generate_feedlist()
function renderSidebar() {
  if (!S.categories.length && !S.feeds.length) {
    return `<div class="sidebar-empty">
      <p>No feeds yet.</p>
      <button class="btn-text" data-action="subscribe">+ Add feed</button>
    </div>`;
  }

  // Group feeds by cat_id
  const bycat = {};
  for (const f of S.feeds) {
    const k = f.cat_id ?? 0;
    (bycat[k] = bycat[k] || []).push(f);
  }

  // Render categories + uncategorized
  let html = '';

  // Special virtual categories first (All Articles -4, Fresh -3, Starred -1)
  const virtFeeds = S.feeds.filter(f => f.id < 0);
  if (virtFeeds.length) {
    html += `<div class="cat-group">
      <div class="cat-title special-cat">Special</div>
      ${virtFeeds.map(f => renderFeedItem(f)).join('')}
    </div>`;
  }

  // Real categories
  for (const cat of S.categories) {
    const catFeeds = bycat[cat.id] || [];
    const expanded = S.catExpanded[cat.id] !== false; // default open
    html += `<div class="cat-group">
      <div class="cat-title ${expanded ? 'expanded' : ''}"
           data-action="toggle-cat" data-cat="${cat.id}">
        <span class="cat-arrow">${expanded ? '▾' : '▸'}</span>
        ${esc(cat.title)}
        ${cat.unread ? `<span class="badge">${cat.unread}</span>` : ''}
      </div>
      ${expanded ? `<div class="cat-feeds">${catFeeds.map(f => renderFeedItem(f)).join('')}</div>` : ''}
    </div>`;
  }

  // Uncategorized feeds (cat_id = 0 or null)
  const uncatFeeds = (bycat[0] || []).filter(f => f.id > 0);
  if (uncatFeeds.length) {
    const expanded = S.catExpanded['uncat'] !== false;
    html += `<div class="cat-group">
      <div class="cat-title ${expanded ? 'expanded' : ''}"
           data-action="toggle-cat" data-cat="uncat">
        <span class="cat-arrow">${expanded ? '▾' : '▸'}</span>
        Uncategorized
      </div>
      ${expanded ? `<div class="cat-feeds">${uncatFeeds.map(f => renderFeedItem(f)).join('')}</div>` : ''}
    </div>`;
  }

  return html || '<div class="sidebar-empty">No feeds.</div>';
}

function renderFeedItem(feed) {
  const sel = S.selectedFeed?.id === feed.id;
  return `<div class="feed-item ${sel ? 'selected' : ''} ${feed.unread ? 'has-unread' : ''}"
              data-action="select-feed" data-feed="${feed.id}">
    <span class="feed-title">${esc(feed.title)}</span>
    ${feed.unread ? `<span class="badge">${feed.unread}</span>` : ''}
  </div>`;
}

async function loadSidebar() {
  try {
    // Source: ttrss/classes/api.php:API.getCategories + getFeeds
    const [cats, feeds] = await Promise.all([
      api('getCategories', { include_empty: true }),
      api('getFeeds', { cat_id: -4, include_nested: false }),
    ]);
    S.categories = (cats || []).filter(c => c.id > 0); // exclude virtual cats
    S.feeds = feeds || [];
    render();
  } catch (e) {
    console.error('loadSidebar', e);
  }
}

async function loadGlobalUnread() {
  try {
    // Source: ttrss/include/functions.php:getGlobalUnread
    const r = await api('getUnread');
    S.globalUnread = parseInt(r.unread) || 0;
    const badge = document.querySelector('.unread-badge');
    if (badge) badge.textContent = S.globalUnread || '';
  } catch (_) {}
}

// ── Article list ──────────────────────────────────────────────────────────────
// Source: ttrss/js/headlines.js (headline list rendering)
function renderArticleList() {
  if (!S.selectedFeed && !S.headlines.length) {
    return `<div class="list-empty">← Select a feed</div>`;
  }
  if (S.loading && !S.headlines.length) {
    return `<div class="list-empty">Loading…</div>`;
  }
  if (!S.headlines.length) {
    return `<div class="list-empty">No articles.</div>`;
  }

  const items = S.headlines.map(h => {
    const sel = S.article?.id === h.id;
    const date = h.updated ? new Date(h.updated * 1000).toLocaleDateString() : '';
    return `<div class="headline-item ${sel ? 'selected' : ''} ${h.unread ? 'unread' : 'read'}"
                data-action="select-article" data-id="${h.id}">
      <div class="hl-title">${esc(h.title || '(no title)')}</div>
      <div class="hl-meta">
        <span class="hl-feed">${esc(h.feed_title || '')}</span>
        <span class="hl-date">${date}</span>
        ${h.marked ? '<span class="hl-star">★</span>' : ''}
      </div>
    </div>`;
  });

  const more = !S.headlinesEnd
    ? `<button class="btn-load-more" data-action="load-more">Load more…</button>`
    : `<div class="list-end">— end —</div>`;

  return `
    <div class="list-toolbar">
      <button class="btn-icon" data-action="catchup" title="Mark all read">✓ All read</button>
      <button class="btn-icon" data-action="reload-feed" title="Refresh">⟳</button>
    </div>
    ${items.join('')}
    ${more}`;
}

async function loadHeadlines(feedId, reset = true) {
  if (reset) {
    S.headlines = [];
    S.headlinesOffset = 0;
    S.headlinesEnd = false;
    S.article = null;
  }
  S.loading = true;
  render();
  try {
    const LIMIT = 30;
    // Source: ttrss/classes/api.php:API.getHeadlines
    const hs = await api('getHeadlines', {
      feed_id: feedId,
      limit: LIMIT,
      offset: S.headlinesOffset,
      show_content: false,
      view_mode: 'all_articles',
      order_by: 'date_reverse',
    });
    const items = hs || [];
    S.headlines = reset ? items : [...S.headlines, ...items];
    S.headlinesOffset += items.length;
    S.headlinesEnd = items.length < LIMIT;
  } catch (e) {
    console.error('loadHeadlines', e);
  }
  S.loading = false;
  render();
}

async function selectArticle(id) {
  // Source: ttrss/classes/api.php:API.getArticle
  const items = await api('getArticle', { article_id: id });
  if (!items?.length) return;
  S.article = items[0];
  // mark-read in background
  // Source: ttrss/classes/api.php:API.updateArticle field=2 (UNREAD), mode=0 (set false)
  if (S.article.unread) {
    api('updateArticle', { article_ids: String(id), field: 2, mode: 0 })
      .then(() => {
        const h = S.headlines.find(x => x.id === id);
        if (h) { h.unread = false; S.globalUnread = Math.max(0, S.globalUnread - 1); }
        if (S.selectedFeed) S.selectedFeed.unread = Math.max(0, (S.selectedFeed.unread || 1) - 1);
      }).catch(() => {});
  }
  render();
}

// ── Reading pane ──────────────────────────────────────────────────────────────
// Source: ttrss/js/article.js (article view)
function renderReadingPanePlaceholder() {
  if (!S.article) return `<div class="pane-empty">← Select an article</div>`;
  return ''; // actual content injected by renderArticleContent() after DOM insert
}

function renderArticleContent() {
  const pane = document.getElementById('reading-pane');
  if (!pane || !S.article) return;
  const a = S.article;
  const date = a.updated ? new Date(a.updated * 1000).toLocaleString() : '';
  // Source: ttrss/classes/api.php:API.getArticle — content field contains feed HTML
  // Security: article content rendered in sandboxed iframe srcdoc to prevent XSS (R08)
  const iframeDoc = `<!doctype html><html><head>
    <meta charset="utf-8">
    <style>
      body { font-family: system-ui, sans-serif; font-size: 15px; line-height: 1.6;
             max-width: 700px; margin: 0 auto; padding: 16px; color: #cdd6f4;
             background: #1e1e2e; }
      a { color: #89b4fa; }
      img { max-width: 100%; height: auto; border-radius: 4px; }
      pre, code { background: #313244; padding: 2px 6px; border-radius: 4px; }
      blockquote { border-left: 3px solid #89b4fa; margin: 0; padding-left: 12px; color: #a6adc8; }
    </style>
  </head><body>${a.content || '<p><em>No content.</em></p>'}</body></html>`;

  pane.innerHTML = `
    <div class="article-header">
      <h2 class="article-title"><a href="${esc(a.link || '#')}" target="_blank" rel="noopener">${esc(a.title || '(no title)')}</a></h2>
      <div class="article-meta">
        ${a.author ? `<span>${esc(a.author)}</span> · ` : ''}
        <span>${date}</span>
        ${a.feed_title ? ` · <span>${esc(a.feed_title)}</span>` : ''}
      </div>
      <div class="article-actions">
        <button class="btn-icon ${a.marked ? 'active' : ''}" data-action="toggle-star" data-id="${a.id}" title="Star">★</button>
        <a class="btn-icon" href="${esc(a.link || '#')}" target="_blank" rel="noopener" title="Open original">↗ Original</a>
      </div>
    </div>
    <iframe class="article-frame" srcdoc="${escAttr(iframeDoc)}"
            sandbox="allow-same-origin allow-popups"
            title="Article content"></iframe>`;
}

// ── Settings / Subscribe modal ────────────────────────────────────────────────
// Source: ttrss/js/prefs.js + ttrss/classes/handler/prefs.php (settings UI)
function renderModal() {
  if (S.modal === 'subscribe') return renderSubscribeModal();
  if (S.modal === 'settings') return renderSettingsModal();
  return '';
}

function renderSubscribeModal() {
  return `
  <div class="modal-overlay" id="modal-overlay">
    <div class="modal-box">
      <div class="modal-header">
        <h3>Subscribe to feed</h3>
        <button class="btn-icon" data-action="close-modal">✕</button>
      </div>
      <div class="modal-body">
        <p>Enter a feed URL or website address:</p>
        <input id="sub-url" type="url" class="modal-input"
               placeholder="https://example.com/feed.xml"
               value="${esc(S.subscribeUrl)}">
        ${S.subscribeStatus ? `<div class="sub-status">${esc(S.subscribeStatus)}</div>` : ''}
      </div>
      <div class="modal-footer">
        <button class="btn-primary" data-action="do-subscribe">Subscribe</button>
        <button class="btn-text modal-cancel" data-action="close-modal">Cancel</button>
      </div>
    </div>
  </div>`;
}

function renderSettingsModal() {
  return `
  <div class="modal-overlay" id="modal-overlay">
    <div class="modal-box">
      <div class="modal-header">
        <h3>Settings</h3>
        <button class="btn-icon" data-action="close-modal">✕</button>
      </div>
      <div class="modal-body">
        <p class="settings-info">
          Server: TT-RSS Python · API Level 8<br>
          User: ${esc(S.user || '')}
        </p>
        <h4>Subscribed feeds (${S.feeds.filter(f => f.id > 0).length})</h4>
        <div class="feeds-list">
          ${S.feeds.filter(f => f.id > 0).map(f => `
            <div class="feed-settings-row">
              <span>${esc(f.title)}</span>
              <button class="btn-danger-sm" data-action="unsubscribe" data-feed="${f.id}">Remove</button>
            </div>`).join('') || '<p><em>No feeds subscribed.</em></p>'}
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-text" data-action="close-modal">Close</button>
      </div>
    </div>
  </div>`;
}

async function doSubscribe() {
  const url = document.getElementById('sub-url')?.value?.trim();
  if (!url) return;
  S.subscribeUrl = url;
  S.subscribeStatus = 'Subscribing…';
  render();
  try {
    // Source: ttrss/classes/api.php:API.subscribeToFeed
    const r = await api('subscribeToFeed', { feed_url: url });
    const code = r?.status?.code ?? r?.code ?? -1;
    S.subscribeStatus = code === 1 ? '✓ Subscribed!' : code === 0 ? 'Already subscribed.' : `Done (code ${code})`;
    S.subscribeUrl = '';
    await loadSidebar();
    await loadGlobalUnread();
  } catch (e) {
    S.subscribeStatus = `Error: ${e.message}`;
  }
  render();
}

async function doUnsubscribe(feedId) {
  try {
    // Source: ttrss/classes/api.php:API.unsubscribeFeed
    await api('unsubscribeFeed', { feed_id: feedId });
    await loadSidebar();
    if (S.selectedFeed?.id === feedId) {
      S.selectedFeed = null;
      S.headlines = [];
      S.article = null;
    }
    S.modal = 'settings'; // keep modal open, re-render
  } catch (e) {
    alert('Unsubscribe failed: ' + e.message);
  }
  render();
}

// ── Event binding ─────────────────────────────────────────────────────────────
function bind() {
  const root = document.getElementById('app');
  if (!root) return;

  // Login form submit
  root.querySelector('#login-form')?.addEventListener('submit', e => {
    e.preventDefault();
    const user = root.querySelector('#login-user')?.value?.trim();
    const pass = root.querySelector('#login-pass')?.value;
    if (user && pass) doLogin(user, pass);
  });

  // Subscribe URL input — update state on keyup so value survives re-render
  root.querySelector('#sub-url')?.addEventListener('input', e => {
    S.subscribeUrl = e.target.value;
  });

  // Modal overlay background click — close only when clicking the backdrop, not the box
  root.querySelector('#modal-overlay')?.addEventListener('click', e => {
    if (e.target === e.currentTarget) { S.modal = null; S.subscribeStatus = ''; render(); }
  });

  // Delegated click handler for all data-action elements
  root.addEventListener('click', e => {
    const el = e.target.closest('[data-action]');
    if (!el) return;
    const action = el.dataset.action;

    if (action === 'logout') {
      api('logout').catch(() => {}).finally(() => {
        S.view = 'login'; S.user = null; S.feeds = []; S.categories = [];
        S.headlines = []; S.article = null; S.globalUnread = 0;
        render();
      });
    }
    else if (action === 'refresh') {
      loadSidebar(); loadGlobalUnread();
    }
    else if (action === 'subscribe') {
      S.modal = 'subscribe'; S.subscribeStatus = ''; render();
    }
    else if (action === 'settings') {
      S.modal = 'settings'; render();
    }
    else if (action === 'close-modal') {
      S.modal = null; S.subscribeStatus = ''; render();
    }
    else if (action === 'do-subscribe') {
      doSubscribe();
    }
    else if (action === 'unsubscribe') {
      doUnsubscribe(parseInt(el.dataset.feed));
    }
    else if (action === 'toggle-cat') {
      const k = el.dataset.cat;
      S.catExpanded[k] = !(S.catExpanded[k] !== false);
      render();
    }
    else if (action === 'select-feed') {
      const fid = parseInt(el.dataset.feed);
      S.selectedFeed = S.feeds.find(f => f.id === fid) || { id: fid, title: '' };
      loadHeadlines(fid);
    }
    else if (action === 'reload-feed') {
      if (S.selectedFeed) loadHeadlines(S.selectedFeed.id);
    }
    else if (action === 'catchup') {
      if (!S.selectedFeed) return;
      // Source: ttrss/classes/api.php:API.catchupFeed
      api('catchupFeed', { feed_id: S.selectedFeed.id })
        .then(() => {
          S.headlines.forEach(h => h.unread = false);
          S.selectedFeed.unread = 0;
          S.globalUnread = 0;
          render(); loadGlobalUnread();
        }).catch(e => alert('Catchup failed: ' + e.message));
    }
    else if (action === 'select-article') {
      const id = parseInt(el.dataset.id);
      selectArticle(id);
    }
    else if (action === 'load-more') {
      if (S.selectedFeed && !S.headlinesEnd) loadHeadlines(S.selectedFeed.id, false);
    }
    else if (action === 'toggle-star') {
      const id = parseInt(el.dataset.id);
      if (!S.article || S.article.id !== id) return;
      const nowStarred = !S.article.marked;
      // Source: ttrss/classes/api.php:API.updateArticle field=0 (MARKED)
      api('updateArticle', { article_ids: String(id), field: 0, mode: nowStarred ? 1 : 0 })
        .then(() => {
          S.article.marked = nowStarred;
          const h = S.headlines.find(x => x.id === id);
          if (h) h.marked = nowStarred;
          render();
        }).catch(e => console.error('star', e));
    }
  });
}

// ── Utilities ─────────────────────────────────────────────────────────────────
// Escape HTML for text content
function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
// Escape for HTML attribute values (e.g. srcdoc)
function escAttr(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/"/g,'&quot;');
}

// Close modal on Escape key
// New: keyboard UX — no PHP equivalent
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && S.modal) { S.modal = null; render(); }
});

// ── Bootstrap ─────────────────────────────────────────────────────────────────
// Source: ttrss/index.php (app entry point) + ttrss/classes/api.php:API.isLoggedIn
(async () => {
  try {
    // Source: ttrss/classes/api.php:API.isLoggedIn (lines 94-95)
    const r = await api('isLoggedIn');
    if (r?.status === true) {
      S.view = 'app';
      render();
      await Promise.all([loadSidebar(), loadGlobalUnread()]);
    } else {
      render();
    }
  } catch (_) {
    render();
  }
})();
