/* =========================================================
   SHOWCASE FEATURES — presentation, search, client mode,
   analytics, transitions, story mode helpers
========================================================= */

(function () {
    const SETTINGS = (typeof window.SETTINGS !== 'undefined' && window.SETTINGS) ||
        (typeof SETTINGS !== 'undefined' ? SETTINGS : {}) || {};

    const defaults = {
        transition: 'fade',       // fade | slide | none
        autoAdvanceSec: 0,        // 0 = off
        audioSrc: '',
        audioVolume: 0.25,
        followSystemTheme: false,
        clientMode: false,
        homeThumbnails: true,
        analytics: true
    };
    const cfg = Object.assign({}, defaults, SETTINGS);

    /* ---------- visible project list (client mode) ---------- */
    window.getVisibleProjects = function getVisibleProjects() {
        if (typeof PROJECTS === 'undefined') return [];
        const client = cfg.clientMode ||
            (typeof location !== 'undefined' && /[?&]client=1\b/.test(location.search));
        if (!client) return PROJECTS.slice();
        return PROJECTS.filter(p => !p.clientHidden);
    };

    /* ---------- Analytics (local only) ---------- */
    function track(event, detail) {
        if (!cfg.analytics) return;
        try {
            const key = 'showcase_analytics_v1';
            const log = JSON.parse(localStorage.getItem(key) || '[]');
            log.push({ t: Date.now(), e: event, d: detail || null, path: location.pathname });
            while (log.length > 400) log.shift();
            localStorage.setItem(key, JSON.stringify(log));
        } catch (_) { /* private mode */ }
    }
    window.showcaseTrack = track;

    /* ---------- System theme ---------- */
    function applySystemThemeIfNeeded() {
        if (!cfg.followSystemTheme) return;
        const dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (typeof applyTheme === 'function') applyTheme(dark ? 'dark' : 'light');
    }

    /* ---------- Presentation mode ---------- */
    let presentOn = false;
    let advanceTimer = null;

    function setPresentation(on) {
        presentOn = !!on;
        document.body.classList.toggle('presentation-mode', presentOn);
        document.body.classList.toggle('chrome-hidden', presentOn);
        const btn = document.getElementById('presentBtn');
        if (btn) btn.classList.toggle('active', presentOn);
        if (presentOn) {
            track('present_on');
            try { document.documentElement.requestFullscreen?.(); } catch (_) {}
            startAutoAdvance();
        } else {
            stopAutoAdvance();
            try { if (document.fullscreenElement) document.exitFullscreen?.(); } catch (_) {}
        }
        showToast(presentOn ? 'PRESENTATION ON' : 'PRESENTATION OFF');
    }
    window.togglePresentation = function () { setPresentation(!presentOn); };

    function startAutoAdvance() {
        stopAutoAdvance();
        const sec = Number(cfg.autoAdvanceSec) || 0;
        if (sec <= 0 || !presentOn) return;
        advanceTimer = setInterval(() => {
            if (!presentOn) return;
            goNextProject();
        }, sec * 1000);
    }
    function stopAutoAdvance() {
        if (advanceTimer) clearInterval(advanceTimer);
        advanceTimer = null;
    }

    function goNextProject() {
        const list = window.getVisibleProjects();
        const bodyProject = document.body.getAttribute('data-project');
        if (bodyProject === 'end') {
            window.location.href = (location.pathname.includes('/projects/') ? '../' : '') + 'index.html';
            return;
        }
        const id = parseInt(bodyProject, 10);
        if (isNaN(id)) {
            // home / thanks → first project
            if (list[0]) {
                const base = location.pathname.includes('/projects/') ? '' : 'projects/';
                window.location.href = base + list[0].file;
            }
            return;
        }
        const idx = list.findIndex(p => p.id === id || PROJECTS.indexOf(p) === id);
        const next = list[idx + 1];
        if (next) window.location.href = next.file;
        else window.location.href = 'end.html';
    }
    function goPrevProject() {
        const list = window.getVisibleProjects();
        const bodyProject = document.body.getAttribute('data-project');
        const id = parseInt(bodyProject, 10);
        if (isNaN(id) || id <= 0) {
            window.location.href = (location.pathname.includes('/projects/') ? '../' : '') + 'index.html';
            return;
        }
        const idx = list.findIndex(p => p.id === id || PROJECTS.indexOf(p) === id);
        if (idx > 0) window.location.href = list[idx - 1].file;
        else window.location.href = (location.pathname.includes('/projects/') ? '../' : '') + 'index.html';
    }

    /* ---------- Search overlay ---------- */
    function ensureSearchUI() {
        if (document.getElementById('searchOverlay')) return;
        const el = document.createElement('div');
        el.id = 'searchOverlay';
        el.className = 'search-overlay';
        el.innerHTML = `
            <div class="search-panel">
                <input type="search" id="searchInput" placeholder="Search projects, tools, tags…" autocomplete="off" />
                <div id="searchResults" class="search-results"></div>
                <div class="search-hint">Type to filter · Enter open · Esc close</div>
            </div>`;
        document.body.appendChild(el);
        el.addEventListener('click', (e) => { if (e.target === el) closeSearch(); });
        document.getElementById('searchInput').addEventListener('input', renderSearch);
        document.getElementById('searchInput').addEventListener('keydown', (e) => {
            if (e.key === 'Escape') { closeSearch(); e.preventDefault(); }
            if (e.key === 'Enter') {
                const first = document.querySelector('#searchResults a');
                if (first) first.click();
            }
        });
    }
    function openSearch() {
        ensureSearchUI();
        document.getElementById('searchOverlay').classList.add('active');
        const input = document.getElementById('searchInput');
        input.value = '';
        renderSearch();
        setTimeout(() => input.focus(), 30);
        track('search_open');
    }
    function closeSearch() {
        document.getElementById('searchOverlay')?.classList.remove('active');
    }
    window.toggleSearch = function () {
        const el = document.getElementById('searchOverlay');
        if (el && el.classList.contains('active')) closeSearch();
        else openSearch();
    };

    function renderSearch() {
        const q = (document.getElementById('searchInput')?.value || '').trim().toLowerCase();
        const box = document.getElementById('searchResults');
        if (!box) return;
        const list = window.getVisibleProjects();
        const base = location.pathname.includes('/projects/') ? '' : 'projects/';
        const hits = list.filter(p => {
            if (!q) return true;
            const bag = [
                p.title, p.category, p.description, p.status,
                ...(p.tags || []),
                ...(p.tools || []),
                JSON.stringify(p.details || {})
            ].join(' ').toLowerCase();
            return bag.includes(q);
        });
        if (!hits.length) {
            box.innerHTML = '<div class="search-empty">No matches</div>';
            return;
        }
        box.innerHTML = hits.map(p => {
            const status = p.status ? `<span class="tag-pill status-${esc(p.status)}">${esc(p.status)}</span>` : '';
            const tags = (p.tags || []).slice(0, 4).map(t => `<span class="tag-pill">${esc(t)}</span>`).join('');
            return `<a class="search-hit" href="${base}${esc(p.file)}">
                <span class="search-hit-title">${esc(p.title || 'Untitled')}</span>
                <span class="search-hit-meta">${esc(p.category || '')}</span>
                <span class="search-hit-tags">${status}${tags}</span>
            </a>`;
        }).join('');
    }
    function esc(s) {
        return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    /* ---------- Home thumbnails ---------- */
    function buildHomeThumbnails() {
        if (!cfg.homeThumbnails) return;
        if (!document.querySelector('.landing-screen')) return;
        const list = window.getVisibleProjects();
        if (!list.length) return;
        let strip = document.getElementById('homeThumbStrip');
        if (!strip) {
            strip = document.createElement('div');
            strip.id = 'homeThumbStrip';
            strip.className = 'home-thumb-strip';
            const main = document.querySelector('.landing-main') || document.querySelector('.landing-screen');
            main.appendChild(strip);
        }
        const base = 'projects/';
        const assetBase = (typeof PATHS !== 'undefined' && PATHS.assetBase) || '';
        strip.innerHTML = list.map(p => {
            const img = p.poster || (Array.isArray(p.gallery) && p.gallery[0] && (p.gallery[0].src || p.gallery[0])) || '';
            const src = img ? assetBase + img : '';
            const st = p.status ? `<span class="thumb-status">${esc(p.status)}</span>` : '';
            return `<a class="home-thumb" href="${base}${esc(p.file)}" title="${esc(p.title)}">
                <div class="home-thumb-img">${src ? `<img src="${esc(src)}" alt="" loading="lazy"/>` : '<div class="home-thumb-ph"></div>'}</div>
                <div class="home-thumb-cap">${esc(p.title || '')}${st}</div>
            </a>`;
        }).join('');
    }

    /* ---------- Status badges in sidebar ---------- */
    function enhanceSidebar() {
        const nav = document.getElementById('sidebarNav');
        if (!nav || typeof PROJECTS === 'undefined') return;
        const client = cfg.clientMode || /[?&]client=1\b/.test(location.search);
        nav.querySelectorAll('.sidebar-project-link').forEach((a, i) => {
            const p = PROJECTS[i];
            if (!p) return;
            if (client && p.clientHidden) {
                a.style.display = 'none';
                return;
            }
            if (p.status && !a.querySelector('.side-status')) {
                const s = document.createElement('span');
                s.className = 'side-status status-' + String(p.status).toLowerCase().replace(/\s+/g, '-');
                s.textContent = p.status;
                a.appendChild(s);
            }
        });
    }

    /* ---------- Audio bed ---------- */
    function setupAudio() {
        if (!cfg.audioSrc) return;
        let audio = document.getElementById('showcaseAudio');
        if (!audio) {
            audio = document.createElement('audio');
            audio.id = 'showcaseAudio';
            audio.loop = true;
            audio.preload = 'auto';
            audio.src = ((typeof PATHS !== 'undefined' && PATHS.assetBase) || '') + cfg.audioSrc;
            audio.volume = Math.min(1, Math.max(0, Number(cfg.audioVolume) || 0.25));
            document.body.appendChild(audio);
        }
        const btn = document.getElementById('audioBtn');
        if (btn) {
            btn.style.display = '';
            btn.onclick = () => {
                if (audio.paused) { audio.play().catch(() => {}); btn.classList.add('active'); }
                else { audio.pause(); btn.classList.remove('active'); }
            };
        }
    }

    /* ---------- Transitions ---------- */
    function applyTransitionClass() {
        document.body.classList.add('tx-' + (cfg.transition || 'fade'));
        document.body.classList.add('page-enter');
        requestAnimationFrame(() => {
            requestAnimationFrame(() => document.body.classList.add('page-enter-active'));
        });
    }

    /* ---------- Topbar feature buttons ---------- */
    function injectTopbarControls() {
        const right = document.querySelector('.topbar-right') || document.querySelector('.topbar');
        if (!right || document.getElementById('presentBtn')) return;
        const wrap = document.createElement('div');
        wrap.className = 'feature-btns';
        wrap.innerHTML = `
            <button type="button" class="icon-btn" id="searchBtn" title="Search (/)" aria-label="Search">⌕</button>
            <button type="button" class="icon-btn" id="presentBtn" title="Presentation (P)" aria-label="Presentation">▣</button>
            <button type="button" class="icon-btn" id="audioBtn" title="Audio" aria-label="Audio" style="display:none">♪</button>
            <button type="button" class="icon-btn" id="printBtn" title="Print / PDF" aria-label="Print">⎙</button>
        `;
        right.insertBefore(wrap, right.firstChild);
        document.getElementById('searchBtn').onclick = () => window.toggleSearch();
        document.getElementById('presentBtn').onclick = () => window.togglePresentation();
        document.getElementById('printBtn').onclick = () => window.print();
    }

    /* ---------- Keys ---------- */
    document.addEventListener('keydown', (e) => {
        const tag = (e.target && e.target.tagName) || '';
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
        if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
            e.preventDefault();
            window.toggleSearch();
            return;
        }
        if (e.key === 'p' || e.key === 'P') {
            if (!e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                window.togglePresentation();
            }
        }
        if (presentOn && e.key === ' ') {
            e.preventDefault();
            goNextProject();
        }
    });

    /* ---------- Passes story mode (called from project page) ---------- */
    window.startPassesStory = function (images, labelEl, imgEl, intervalMs) {
        if (!images || !images.length) return null;
        let i = 0;
        const tick = () => {
            i = (i + 1) % images.length;
            const item = images[i];
            const src = typeof item === 'string' ? item : (item.src || '');
            const name = typeof item === 'string' ? '' : (item.name || item.label || '');
            if (imgEl && src) imgEl.src = ((typeof PATHS !== 'undefined' && PATHS.assetBase) || '') + src;
            if (labelEl) labelEl.textContent = name || ('Pass ' + (i + 1));
        };
        return setInterval(tick, intervalMs || 1600);
    };

    /* ---------- Boot ---------- */
    function boot() {
        applyTransitionClass();
        applySystemThemeIfNeeded();
        injectTopbarControls();
        setupAudio();
        enhanceSidebar();
        buildHomeThumbnails();
        track('page_view', document.body.getAttribute('data-project') || 'home');
        // Client mode badge
        if (cfg.clientMode || /[?&]client=1\b/.test(location.search)) {
            document.body.classList.add('client-mode');
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
