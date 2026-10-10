/* =========================================================
   THEME
========================================================= */

let currentTheme = 'dark';

function applyTheme(theme) {
    currentTheme = theme;
    document.body.classList.toggle('theme-light', theme === 'light');
    document.body.classList.toggle('theme-dark', theme === 'dark');

    const icon = document.querySelector('#themeToggleBtn .theme-icon');
    if (icon) icon.textContent = theme === 'light' ? '☾' : '☀';
}

function toggleTheme() {
    const next = currentTheme === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    try {
        localStorage.setItem('artistShowcaseTheme', next);
    } catch (_) { /* private mode / blocked storage */ }
    showToast(next === 'light' ? 'LIGHT THEME' : 'DARK THEME');
}

function loadTheme() {
    let saved = 'dark';
    try {
        saved = localStorage.getItem('artistShowcaseTheme') || 'dark';
    } catch (_) {}
    applyTheme(saved);
}


/* =========================================================
   CUSTOM FONT
========================================================= */

function applyHeader() {
    if (typeof HEADER === 'undefined' || !HEADER) return;
    const brand = (HEADER.brand || '').trim();
    if (!brand) return;
    document.querySelectorAll('.brand').forEach(el => {
        el.textContent = brand;
    });
}

function applyFont() {
    if (typeof FONT === 'undefined' || !FONT) return;
    const family = (FONT.family || '').trim();
    const url = (FONT.url || '').trim();
    if (url) {
        let link = document.getElementById('customFontLink');
        if (!link) {
            link = document.createElement('link');
            link.id = 'customFontLink';
            link.rel = 'stylesheet';
            document.head.appendChild(link);
        }
        link.href = url;
    }
    if (family) {
        document.documentElement.style.setProperty('--app-font', family);
        document.body.style.fontFamily = family;
    }
}

/* =========================================================
   HOME / END content from data.js
========================================================= */

function applyHomeContent() {
    if (typeof HOME === 'undefined' || !HOME) return;
    const eye = document.querySelector('.landing-screen .eyebrow');
    const head = document.querySelector('.landing-screen .main-heading');
    if (eye && HOME.eyebrow != null) eye.textContent = HOME.eyebrow;
    if (head && HOME.heading != null) {
        head.innerHTML = String(HOME.heading).replace(/\n/g, '<br>');
    }
    const mediaWrap = document.getElementById('homeMedia');
    if (!mediaWrap) return;
    const type = (HOME.mediaType || '').toLowerCase();
    const src = HOME.media || '';
    mediaWrap.innerHTML = '';
    if (!src || !type) {
        mediaWrap.style.display = 'none';
        document.querySelector('.landing-screen')?.classList.remove('has-media');
        return;
    }
    mediaWrap.style.display = '';
    document.querySelector('.landing-screen')?.classList.add('has-media');
    const base = (typeof PATHS !== 'undefined' && PATHS.assetBase) ? PATHS.assetBase : '';
    const url = base + src;
    if (type === 'video') {
        const v = document.createElement('video');
        v.src = url;
        v.autoplay = true;
        v.muted = true;
        v.loop = true;
        v.playsInline = true;
        v.className = 'hero-media-el';
        mediaWrap.appendChild(v);
    } else {
        const img = document.createElement('img');
        img.src = url;
        img.alt = '';
        img.className = 'hero-media-el';
        mediaWrap.appendChild(img);
    }
}

