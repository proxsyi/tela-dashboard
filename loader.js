(function () {
  'use strict';

  // ── Fallback config ─────────────────────────────────────────
  const FALLBACK_CONFIG = {
    schemaVersion: 1,
    name: 'Tela Hub',
    status: 'Preparing custom dashboard',
    autonomy: 'Dormant until Phase 2',
    progress: 80,
    currentTask: 'Build custom GitHub Pages dashboard embedded in Notion',
    sourceMode: 'fallback-static-config',
    lastUpdated: '2026-04-28',
    repo: {
      name: 'tela-dashboard',
      status: 'local-build',
      url: 'https://github.com/proxsyi/tela-dashboard',
      pagesUrl: 'https://proxsyi.github.io/tela-dashboard/',
    },
    needsCash: [
      {
        title: 'Publish the public-safe Notion source page after review',
        status: 'Waiting',
        tone: 'yellow',
      },
      {
        title: 'Paste the GitHub Pages URL back into Tela Hub',
        status: 'Waiting',
        tone: 'purple',
      },
    ],
    cards: [
      { label: 'System',    value: 'Operational', detail: 'Dashboard shell ready',       tone: 'green'  },
      { label: 'Autonomy',  value: 'Dormant',      detail: 'No live controls in v1',      tone: 'yellow' },
      { label: 'Progress',  value: '80%',           detail: 'Foundation built',            tone: 'purple' },
      { label: 'Cost',      value: '$0.00',         detail: 'Static GitHub Pages hosting', tone: 'gray'   },
    ],
    sections: [
      {
        title: 'Current Work',
        body: 'Build the custom dashboard repo and embed it in Tela Hub.',
      },
      {
        title: 'Next Step',
        body: 'Create the GitHub repo, enable GitHub Pages, then connect the public-safe Notion source config.',
      },
      {
        title: 'Backend State',
        body: 'Dashboard databases already exist in Notion for future writeback. V1 only reads safe config and does not expose controls.',
      },
    ],
  };

  // ── Normalise config ────────────────────────────────────────
  function normalise(cfg) {
    if (!cfg || typeof cfg !== 'object') return FALLBACK_CONFIG;
    return {
      schemaVersion: cfg.schemaVersion || 1,
      name:          (typeof cfg.name === 'string' && cfg.name) ? cfg.name : FALLBACK_CONFIG.name,
      status:        typeof cfg.status === 'string' ? cfg.status : '',
      autonomy:      typeof cfg.autonomy === 'string' ? cfg.autonomy : '',
      progress:      Math.min(100, Math.max(0, Number(cfg.progress) || 0)),
      currentTask:   typeof cfg.currentTask === 'string' ? cfg.currentTask : '',
      sourceMode:    typeof cfg.sourceMode === 'string' ? cfg.sourceMode : 'unknown',
      lastUpdated:   typeof cfg.lastUpdated === 'string' ? cfg.lastUpdated : '',
      repo:          (cfg.repo && typeof cfg.repo === 'object') ? cfg.repo : {},
      needsCash:     Array.isArray(cfg.needsCash) ? cfg.needsCash : [],
      cards:         Array.isArray(cfg.cards) ? cfg.cards : [],
      sections:      Array.isArray(cfg.sections) ? cfg.sections : [],
    };
  }

  // ── DOM helpers ─────────────────────────────────────────────
  function el(tag, cls) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    return e;
  }

  function setText(id, text) {
    const node = document.getElementById(id);
    if (node) node.textContent = text;
  }

  function safeAttr(val) {
    return String(val || '').replace(/[<>"'&]/g, c => ({
      '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;', '&': '&amp;',
    }[c]));
  }

  // ── Render functions ────────────────────────────────────────
  function renderHero(cfg, isRemote) {
    setText('dash-name', cfg.name);
    setText('hero-status', cfg.status);
    setText('hero-autonomy', cfg.autonomy);

    const bar = document.getElementById('progress-bar');
    const label = document.getElementById('progress-label');
    if (bar) bar.style.width = cfg.progress + '%';
    if (label) label.textContent = cfg.progress + '%';

    const pill = document.getElementById('dash-source-pill');
    if (pill) {
      pill.textContent = isRemote ? 'Remote Config' : 'Fallback Config';
      if (isRemote) pill.classList.add('remote');
    }

    const updated = document.getElementById('dash-last-updated');
    if (updated && cfg.lastUpdated) {
      updated.textContent = 'Updated ' + cfg.lastUpdated;
    }
  }

  function renderCards(cfg) {
    const grid = document.getElementById('cards-grid');
    if (!grid) return;
    grid.textContent = '';

    for (const c of cfg.cards) {
      const tone = typeof c.tone === 'string' ? c.tone : 'gray';
      const wrapper = el('div', 'tone-' + tone);
      const card = el('div', 'card');

      const lbl = el('div', 'card-label');
      lbl.textContent = c.label || '';

      const val = el('div', 'card-value');
      val.textContent = c.value || '';

      const detail = el('div', 'card-detail');
      detail.textContent = c.detail || '';

      card.appendChild(lbl);
      card.appendChild(val);
      card.appendChild(detail);
      wrapper.appendChild(card);
      grid.appendChild(wrapper);
    }
  }

  function renderCurrentTask(cfg) {
    const body = document.getElementById('current-task-body');
    if (body) body.textContent = cfg.currentTask;
  }

  function renderNeedsCash(cfg) {
    const section = document.getElementById('needs-cash-section');
    const list = document.getElementById('needs-cash-list');
    if (!section || !list) return;

    if (!cfg.needsCash.length) {
      section.classList.add('hidden');
      return;
    }
    section.classList.remove('hidden');
    list.textContent = '';

    for (const item of cfg.needsCash) {
      const tone = typeof item.tone === 'string' ? item.tone : 'gray';
      const row = el('div', 'needs-item');

      const title = el('span', 'needs-title');
      title.textContent = item.title || '';

      const pill = el('span', 'status-pill pill-' + tone);
      pill.textContent = item.status || '';

      row.appendChild(title);
      row.appendChild(pill);
      list.appendChild(row);
    }
  }

  function renderSections(cfg) {
    const area = document.getElementById('sections-area');
    if (!area) return;
    area.textContent = '';

    for (const s of cfg.sections) {
      const panel = el('div', 'info-section');

      const h = el('div', 'info-section-title');
      h.textContent = s.title || '';

      const body = el('div', 'info-section-body');
      body.textContent = s.body || '';

      panel.appendChild(h);
      panel.appendChild(body);
      area.appendChild(panel);
    }
  }

  function renderRepo(cfg) {
    const container = document.getElementById('repo-info');
    if (!container) return;
    container.textContent = '';
    const repo = cfg.repo;

    const rows = [
      { label: 'Name',   value: repo.name || '—', link: null },
      { label: 'Status', value: repo.status || '—', link: null },
      { label: 'Repo',   value: repo.url || '', link: repo.url || null },
      { label: 'Pages',  value: repo.pagesUrl || '', link: repo.pagesUrl || null },
    ];

    for (const r of rows) {
      if (!r.value) continue;
      const row = el('div', 'repo-row');

      const lbl = el('span', 'repo-row-label');
      lbl.textContent = r.label;

      const val = el('span', 'repo-row-value');
      if (r.link) {
        const a = document.createElement('a');
        a.href = safeAttr(r.link);
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        a.textContent = r.value;
        val.appendChild(a);
      } else {
        val.textContent = r.value;
      }

      row.appendChild(lbl);
      row.appendChild(val);
      container.appendChild(row);
    }
  }

  // ── Main render ─────────────────────────────────────────────
  function render(raw, isRemote) {
    const cfg = normalise(raw);

    renderHero(cfg, isRemote);
    renderCards(cfg);
    renderCurrentTask(cfg);
    renderNeedsCash(cfg);
    renderSections(cfg);
    renderRepo(cfg);

    const loading = document.getElementById('loading');
    const dashboard = document.getElementById('dashboard');
    if (loading) loading.classList.add('hidden');
    if (dashboard) dashboard.classList.remove('hidden');
  }

  // ── Boot ────────────────────────────────────────────────────
  async function boot() {
    if (!window.TelaSource) {
      console.warn('[Tela] notion-source.js not loaded — using fallback config');
      render(FALLBACK_CONFIG, false);
      return;
    }

    let remote = null;
    try {
      remote = await window.TelaSource.loadRemoteConfig();
    } catch (err) {
      console.warn('[Tela] Remote config load threw unexpectedly:', err.message);
    }

    if (remote && typeof remote === 'object') {
      console.log('[Tela] Using remote config.');
      render(remote, true);
    } else {
      console.log('[Tela] Using fallback config.');
      render(FALLBACK_CONFIG, false);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