function applyEndContent() {
    if (typeof END === 'undefined' || !END) return;
    const eye = document.querySelector('.end-screen .eyebrow');
    const head = document.querySelector('.end-screen .end-heading');
    const note = document.querySelector('.end-screen .end-note');
    if (eye && END.eyebrow != null) eye.textContent = END.eyebrow;
    if (head && END.heading != null) head.textContent = END.heading;
    if (note && END.note != null) note.textContent = END.note;
    const mediaWrap = document.getElementById('endMedia');
    if (!mediaWrap) return;
    const type = (END.mediaType || '').toLowerCase();
    const src = END.media || '';
    mediaWrap.innerHTML = '';
    if (!src || !type) {
        mediaWrap.style.display = 'none';
        document.querySelector('.end-screen')?.classList.remove('has-media');
        return;
    }
    mediaWrap.style.display = '';
    document.querySelector('.end-screen')?.classList.add('has-media');
    const base = (typeof PATHS !== 'undefined' && PATHS.assetBase) ? PATHS.assetBase : '';
    const url = base + src;
    if (type === 'video') {
        const v = document.createElement('video');
        v.src = url;
        v.autoplay = true;
        v.muted = true;
        v.loop = true;
        v.playsInline = true;
        v.className = 'hero-media-el';
        mediaWrap.appendChild(v);
    } else {
        const img = document.createElement('img');
        img.src = url;
        img.alt = '';
        img.className = 'hero-media-el';
        mediaWrap.appendChild(img);
    }
}

/* =========================================================
   SIDEBAR — hidden by default
========================================================= */

let sidebarCollapsed = true;

function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;
    document.getElementById('sidebar')?.classList.toggle('collapsed', sidebarCollapsed);
    showToast(sidebarCollapsed ? 'SIDEBAR HIDDEN' : 'SIDEBAR SHOWN');
}

function initSidebar() {
    document.getElementById('sidebar')?.classList.add('collapsed');
}

function buildSidebar() {
    const nav = document.getElementById('sidebarNav');
    if (!nav || typeof PROJECTS === 'undefined') return;

    nav.innerHTML = '';

    const nameEl = document.getElementById('sidebarArtistName');
    const roleEl = document.getElementById('sidebarArtistRole');
    if (typeof ARTIST !== 'undefined') {
        if (nameEl) nameEl.textContent = ARTIST.name || '';
        if (roleEl) roleEl.textContent = ARTIST.role || '';
    }

    const bodyProject = document.body.getAttribute('data-project');
    const currentId = bodyProject !== null ? parseInt(bodyProject, 10) : -1;

    const inProjectsFolder = window.location.pathname.includes('/projects/');
    const baseHref = inProjectsFolder ? '' : 'projects/';

    PROJECTS.forEach(p => {
        const a = document.createElement('a');
        a.className = 'sidebar-project-link';
        if (p.id === currentId) a.classList.add('active');
        a.href = baseHref + p.file;
        a.addEventListener('click', () => {
            if (typeof lockChromeForNavigation === 'function') lockChromeForNavigation();
        });

        a.innerHTML = `
            <span class="sidebar-project-num">${String(p.id + 1).padStart(2, '0')}</span>
            <span class="sidebar-project-name">${escapeHtml(p.title || 'Untitled')}</span>
        `;

        nav.appendChild(a);
    });

    // Optional thank-you slide (when THANKS.enabled)
    const bodyPage = document.body.getAttribute('data-page');
    if (typeof isThanksEnabled === 'function' && isThanksEnabled()) {
        const thanksLink = document.createElement('a');
        thanksLink.className = 'sidebar-project-link';
        thanksLink.href = inProjectsFolder ? '../thanks.html' : 'thanks.html';
        if (bodyPage === 'thanks') thanksLink.classList.add('active');
        thanksLink.innerHTML = `
            <span class="sidebar-project-num">◇</span>
            <span class="sidebar-project-name">THANKS</span>
        `;
        thanksLink.addEventListener('click', () => {
            if (typeof lockChromeForNavigation === 'function') lockChromeForNavigation();
        });
        nav.appendChild(thanksLink);
    }

    // Fixed end slide — always last in sidebar, never a PROJECTS entry
    const endLink = document.createElement('a');
    endLink.className = 'sidebar-project-link';
    endLink.href = baseHref + 'end.html';
    if (bodyProject === 'end') endLink.classList.add('active');
    endLink.innerHTML = `
        <span class="sidebar-project-num">✦</span>
        <span class="sidebar-project-name">END</span>
    `;
    endLink.addEventListener('click', () => {
        if (typeof lockChromeForNavigation === 'function') lockChromeForNavigation();
    });
    nav.appendChild(endLink);
}

/* =========================================================
   LANDING PAGE — dynamic artist card from data.js
========================================================= */

function isThanksEnabled() {
    return typeof THANKS !== 'undefined' && THANKS && THANKS.enabled !== false;
}

function getFirstContentHref() {
    if (isThanksEnabled()) return 'thanks.html';
    if (typeof PROJECTS !== 'undefined' && PROJECTS.length) return 'projects/' + PROJECTS[0].file;
    return '#';
}

function buildLanding() {
    const grid = document.querySelector('.artist-grid');
    if (!grid || typeof PROJECTS === 'undefined' || typeof ARTIST === 'undefined') return;

    grid.innerHTML = '';

    const card = document.createElement('a');
    card.className = 'artist-card';
    card.href = getFirstContentHref();

    const num = document.createElement('div');
    num.className = 'artist-number';
    num.textContent = String(PROJECTS.length).padStart(2, '0') + ' PROJECTS';

    const h2 = document.createElement('h2');
    h2.textContent = ARTIST.name || 'ARTIST';

    const p = document.createElement('p');
    p.textContent = ARTIST.role || '';

    const arrow = document.createElement('div');
    arrow.className = 'artist-arrow';
    arrow.textContent = '→';

    card.appendChild(num);
    card.appendChild(h2);
    card.appendChild(p);
    card.appendChild(arrow);
    grid.appendChild(card);
}

/* =========================================================
   TOAST
========================================================= */

let toastTimer;

function showToast(message) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 1800);
}

/* =========================================================
   HELPERS
========================================================= */

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

/* =========================================================
   GLOBAL KEYBOARD
========================================================= */

document.addEventListener('keydown', (e) => {
    const tag = (e.target && e.target.tagName) || '';
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

    if (e.key === 'h' || e.key === 'H') { toggleHelp(); return; }
    if (e.key === 'Escape') {
        document.getElementById('helpPanel')?.classList.remove('active');
        document.getElementById('lightbox')?.classList.remove('active');
        return;
    }

    if (e.key === 't' || e.key === 'T') { toggleTheme(); return; }
    if ((e.key === '/' || e.key === 'p' || e.key === 'P') && typeof window.toggleSearch === 'function') { /* features.js handles */ }
    if (e.key === 's' || e.key === 'S') { toggleSidebar(); return; }

    if (document.getElementById('helpPanel')?.classList.contains('active')) return;

    // Full-view still/pass open → arrows handled by project.js, do not change project
    if (document.getElementById('lightbox')?.classList.contains('active')) return;

    const bodyProject = document.body.getAttribute('data-project');
    if (bodyProject === null || typeof PROJECTS === 'undefined') return;

    const id = parseInt(bodyProject, 10);
    if (isNaN(id)) return;

    if (e.key === 'ArrowRight') {
        if (typeof lockChromeForNavigation === 'function') lockChromeForNavigation();
        const next = PROJECTS[id + 1];
        if (next) window.location.href = next.file;
        else window.location.href = 'end.html';  // fixed end slide
        return;
    }
    if (e.key === 'ArrowLeft') {
        if (typeof lockChromeForNavigation === 'function') lockChromeForNavigation();
        if (id > 0) window.location.href = PROJECTS[id - 1].file;
        else window.location.href = '../index.html';
        return;
    }
});

/* =========================================================
   HELP
========================================================= */

function toggleHelp() {
    document.getElementById('helpPanel')?.classList.toggle('active');
}


/* =========================================================
   CHROME AUTO-HIDE (header + footer on project pages)
   Clean presentation: bars hide until mouse nears top/bottom
========================================================= */

const CHROME_EDGE_PX = 56;      // reveal when pointer is this close to top/bottom
const CHROME_HIDE_DELAY = 350;  // hide quickly after leaving
const CHROME_LOCK_KEY = 'artistShowcaseChromeLock';
let chromeHideTimer = null;
let chromePinned = false;       // true while hovering the bar itself
let chromeLocked = false;       // true after next/prev until cursor leaves edges

function isProjectPage() {
    return document.body.getAttribute('data-project') !== null;
}

function setChromeVisible(visible) {
    if (!isProjectPage()) return;
    // While locked (post-navigation), never show
    if (chromeLocked && visible) return;
    document.body.classList.toggle('chrome-visible', !!visible);
}

function scheduleChromeHide() {
    clearTimeout(chromeHideTimer);
    if (chromePinned || chromeLocked) return;
    chromeHideTimer = setTimeout(() => {
        if (!chromePinned && !chromeLocked) setChromeVisible(false);
    }, CHROME_HIDE_DELAY);
}

/** Call before navigating to another project — keeps chrome hidden on the next page. */
function lockChromeForNavigation() {
    try {
        sessionStorage.setItem(CHROME_LOCK_KEY, '1');
    } catch (_) {}
    chromeLocked = true;
    chromePinned = false;
    clearTimeout(chromeHideTimer);
    setChromeVisible(false);
    document.body.classList.remove('chrome-visible');
}

function consumeChromeLock() {
    try {
        if (sessionStorage.getItem(CHROME_LOCK_KEY) === '1') {
            sessionStorage.removeItem(CHROME_LOCK_KEY);
            return true;
        }
    } catch (_) {}
    return false;
}

function initChromeAutoHide() {
    if (!isProjectPage()) return;

    // Default: always hidden — clean project slide
    document.body.classList.add('chrome-autohide');
    setChromeVisible(false);

    // After next/prev navigation, stay locked until mouse leaves top/bottom edges
    chromeLocked = consumeChromeLock();
    if (chromeLocked) {
        document.body.classList.remove('chrome-visible');
    }

    document.addEventListener('mousemove', (e) => {
        const h = window.innerHeight;
        const nearTop = e.clientY <= CHROME_EDGE_PX;
        const nearBottom = e.clientY >= h - CHROME_EDGE_PX;
        const nearEdge = nearTop || nearBottom;

        if (chromeLocked) {
            // Unlock only once the cursor has left both edges
            if (!nearEdge) {
                chromeLocked = false;
            }
            // Still locked (or just unlocked but not near): keep hidden
            if (chromeLocked || !nearEdge) {
                setChromeVisible(false);
                return;
            }
        }

        if (nearEdge || chromePinned) {
            setChromeVisible(true);
            clearTimeout(chromeHideTimer);
        } else {
            scheduleChromeHide();
        }
    });

    // Stay open while the cursor is on the bar (only if not locked)
    const topbar = document.querySelector('.topbar');
    const bottom = document.querySelector('.bottom-bar');
    [topbar, bottom].forEach(el => {
        if (!el) return;
        el.addEventListener('mouseenter', () => {
            if (chromeLocked) return;
            chromePinned = true;
            setChromeVisible(true);
            clearTimeout(chromeHideTimer);
        });
        el.addEventListener('mouseleave', () => {
            chromePinned = false;
            scheduleChromeHide();
        });
    });

    // Prev / Next links — lock chrome so the next page does not flash bars
    document.querySelectorAll('#prevBtn, #nextBtn').forEach(a => {
        a.addEventListener('click', () => {
            lockChromeForNavigation();
        });
    });
}


/* =========================================================
   INIT
========================================================= */

function initApp() {
    if (typeof ARTIST === 'undefined' || typeof PROJECTS === 'undefined') {
        console.error('data.js failed to load (ARTIST / PROJECTS missing)');
        showToast('DATA.JS MISSING');
        return;
    }
    loadTheme();
    applyFont();
    applyHeader();
    initSidebar();
    buildSidebar();
    buildLanding();
    applyHomeContent();
    applyEndContent();
    initChromeAutoHide();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
