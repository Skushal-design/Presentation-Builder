"""
Artist Showcase — data.js Editor (PySide6) + Pass Breakdown tab
A modern GUI to edit js/data.js without touching code.

Features:
  - Robust load: auto-repairs non-JSON data.js (unquoted keys, trailing commas,
    single quotes, JS comments) before parsing.
  - Safe save: always writes strict JSON-compatible output + automatic backup.
  - Auto-generates / regenerates projects/project-XX.html from template.
  - Validate missing videos, images, HTML pages.
  - Export / import JSON; CLI flags for repair, validate, regenerate, backup.
  - Asset copy on browse (videos / images).

Run:  python editor.py
"""

import json
from pathlib import Path
import re
import os
import sys
import shutil
from pathlib import Path

# ---------------- Optional GUI (PySide6) — not required for CLI ----------------
HAS_QT = False
try:
    from PySide6.QtCore import Qt, QSize, QRect, QTimer
    from PySide6.QtGui import QPixmap, QIcon, QFont, QAction, QColor, QKeySequence, QPainter, QPen, QBrush, QTextCharFormat, QTextCursor
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QTextEdit, QPushButton, QComboBox, QListWidget,
        QListWidgetItem, QFileDialog, QMessageBox, QSplitter, QFormLayout,
        QGroupBox, QScrollArea, QFrame, QStatusBar, QToolBar, QSizePolicy,
        QInputDialog,
        QCheckBox,
        QTabWidget,
        QGridLayout,
        QMenu,
        QToolButton,
        QDialog,
        QDialogButtonBox,
        QDockWidget,
    )
    HAS_QT = True
except ImportError:
    # Stubs so CLI (--init, --repair, …) works without PySide6
    QMainWindow = object  # type: ignore
    QWidget = object  # type: ignore
    QFrame = object  # type: ignore
    QLabel = object  # type: ignore
    QLineEdit = object  # type: ignore
    QTextEdit = object  # type: ignore
    QPushButton = object  # type: ignore
    QComboBox = object  # type: ignore
    QListWidget = object  # type: ignore
    QListWidgetItem = object  # type: ignore
    QFileDialog = object  # type: ignore
    QMessageBox = object  # type: ignore
    QSplitter = object  # type: ignore
    QFormLayout = object  # type: ignore
    QGroupBox = object  # type: ignore
    QScrollArea = object  # type: ignore
    QStatusBar = object  # type: ignore
    QToolBar = object  # type: ignore
    QSizePolicy = object  # type: ignore
    QInputDialog = object  # type: ignore
    QCheckBox = object  # type: ignore
    QTabWidget = object  # type: ignore
    QGridLayout = object  # type: ignore
    QVBoxLayout = object  # type: ignore
    QHBoxLayout = object  # type: ignore
    QApplication = object  # type: ignore
    Qt = type("Qt", (), {"AlignmentFlag": type("AF", (), {}), "Orientation": type("O", (), {}), "TextFlag": type("TF", (), {})})()  # type: ignore
    QSize = object  # type: ignore
    QRect = object  # type: ignore
    QTimer = object  # type: ignore
    QPixmap = object  # type: ignore
    QIcon = object  # type: ignore
    QFont = object  # type: ignore
    QAction = object  # type: ignore
    QColor = object  # type: ignore
    QKeySequence = object  # type: ignore
    QPainter = object  # type: ignore
    QPen = object  # type: ignore
    QBrush = object  # type: ignore

# ---------------- Optional Pillow for thumbnails ----------------
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ---------------- Paths ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_JS = os.path.join(BASE_DIR, "js", "data.js")
ASSETS_VIDEOS = os.path.join(BASE_DIR, "assets", "videos")
ASSETS_IMAGES = os.path.join(BASE_DIR, "assets", "images")
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

STANDARD_DETAIL_KEYS = ("ROLE", "TASK", "DURATION", "OUTPUT")

CACHE_BUSTER = "20260929a"

# ---- Embedded shell templates (generated) ----
TEMPLATE_INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Artist Showcase 2026</title>
    <link rel="stylesheet" href="css/style.css?v=20260924i">
</head>

<body class="theme-dark">

<div id="app">

    <header class="topbar">
        <div class="topbar-left">
            <button class="sidebar-toggle-btn" onclick="toggleSidebar()" title="Toggle sidebar (S)">
                <span class="hamburger-line"></span>
                <span class="hamburger-line"></span>
                <span class="hamburger-line"></span>
            </button>
        </div>

        <div class="topbar-center">
            <div class="brand">ARTIST SHOWCASE · 2026</div>
        </div>

        <div class="topbar-right">
            <button class="theme-toggle-btn" id="themeToggleBtn" onclick="toggleTheme()" title="Toggle theme (T)">
                <span class="theme-icon">☀</span>
            </button>
        </div>
    </header>

    <div class="layout">

        <aside class="sidebar collapsed" id="sidebar">
            <div class="sidebar-header">
                <span class="sidebar-title">PROJECTS</span>
            </div>
            <nav class="sidebar-nav" id="sidebarNav"></nav>
            <div class="sidebar-footer">
                <div class="artist-info-mini">
                    <div class="artist-name-mini" id="sidebarArtistName"></div>
                    <div class="artist-role-mini" id="sidebarArtistRole"></div>
                </div>
            </div>
        </aside>

        <main class="content">
            <section class="landing-screen">
                <div class="landing-main">
                    <div class="eyebrow">COMPANY CREATIVE SHOWCASE</div>
                    <h1 class="main-heading">SHADING DEPARTMENT<br>SHOWCASE</h1>
                    <!-- Filled dynamically from ARTIST + PROJECTS in data.js -->
                    <div class="artist-grid"></div>
                </div>
                <div class="landing-media" id="homeMedia" style="display:none" aria-hidden="true"></div>
            </section>
        </main>
    </div>

    <div class="toast" id="toast">READY</div>
</div>

<script src="js/data.js?v=20260924i"></script>
<script src="js/main.js?v=20260924i"></script>
</body>
</html>
"""

TEMPLATE_THANKS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Thank You · Artist Showcase 2026</title>
    <link rel="stylesheet" href="css/style.css?v=20260924i">
</head>

<body class="theme-dark" data-page="thanks">

<div id="app">

    <header class="topbar">
        <div class="topbar-left">
            <button class="sidebar-toggle-btn" onclick="toggleSidebar()" title="Toggle sidebar (S)">
                <span class="hamburger-line"></span>
                <span class="hamburger-line"></span>
                <span class="hamburger-line"></span>
            </button>
        </div>
        <div class="topbar-center">
            <div class="brand">ARTIST SHOWCASE · 2026</div>
        </div>
        <div class="topbar-right">
            <button class="theme-toggle-btn" id="themeToggleBtn" onclick="toggleTheme()" title="Toggle theme (T)">
                <span class="theme-icon">☀</span>
            </button>
        </div>
    </header>

    <div class="layout">
        <aside class="sidebar collapsed" id="sidebar">
            <div class="sidebar-header">
                <span class="sidebar-title">PROJECTS</span>
            </div>
            <nav class="sidebar-nav" id="sidebarNav"></nav>
            <div class="sidebar-footer">
                <div class="artist-info-mini">
                    <div class="artist-name-mini" id="sidebarArtistName"></div>
                    <div class="artist-role-mini" id="sidebarArtistRole"></div>
                </div>
                <a class="back-home-btn" href="index.html">← HOME</a>
            </div>
        </aside>

        <main class="content">
            <section class="thanks-screen" id="thanksScreen">
                <div class="eyebrow" id="thanksEyebrow">WITH GRATITUDE</div>
                <h1 class="thanks-heading" id="thanksHeading">THANK YOU</h1>
                <p class="thanks-sub" id="thanksSub">TO EVERY DEPARTMENT THAT MADE THIS POSSIBLE</p>
                <p class="thanks-note" id="thanksNote"></p>
                <div class="thanks-grid" id="thanksGrid"></div>
                <div class="thanks-actions">
                    <a class="end-btn" href="index.html">← HOME</a>
                    <a class="end-btn end-btn-primary" id="thanksContinueBtn" href="#">CONTINUE →</a>
                </div>
            </section>
        </main>
    </div>

    <footer class="bottom-bar">
        <a class="bottom-button" href="index.html">← HOME</a>
        <div class="help-text">← HOME · → CONTINUE · S SIDEBAR · T THEME</div>
        <a class="bottom-button" id="thanksNextBtn" href="#">CONTINUE →</a>
    </footer>

    <div class="toast" id="toast">READY</div>
</div>

<script src="js/data.js?v=20260924i"></script>
<script src="js/main.js?v=20260924i"></script>
<script>
(function () {
    const thanks = (typeof THANKS !== 'undefined') ? THANKS : null;
    if (thanks && thanks.enabled === false) {
        const first = (typeof PROJECTS !== 'undefined' && PROJECTS.length)
            ? ('projects/' + PROJECTS[0].file)
            : 'index.html';
        window.location.replace(first);
        return;
    }

    const firstProjectHref = (typeof PROJECTS !== 'undefined' && PROJECTS.length)
        ? ('projects/' + PROJECTS[0].file)
        : 'index.html';

    const continueBtn = document.getElementById('thanksContinueBtn');
    const nextBtn = document.getElementById('thanksNextBtn');
    if (continueBtn) continueBtn.href = firstProjectHref;
    if (nextBtn) nextBtn.href = firstProjectHref;

    if (thanks) {
        const set = (id, val) => {
            const el = document.getElementById(id);
            if (el && val != null) el.textContent = val;
        };
        set('thanksEyebrow', thanks.eyebrow);
        set('thanksHeading', thanks.heading);
        set('thanksSub', thanks.sub);
        set('thanksNote', thanks.note);

        const grid = document.getElementById('thanksGrid');
        if (grid && Array.isArray(thanks.departments)) {
            grid.innerHTML = '';
            thanks.departments.forEach((d) => {
                const card = document.createElement('div');
                card.className = 'thanks-card';
                card.innerHTML =
                    '<div class="thanks-dept">' + (d.name || '') + '</div>' +
                    '<p class="thanks-dept-text">' + (d.text || '') + '</p>';
                grid.appendChild(card);
            });
        }
    }

    document.addEventListener('keydown', (e) => {
        const tag = (e.target && e.target.tagName) || '';
        if (tag === 'INPUT' || tag === 'TEXTAREA') return;
        if (e.key === 'ArrowRight') window.location.href = firstProjectHref;
        if (e.key === 'ArrowLeft' || e.key === 'Home') window.location.href = 'index.html';
    });
})();
</script>
</body>
</html>
"""

TEMPLATE_END_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>End · Artist Showcase 2026</title>
    <link rel="stylesheet" href="../css/style.css?v=20260924i">
</head>

<!-- Terminal slide — always last, not listed in PROJECTS -->
<body class="theme-dark" data-project="end">

<div id="app">

    <header class="topbar">
        <div class="topbar-left">
            <button class="sidebar-toggle-btn" onclick="toggleSidebar()" title="Toggle sidebar (S)">
                <span class="hamburger-line"></span>
                <span class="hamburger-line"></span>
                <span class="hamburger-line"></span>
            </button>
        </div>
        <div class="topbar-center">
            <div class="brand">ARTIST SHOWCASE · 2026</div>
        </div>
        <div class="topbar-right">
            <button class="theme-toggle-btn" id="themeToggleBtn" onclick="toggleTheme()" title="Toggle theme (T)">
                <span class="theme-icon">☀</span>
            </button>
        </div>
    </header>

    <div class="layout">
        <aside class="sidebar collapsed" id="sidebar">
            <div class="sidebar-header">
                <span class="sidebar-title">PROJECTS</span>
            </div>
            <nav class="sidebar-nav" id="sidebarNav"></nav>
            <div class="sidebar-footer">
                <div class="artist-info-mini">
                    <div class="artist-name-mini" id="sidebarArtistName"></div>
                    <div class="artist-role-mini" id="sidebarArtistRole"></div>
                </div>
                <a class="back-home-btn" href="../index.html">← HOME</a>
            </div>
        </aside>

        <main class="content">
            <section class="end-screen">
                <div class="end-main">
                    <div class="eyebrow">PRESENTATION COMPLETE</div>
                    <h1 class="end-heading">THANK YOU</h1>
                    <p class="end-sub" id="endArtistLine"></p>
                    <p class="end-note">...</p>
                    <div class="end-actions">
                        <a class="end-btn" id="endReplayBtn" href="#">← LAST PROJECT</a>
                        <a class="end-btn end-btn-primary" href="../index.html">HOME</a>
                    </div>
                </div>
                <div class="end-media" id="endMedia" style="display:none" aria-hidden="true"></div>
            </section>
        </main>
    </div>

    <footer class="bottom-bar">
        <a class="bottom-button" id="prevBtn" href="#">← PREVIOUS</a>
        <div class="help-text">← BACK · H HOME · S SIDEBAR · T THEME</div>
        <a class="bottom-button" id="nextBtn" href="../index.html">HOME →</a>
    </footer>

    <div class="toast" id="toast">READY</div>
</div>

<script src="../js/data.js?v=20260924i"></script>
<script src="../js/main.js?v=20260924i"></script>
<script>
(function () {
    // Wire end-slide navigation from PROJECTS (always after the last real project)
    const last = (typeof PROJECTS !== 'undefined' && PROJECTS.length)
        ? PROJECTS[PROJECTS.length - 1]
        : null;

    const prevBtn = document.getElementById('prevBtn');
    const replay = document.getElementById('endReplayBtn');
    if (last) {
        if (prevBtn) prevBtn.href = last.file;
        if (replay) replay.href = last.file;
    } else {
        if (prevBtn) prevBtn.href = '../index.html';
        if (replay) replay.href = '../index.html';
    }

    const line = document.getElementById('endArtistLine');
    if (line && typeof ARTIST !== 'undefined') {
        line.textContent = [ARTIST.name, ARTIST.role].filter(Boolean).join('  ·  ');
    }

    // Keyboard: left → last project, right/home → index
    document.addEventListener('keydown', (e) => {
        const tag = (e.target && e.target.tagName) || '';
        if (tag === 'INPUT' || tag === 'TEXTAREA') return;
        if (e.key === 'ArrowLeft' && last) {
            if (typeof lockChromeForNavigation === 'function') lockChromeForNavigation();
            window.location.href = last.file;
        }
        if (e.key === 'ArrowRight' || e.key === 'Home') {
            window.location.href = '../index.html';
        }
    });
})();
</script>
</body>
</html>
"""

TEMPLATE_STYLE_CSS = """/* =========================================================
   THEMES
========================================================= */

:root {
    /* ---------- DARK (default) ---------- */
    --bg-primary: #000000;
    --bg-secondary: #0a0a0a;
    --bg-tertiary: #111111;
    --bg-card: rgba(255, 215, 0, 0.04);
    --bg-card-hover: rgba(255, 215, 0, 0.10);
    --bg-sidebar: #050505;
    --bg-overlay: rgba(0, 0, 0, 0.92);

    --text-primary: #ffffff;
    --text-secondary: #f5e6b8;
    --text-accent: #d4af37;
    --text-muted: #b8962e;
    --text-dim: #8a7222;
    --text-sidebar: #d4af37;

    --border-accent: rgba(255, 215, 0, 0.25);
    --border-strong: rgba(255, 215, 0, 0.5);
    --border-subtle: rgba(255, 215, 0, 0.15);

    --progress-bg: #2a220e;
    --progress-fill: #d4af37;

    --grid-color: rgba(255, 215, 0, 0.04);
    --glow-color: rgba(255, 215, 0, 0.05);

    --radius-sm: 0px;
    --radius-md: 0px;
    --radius-lg: 0px;
    --shadow-sm: none;
    --shadow-md: none;

    --sidebar-width: 280px;

    /* Font sizes — bumped up slightly */
    --fs-micro: 10px;   /* was 8px */
    --fs-tiny: 11px;    /* was 9px  */
    --fs-small: 13px;   /* was 11px */
    --fs-body: 15px;    /* was 14px */
}

/* =========================================================
   LIGHT — REFINED MICROSOFT FLUENT STYLE
========================================================= */
body.theme-light {
    /* Surfaces — layered like Windows 11 */
    --bg-primary: #faf9f7;         /* soft warm off-white */
    --bg-secondary: #ffffff;       /* card surface */
    --bg-tertiary: #f5f3ef;
    --bg-card: #ffffff;
    --bg-card-hover: #f7f5f1;
    --bg-sidebar: #f5f3ef;
    --bg-overlay: rgba(250, 249, 247, 0.90);

    /* Text — deeper contrast */
    --text-primary: #0d0d0d;
    --text-secondary: #2a2a2a;
    --text-accent: #b8860b;        /* richer dark gold */
    --text-muted: #6b6b6b;
    --text-dim: #8a8a8a;
    --text-sidebar: #1a1a1a;

    /* Borders — soft */
    --border-accent: #e8e3d8;
    --border-strong: #d4cdb8;
    --border-subtle: #f0ece2;

    /* Progress */
    --progress-bg: #e8e3d8;
    --progress-fill: #b8860b;

    /* Backgrounds */
    --grid-color: rgba(184, 134, 11, 0.04);
    --glow-color: rgba(184, 134, 11, 0.05);

    /* Shape + shadows (Fluent) */
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.06);
    --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04);
}

/* =========================================================
   RESET
========================================================= */

* { margin: 0; padding: 0; box-sizing: border-box; }

html, body {
    width: 100%; height: 100%;
    overflow: hidden;
}

body {
    background: var(--bg-primary);
    color: var(--text-secondary);
    font-family: var(--app-font, "Segoe UI", Arial, Helvetica, sans-serif);
    font-size: var(--fs-small);
    user-select: none;
    -webkit-font-smoothing: antialiased;
    transition: background 0.3s ease, color 0.3s ease;
}

#app {
    width: 100vw; height: 100vh;
    position: relative; overflow: hidden;
    background:
        radial-gradient(circle at 75% 20%, var(--glow-color), transparent 40%),
        radial-gradient(circle at 20% 80%, var(--glow-color), transparent 40%),
        var(--bg-primary);
    transition: background 0.3s ease;
}

#app::before {
    content: ""; position: absolute; inset: 0;
    background-image:
        linear-gradient(var(--grid-color) 1px, transparent 1px),
        linear-gradient(90deg, var(--grid-color) 1px, transparent 1px);
    background-size: 50px 50px;
    pointer-events: none; z-index: 0;
    opacity: 0; /* clean slide — grid off */
}

/* =========================================================
   TOP BAR — Brand centered
========================================================= */

.topbar {
    position: absolute; left: 0; top: 0;
    width: 100%; height: 56px;
    padding: 0 28px;
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    border-bottom: 1px solid var(--border-accent);
    z-index: 100;
    background: var(--bg-primary);
    backdrop-filter: blur(12px);
    transition:
        background 0.3s ease,
        border-color 0.3s ease,
        transform 0.35s ease,
        opacity 0.35s ease;
    will-change: transform, opacity;
}

/* Menu-bar accent line */
.topbar::after {
    content: "";
    position: absolute;
    left: 0; right: 0; bottom: -1px;
    height: 1px;
    background: linear-gradient(
        90deg,
        transparent 0%,
        var(--border-strong) 20%,
        var(--text-accent) 50%,
        var(--border-strong) 80%,
        transparent 100%
    );
    opacity: 0.55;
    pointer-events: none;
}

.topbar-left {
    display: flex;
    align-items: center;
    gap: 12px;
    justify-self: start;
}

.topbar-center {
    justify-self: center;
    text-align: center;
    display: flex;
    align-items: center;
    gap: 16px;
}

.topbar-right {
    display: flex;
    align-items: center;
    gap: 10px;
    justify-self: end;
}

.brand {
    font-size: var(--fs-tiny);
    letter-spacing: 4px;
    color: var(--text-accent);
    font-weight: 700;
    white-space: nowrap;
    padding: 6px 12px;
    border-radius: var(--radius-sm);
    transition: background 0.2s ease, color 0.2s ease;
}

.brand:hover {
    background: var(--bg-card-hover);
}

/* Menu-style items (optional nav chips in topbar) */
.topbar-menu {
    display: flex;
    align-items: center;
    gap: 4px;
}

.topbar-menu-item {
    appearance: none;
    background: transparent;
    border: 1px solid transparent;
    color: var(--text-muted);
    font-size: var(--fs-tiny);
    font-weight: 600;
    letter-spacing: 1.5px;
    padding: 7px 12px;
    cursor: pointer;
    border-radius: var(--radius-sm);
    text-decoration: none;
    transition: 0.2s;
    white-space: nowrap;
}

.topbar-menu-item:hover {
    color: var(--text-primary);
    background: var(--bg-card-hover);
    border-color: var(--border-subtle);
}

.topbar-menu-item.active {
    color: var(--text-accent);
    border-color: var(--border-accent);
    background: var(--bg-card);
}

.sidebar-toggle-btn {
    background: transparent;
    border: 1px solid transparent;
    color: var(--text-accent);
    width: 34px; height: 34px;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 4px; cursor: pointer; padding: 0;
    border-radius: var(--radius-sm);
    transition: 0.2s;
}

.sidebar-toggle-btn:hover {
    background: var(--bg-card-hover);
    border-color: var(--border-accent);
}

.hamburger-line {
    width: 15px; height: 1.5px;
    background: var(--text-accent);
    transition: 0.2s;
}

.theme-toggle-btn {
    background: transparent;
    border: 1px solid transparent;
    color: var(--text-accent);
    width: 34px; height: 34px;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; font-size: 15px;
    border-radius: var(--radius-sm);
    transition: 0.2s;
}

.theme-toggle-btn:hover {
    background: var(--bg-card-hover);
    border-color: var(--border-accent);
}

.page-counter {
    font-size: var(--fs-tiny);
    letter-spacing: 3px;
    color: var(--text-accent);
    font-weight: 600;
}
.page-counter strong { color: var(--text-primary); }

/* =========================================================
   LAYOUT
========================================================= */

.layout {
    position: absolute;
    left: 0; top: 56px; right: 0; bottom: 75px;
    display: flex; z-index: 5;
    transition: top 0.35s ease, bottom 0.35s ease;
}

/* Auto-hide chrome (header + footer) — project pages only via body class */
body.chrome-autohide .topbar {
    transform: translateY(-100%);
    opacity: 0;
    pointer-events: none;
}
body.chrome-autohide .bottom-bar {
    transform: translateY(100%);
    opacity: 0;
    pointer-events: none;
}
body.chrome-autohide .layout {
    top: 0;
    bottom: 0;
}

/* Show chrome when mouse is near edges or forced visible */
body.chrome-visible .topbar,
body.chrome-autohide.chrome-visible .topbar {
    transform: translateY(0);
    opacity: 1;
    pointer-events: auto;
}
body.chrome-visible .bottom-bar,
body.chrome-autohide.chrome-visible .bottom-bar {
    transform: translateY(0);
    opacity: 1;
    pointer-events: auto;
}
body.chrome-visible .layout,
body.chrome-autohide.chrome-visible .layout {
    top: 56px;
    bottom: 75px;
}

body.theme-light .topbar {
    background: rgba(250, 249, 247, 0.92);
}
body.theme-dark .topbar {
    background: rgba(0, 0, 0, 0.88);
}

/* Landing page: always show chrome (no autohide class applied) */

/* =========================================================
   SIDEBAR — hidden by default (JS adds .collapsed)
========================================================= */

.sidebar {
    width: var(--sidebar-width);
    height: 100%;
    background: var(--bg-sidebar);
    border-right: 1px solid var(--border-accent);
    display: flex; flex-direction: column;
    transition: width 0.35s ease, opacity 0.25s ease,
                background 0.3s ease, border-color 0.3s ease;
    overflow: hidden; flex-shrink: 0;
}

.sidebar.collapsed {
    width: 0; opacity: 0;
    border-right: none; pointer-events: none;
}

.sidebar-header {
    padding: 22px;
    border-bottom: 1px solid var(--border-subtle);
    flex-shrink: 0;
}

.sidebar-title {
    font-size: var(--fs-tiny);
    letter-spacing: 3px;
    color: var(--text-dim);
    font-weight: 700;
}

.sidebar-nav { flex: 1; overflow-y: auto; padding: 12px 0; }

.sidebar-project-link {
    display: flex; align-items: center; gap: 14px;
    padding: 14px 22px;
    cursor: pointer;
    border-left: 3px solid transparent;
    transition: 0.2s;
    color: var(--text-sidebar);
    font-size: var(--fs-small);
    letter-spacing: 1.5px;
    font-weight: 600;
    text-decoration: none;
}

body.theme-dark .sidebar-project-link:hover,
body.theme-dark .sidebar-project-link.active {
    background: var(--bg-card-hover);
    border-left-color: var(--text-accent);
    color: var(--text-primary);
}

body.theme-light .sidebar-project-link:hover,
body.theme-light .sidebar-project-link.active {
    background: var(--bg-card-hover);
    border-left-color: var(--text-accent);
    color: var(--text-accent);
}

.sidebar-project-num {
    font-size: var(--fs-tiny);
    color: var(--text-dim);
    font-weight: 700;
    letter-spacing: 2px;
    min-width: 24px;
}

.sidebar-project-link.active .sidebar-project-num {
    color: var(--text-accent);
}

.sidebar-project-name {
    flex: 1; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis;
}

.sidebar-footer {
    padding: 18px 22px;
    border-top: 1px solid var(--border-subtle);
    flex-shrink: 0;
}

.artist-info-mini { margin-bottom: 14px; }

.artist-name-mini {
    font-size: var(--fs-small);
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: 1px;
    margin-bottom: 4px;
}

.artist-role-mini {
    font-size: var(--fs-micro);
    color: var(--text-dim);
    letter-spacing: 2px;
    font-weight: 600;
}

.back-home-btn {
    display: block;
    background: transparent;
    border: 1px solid var(--border-accent);
    color: var(--text-accent);
    padding: 10px 16px;
    font-size: var(--fs-tiny);
    font-weight: 600;
    letter-spacing: 2px;
    cursor: pointer;
    transition: 0.2s;
    width: 100%; text-align: center;
    text-decoration: none;
    border-radius: var(--radius-sm);
}

.back-home-btn:hover {
    background: var(--text-accent);
    color: var(--bg-secondary);
    border-color: var(--text-accent);
}

/* =========================================================
   CONTENT
========================================================= */

.content {
    flex: 1; position: relative;
    overflow: hidden; min-width: 0;
}

/* Landing */
.landing-screen {
    height: 100%;
    width: 100%;
    padding: 6vh 8%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    box-sizing: border-box;
}
.landing-main {
    width: 100%;
    max-width: 780px;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
}
.end-main {
    width: 100%;
    max-width: 720px;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
}

.eyebrow {
    font-size: 11px;
    letter-spacing: 5px;
    color: var(--text-accent);
    font-weight: 600;
    margin-bottom: 18px;
    text-transform: uppercase;
}

.main-heading {
    font-size: clamp(42px, 6.5vw, 96px);
    line-height: 0.95;
    font-weight: 300;
    letter-spacing: -2px;
    margin-bottom: 42px;
    color: var(--text-primary);
}

.artist-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 18px;
    max-width: 420px;
    width: 100%;
    justify-items: center;
}

.artist-card {
    position: relative;
    width: 100%;
    max-width: 420px;
    min-height: 160px;
    padding: 28px 32px;
    background: rgba(20, 18, 12, 0.55);
    border: 1px solid var(--border-accent);
    cursor: pointer;
    overflow: hidden;
    transition: 0.3s;
    text-align: center;
    text-decoration: none;
    color: inherit;
    border-radius: 2px;
    box-shadow: var(--shadow-sm);
}

.artist-card:hover {
    background: var(--bg-card-hover);
    border-color: var(--border-strong);
    transform: translateY(-3px);
    box-shadow: var(--shadow-md);
}

.artist-number {
    font-size: var(--fs-small);
    letter-spacing: 3px;
    color: var(--text-muted);
    font-weight: 600;
    margin-bottom: 35px;
}

.artist-card h2 {
    font-size: 36px;
    font-weight: 400;
    letter-spacing: -1px;
    margin-bottom: 14px;
    color: var(--text-primary);
}

.artist-card p {
    color: var(--text-accent);
    font-size: var(--fs-small);
    letter-spacing: 2px;
    font-weight: 600;
    text-transform: uppercase;
}

.artist-arrow {
    position: absolute; right: 25px; bottom: 22px;
    font-size: 18px;
    color: var(--text-muted);
    transition: 0.3s;
}
.artist-card:hover .artist-arrow {
    color: var(--text-primary);
    transform: translateX(6px);
}

/* =========================================================
   PROJECT AREA — with sticky title
========================================================= */

.project-area {
    height: 100%;
    overflow-y: auto;
    position: relative;
}

/* STICKY TITLE ROW — number left | TITLE center | category right */
.project-title-row {
    position: sticky;
    top: 0;
    z-index: 20;
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 16px;
    padding: 18px 6% 16px;
    margin-bottom: 18px;
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border-subtle);
    backdrop-filter: blur(10px);
    transition: background 0.3s ease, border-color 0.3s ease;
}

body.theme-light .project-title-row {
    background: rgba(250, 249, 247, 0.92);
}

body.theme-dark .project-title-row {
    background: rgba(0, 0, 0, 0.85);
}

/* Left: project number */
.project-title-row .section-label,
.project-title-row #projectNumber {
    justify-self: start;
    text-align: left;
    margin-bottom: 0;
    white-space: nowrap;
}

/* Center stack: title + artist name underneath */
.project-title-stack {
    justify-self: center;
    grid-column: 2;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    min-width: 0;
}

.project-title {
    font-size: clamp(28px, 3.5vw, 48px);
    font-weight: 300;
    letter-spacing: -2px;
    color: var(--text-primary);
    line-height: 1;
    text-align: center;
    margin: 0;
    white-space: nowrap;
}

.project-title-stack .project-artist {
    margin-top: 0;
    font-size: clamp(11px, 1.1vw, 14px);
    letter-spacing: 2.5px;
    font-weight: 600;
    color: var(--text-accent);
    text-transform: uppercase;
    text-align: center;
    opacity: 0.95;
}

.project-title-stack .project-artist.is-override::before {
    content: "";
}

/* Right: category */
.project-category {
    justify-self: end;
    grid-column: 3;
    text-align: right;
    color: var(--text-accent);
    font-size: var(--fs-tiny);
    font-weight: 600;
    letter-spacing: 2px;
    line-height: 1.5;
    max-width: 100%;
}

/* content below the sticky header */
.project-grid {
    display: grid;
    grid-template-columns: 34% 66%;
    gap: 35px;
    padding: 0 6% 60px;
}

.project-description { padding-right: 20px; }

.section-label {
    color: var(--text-accent);
    font-size: var(--fs-tiny);
    font-weight: 700;
    letter-spacing: 3px;
    margin-bottom: 14px;
}

.description-text {
    color: var(--text-secondary);
    font-size: var(--fs-body);
    line-height: 1.75;
    margin-bottom: 30px;
}

/* =========================================================
   DETAILS
========================================================= */

.details-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    border-top: 1px solid var(--border-subtle);
}

.detail {
    padding: 15px 8px 15px 0;
    border-bottom: 1px solid var(--border-subtle);
}

.detail-label {
    font-size: var(--fs-micro);
    color: var(--text-muted);
    font-weight: 700;
    letter-spacing: 2px;
    margin-bottom: 6px;
}

.detail-value {
    font-size: var(--fs-small);
    color: var(--text-primary);
    font-weight: 500;
}

/* =========================================================
   TOOLS
========================================================= */

.tools { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 25px; }

.tool {
    padding: 7px 12px;
    border: 1px solid var(--border-accent);
    color: var(--text-accent);
    font-size: var(--fs-tiny);
    font-weight: 600;
    letter-spacing: 1px;
    border-radius: var(--radius-sm);
    background: var(--bg-card);
}

/* =========================================================
   VIDEO
========================================================= */

.media-area { min-width: 0; }

.video-wrapper {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    background: #000;
    border: 1px solid var(--border-strong);
    overflow: hidden;
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md);
}

.video-wrapper video {
    display: block;
    width: 100%; height: 100%;
    object-fit: contain;
    background: #000;
}

.video-poster-overlay {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    z-index: 2;
    cursor: pointer;
    background: #000;
    transition: opacity 0.25s ease;
}
.video-poster-overlay.is-hidden {
    opacity: 0;
    pointer-events: none;
}


.media-label {
    position: absolute; left: 15px; top: 15px; z-index: 3;
    padding: 7px 12px;
    background: rgba(0, 0, 0, 0.85);
    border: 1px solid var(--border-strong);
    font-size: var(--fs-tiny);
    font-weight: 700;
    letter-spacing: 2px;
    color: #d4af37;
    pointer-events: none;
    border-radius: var(--radius-sm);
}

.video-controls {
    display: flex; align-items: center;
    gap: 8px; padding: 14px 0;
}

.control-btn {
    background: var(--bg-card);
    border: 1px solid var(--border-accent);
    color: var(--text-accent);
    padding: 9px 12px;
    cursor: pointer;
    font-size: var(--fs-tiny);
    font-weight: 600;
    letter-spacing: 1px;
    transition: 0.2s;
    border-radius: var(--radius-sm);
}

.control-btn:hover {
    color: var(--bg-secondary);
    background: var(--text-accent);
    border-color: var(--text-accent);
}

.progress {
    flex: 1;
    height: 4px;
    background: var(--progress-bg);
    cursor: pointer;
    border-radius: 2px;
    overflow: hidden;
}

.progress-bar {
    width: 0%; height: 100%;
    background: var(--progress-fill);
    transition: width 0.1s linear;
}

/* =========================================================
   CHAPTERS
========================================================= */

.chapters {
    display: flex; flex-wrap: wrap;
    gap: 7px; margin-top: 8px; margin-bottom: 35px;
}

.chapter {
    border: 1px solid var(--border-accent);
    background: transparent;
    color: var(--text-muted);
    padding: 8px 13px;
    cursor: pointer;
    font-size: var(--fs-tiny);
    font-weight: 600;
    letter-spacing: 1px;
    transition: 0.2s;
    border-radius: var(--radius-sm);
}

.chapter:hover {
    color: var(--bg-secondary);
    background: var(--text-accent);
    border-color: var(--text-accent);
}

/* =========================================================
   BREAKDOWN
========================================================= */

.breakdown-section {
    margin-top: 30px;
    border-top: 1px solid var(--border-subtle);
    padding-top: 25px;
}

.breakdown-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
}

.breakdown-card {
    min-height: 110px;
    padding: 18px;
    border: 1px solid var(--border-subtle);
    background: var(--bg-card);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-sm);
}

.breakdown-card span {
    display: block;
    font-size: var(--fs-micro);
    font-weight: 700;
    letter-spacing: 2px;
    color: var(--text-muted);
    margin-bottom: 14px;
}

.breakdown-card strong {
    font-size: var(--fs-small);
    font-weight: 500;
    color: var(--text-primary);
}

/* =========================================================
   GALLERY
========================================================= */

.gallery {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-top: 15px;
}

.gallery img {
    width: 100%;
    aspect-ratio: 16 / 9;
    object-fit: cover;
    border: 1px solid var(--border-accent);
    cursor: pointer;
    transition: 0.25s;
    border-radius: var(--radius-sm);
}

.gallery img:hover {
    opacity: 0.85;
    transform: scale(0.98);
    border-color: var(--text-accent);
}

/* =========================================================
   LIGHTBOX
========================================================= */

.lightbox {
    position: fixed; inset: 0;
    background: var(--bg-overlay);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 500;
    backdrop-filter: blur(6px);
}

.lightbox.active { display: flex; }

.lightbox img {
    max-width: 90vw;
    max-height: 85vh;
    object-fit: contain;
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md);
}

.lightbox-close {
    position: absolute; right: 30px; top: 25px;
    color: var(--text-accent);
    font-size: 28px;
    cursor: pointer;
}

/* =========================================================
   BEFORE / AFTER
========================================================= */

.compare {
    position: relative;
    aspect-ratio: 16 / 9;
    overflow: hidden;
    margin-top: 15px;
    background: #0a0a0a;
    border: 1px solid var(--border-accent);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md);
}

.compare img {
    position: absolute; inset: 0;
    width: 100%; height: 100%;
    object-fit: cover;
}

.after-image { clip-path: inset(0 0 0 50%); }

.compare-slider {
    position: absolute; inset: 0;
    width: 100%; opacity: 0;
    cursor: ew-resize;
}

.compare-line {
    position: absolute;
    top: 0; bottom: 0; left: 50%;
    width: 2px;
    background: var(--text-accent);
    pointer-events: none;
}

.compare-label {
    position: absolute; top: 12px;
    padding: 6px 10px;
    background: rgba(0, 0, 0, 0.8);
    border: 1px solid var(--border-strong);
    font-size: var(--fs-tiny);
    font-weight: 700;
    letter-spacing: 2px;
    color: #d4af37;
    border-radius: var(--radius-sm);
}
.before-label { left: 12px; }
.after-label { right: 12px; }

/* =========================================================
   BOTTOM BAR
========================================================= */

.bottom-bar {
    position: absolute; left: 0; bottom: 0;
    width: 100%; height: 75px;
    border-top: 1px solid var(--border-accent);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 45px;
    z-index: 100;
    background: var(--bg-primary);
    transition:
        background 0.3s ease,
        border-color 0.3s ease,
        transform 0.35s ease,
        opacity 0.35s ease;
    will-change: transform, opacity;
}

.bottom-button {
    border: 0; background: none;
    color: var(--text-accent);
    cursor: pointer;
    font-size: var(--fs-tiny);
    font-weight: 600;
    letter-spacing: 2px;
    transition: 0.2s;
    text-decoration: none;
}

.bottom-button:hover { color: var(--text-primary); }

.help-text {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    font-size: var(--fs-micro);
    font-weight: 600;
    color: var(--text-dim);
    letter-spacing: 1.5px;
}

/* =========================================================
   HELP PANEL
========================================================= */

.help-panel {
    position: fixed; inset: 0;
    background: var(--bg-overlay);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 400;
    backdrop-filter: blur(8px);
}

.help-panel.active { display: flex; }

.help-box {
    width: 460px; max-width: 90vw;
    padding: 35px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
}

.help-box h2 {
    font-size: 22px;
    font-weight: 400;
    margin-bottom: 22px;
    color: var(--text-primary);
}

.shortcut {
    display: flex;
    justify-content: space-between;
    padding: 12px 0;
    border-bottom: 1px solid var(--border-subtle);
    font-size: var(--fs-small);
    color: var(--text-secondary);
}

.key {
    color: var(--bg-secondary);
    background: var(--text-accent);
    padding: 3px 9px;
    font-weight: 700;
    font-size: var(--fs-tiny);
    border-radius: var(--radius-sm);
}

/* =========================================================
   TOAST
========================================================= */

.toast {
    position: fixed; left: 50%; bottom: 95px;
    transform: translateX(-50%) translateY(20px);
    background: var(--bg-secondary);
    border: 1px solid var(--border-strong);
    padding: 10px 18px;
    font-size: var(--fs-tiny);
    font-weight: 700;
    letter-spacing: 2px;
    color: var(--text-accent);
    opacity: 0;
    pointer-events: none;
    transition: 0.3s;
    z-index: 300;
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md);
}

.toast.show {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
}


/* =========================================================
   END OF SHOWCASE SLIDE
========================================================= */

.end-screen {
    height: 100%;
    padding: 55px 7%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
}

.end-heading {
    font-size: clamp(48px, 8vw, 110px);
    font-weight: 300;
    letter-spacing: -4px;
    color: var(--text-primary);
    line-height: 1;
    margin-bottom: 18px;
}

.end-sub {
    color: var(--text-accent);
    font-size: var(--fs-small);
    letter-spacing: 3px;
    font-weight: 600;
    margin-bottom: 14px;
    text-transform: uppercase;
}

.end-note {
    color: var(--text-dim);
    font-size: var(--fs-tiny);
    letter-spacing: 1px;
    margin-bottom: 40px;
    max-width: 420px;
    line-height: 1.6;
}

.end-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    justify-content: center;
}

.end-btn {
    border: 1px solid var(--border-accent);
    color: var(--text-accent);
    padding: 12px 22px;
    font-size: var(--fs-tiny);
    font-weight: 600;
    letter-spacing: 2px;
    text-decoration: none;
    border-radius: var(--radius-sm);
    transition: 0.2s;
    background: var(--bg-card);
}

.end-btn:hover {
    border-color: var(--text-accent);
    color: var(--bg-secondary);
    background: var(--text-accent);
}

.end-btn-primary {
    border-color: var(--text-accent);
    background: rgba(212, 175, 55, 0.12);
}



/* =========================================================
   THANKS SCREEN
========================================================= */

.thanks-screen {
    height: 100%;
    padding: 40px 6% 50px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    overflow-y: auto;
}

.thanks-heading {
    font-size: clamp(42px, 7vw, 96px);
    font-weight: 300;
    letter-spacing: -3px;
    color: var(--text-primary);
    line-height: 1;
    margin-bottom: 14px;
}

.thanks-sub {
    color: var(--text-accent);
    font-size: var(--fs-small);
    letter-spacing: 3px;
    font-weight: 600;
    margin-bottom: 12px;
    text-transform: uppercase;
}

.thanks-note {
    color: var(--text-dim);
    font-size: var(--fs-tiny);
    letter-spacing: 1px;
    margin-bottom: 28px;
    max-width: 520px;
    line-height: 1.6;
}

.thanks-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
    max-width: 900px;
    width: 100%;
    margin-bottom: 32px;
    text-align: left;
}

.thanks-card {
    padding: 18px 20px;
    border: 1px solid var(--border-subtle);
    background: var(--bg-card);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-sm);
}

.thanks-dept {
    font-size: var(--fs-tiny);
    font-weight: 700;
    letter-spacing: 2px;
    color: var(--text-accent);
    margin-bottom: 10px;
}

.thanks-dept-text {
    font-size: var(--fs-small);
    color: var(--text-secondary);
    line-height: 1.55;
}

.thanks-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    justify-content: center;
}

@media (max-width: 700px) {
    .thanks-grid { grid-template-columns: 1fr; }
}

/* =========================================================
   GALLERY CAPTIONS + LIGHTBOX NAV
========================================================= */

.gallery-item {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 0;
}

.gallery-item img {
    width: 100%;
    aspect-ratio: 16 / 9;
    object-fit: cover;
    border: 1px solid var(--border-accent);
    cursor: pointer;
    transition: 0.25s;
    border-radius: var(--radius-sm);
}

.gallery-item img:hover {
    opacity: 0.85;
    transform: scale(0.98);
    border-color: var(--text-accent);
}

.gallery-caption {
    margin-top: 6px;
    font-size: var(--fs-micro);
    color: var(--text-muted);
    letter-spacing: 0.5px;
    line-height: 1.4;
    text-align: left;
}

.lightbox {
    flex-direction: column;
    gap: 12px;
}

.lightbox-nav {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    width: 44px;
    height: 44px;
    border: 1px solid var(--border-strong);
    background: rgba(0, 0, 0, 0.75);
    color: var(--text-accent);
    font-size: 22px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-sm);
    z-index: 2;
    transition: 0.2s;
}

.lightbox-nav:hover {
    background: var(--text-accent);
    color: #000;
}

.lightbox-prev { left: 18px; }
.lightbox-next { right: 18px; }

.lightbox-caption {
    max-width: 80vw;
    text-align: center;
    color: var(--text-secondary);
    font-size: var(--fs-small);
    letter-spacing: 1px;
    line-height: 1.5;
    padding: 0 20px;
}

.lightbox-counter {
    position: absolute;
    left: 50%;
    bottom: 22px;
    transform: translateX(-50%);
    font-size: var(--fs-tiny);
    letter-spacing: 2px;
    color: var(--text-accent);
    font-weight: 600;
}

/* =========================================================
   VIDEO SPEED + CLIP CONTROLS
========================================================= */

.video-extra-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    padding: 0 0 12px;
}

.video-extra-label {
    font-size: var(--fs-micro);
    letter-spacing: 2px;
    color: var(--text-dim);
    font-weight: 700;
    margin-right: 4px;
}

.control-btn.active {
    color: var(--bg-secondary);
    background: var(--text-accent);
    border-color: var(--text-accent);
}

.video-extra-sep {
    width: 1px;
    height: 18px;
    background: var(--border-subtle);
    margin: 0 4px;
}

/* =========================================================
   RESPONSIVE
========================================================= */

@media (max-width: 1100px) {
    .project-grid { grid-template-columns: 1fr; }
    .project-description { padding-right: 0; }
    .breakdown-grid { grid-template-columns: 1fr 1fr; }
}

@media (max-width: 900px) {
    :root { --sidebar-width: 240px; }
    .help-text { display: none; }
}

@media (max-width: 650px) {
    .topbar, .bottom-bar { padding: 0 20px; }
    .landing-screen { padding: 35px 20px; }
    .project-grid { padding-left: 20px; padding-right: 20px; }
    .project-title-row { padding-left: 20px; padding-right: 20px; }
    .sidebar {
        position: absolute;
        z-index: 200;
        top: 0; left: 0;
        height: 100%;
        box-shadow: 4px 0 20px rgba(0, 0, 0, 0.15);
    }
    .brand { letter-spacing: 3px; }
}

/* =========================================================
   VIDEO SOURCE SWITCHER (multi-video)
========================================================= */

.video-source-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 10px;
    align-items: center;
}

.video-source-btn {
    background: var(--bg-card);
    border: 1px solid var(--border-accent);
    color: var(--text-muted);
    padding: 7px 12px;
    cursor: pointer;
    font-size: var(--fs-tiny);
    font-weight: 600;
    letter-spacing: 1px;
    border-radius: var(--radius-sm);
    transition: 0.2s;
}

.video-source-btn:hover {
    color: var(--text-primary);
    border-color: var(--border-strong);
}

.video-source-btn.active {
    color: var(--bg-secondary);
    background: var(--text-accent);
    border-color: var(--text-accent);
}

/* =========================================================
   MEDIA TABS (Before/After | Passes carousel)
========================================================= */

.media-tabs {
    display: flex;
    gap: 6px;
    margin-top: 28px;
    margin-bottom: 12px;
    flex-wrap: wrap;
}

.media-tab-btn {
    background: transparent;
    border: 1px solid var(--border-accent);
    color: var(--text-muted);
    padding: 8px 14px;
    cursor: pointer;
    font-size: var(--fs-tiny);
    font-weight: 700;
    letter-spacing: 2px;
    border-radius: var(--radius-sm);
    transition: 0.2s;
}

.media-tab-btn:hover {
    color: var(--text-primary);
    border-color: var(--border-strong);
}

.media-tab-btn.active {
    color: var(--bg-secondary);
    background: var(--text-accent);
    border-color: var(--text-accent);
}

.media-tab-panel { display: none; }
.media-tab-panel.active { display: block; }

/* =========================================================
   PASSES CAROUSEL (looping slider, pause on hover)
========================================================= */

.passes-carousel {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    background: #0a0a0a;
    border: 1px solid var(--border-accent);
    border-radius: var(--radius-md);
    overflow: hidden;
    box-shadow: var(--shadow-md);
}

.passes-carousel-track {
    display: flex;
    height: calc(100% - 42px);
    transition: transform 0.45s ease;
}

.passes-carousel-slide {
    min-width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #000;
}

.passes-carousel-slide img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    display: block;
}

.passes-carousel-bar {
    position: absolute;
    left: 0; right: 0; bottom: 0;
    height: 42px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 0 12px;
    background: rgba(0, 0, 0, 0.82);
    border-top: 1px solid var(--border-subtle);
}

.passes-carousel-name {
    font-size: var(--fs-micro);
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #fff;
    text-align: center;
}

.passes-carousel-nav {
    display: flex;
    align-items: center;
    gap: 6px;
}

.passes-carousel-btn {
    background: transparent;
    border: 1px solid var(--border-accent);
    color: var(--text-accent);
    width: 28px;
    height: 28px;
    cursor: pointer;
    border-radius: var(--radius-sm);
    font-size: 14px;
    line-height: 1;
    transition: 0.2s;
}

.passes-carousel-btn:hover {
    background: var(--text-accent);
    color: #000;
}

.passes-carousel-dots {
    display: flex;
    gap: 5px;
    align-items: center;
}

.passes-carousel-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--border-strong);
    opacity: 0.5;
    cursor: pointer;
    transition: 0.2s;
}

.passes-carousel-dot.active {
    opacity: 1;
    background: var(--text-accent);
    transform: scale(1.25);
}

.passes-carousel.empty {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-dim);
    font-size: var(--fs-tiny);
    letter-spacing: 2px;
}

/* =========================================================
   PASSES GRID (full page section — image 2 style)
========================================================= */

.passes-section {
    margin-top: 40px;
    padding: 0 6% 70px;
}

.passes-section .section-label {
    margin-bottom: 18px;
}

.passes-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
}

.pass-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    overflow: hidden;
    transition: 0.2s;
    cursor: pointer;
}

.pass-card:hover {
    border-color: var(--border-strong);
    box-shadow: var(--shadow-sm);
}

.pass-card img {
    display: block;
    width: 100%;
    aspect-ratio: 16 / 10;
    object-fit: cover;
    background: #000;
}

.pass-card-name {
    padding: 8px 10px;
    font-size: var(--fs-micro);
    font-weight: 600;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    line-height: 1.35;
    word-break: break-word;
    text-align: center;
    border-top: 1px solid var(--border-subtle);
    background: var(--bg-secondary);
}

@media (max-width: 1100px) {
    .passes-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 650px) {
    .passes-grid { grid-template-columns: repeat(2, 1fr); }
    .passes-section { padding-left: 20px; padding-right: 20px; }
}


/* Passes scrub (manual, like before/after control) */
.passes-scrub-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
    flex: 1;
    min-width: 0;
    margin-right: 8px;
}
.passes-scrub-label {
    font-size: var(--fs-micro);
    font-weight: 700;
    letter-spacing: 1px;
    color: var(--text-muted);
    white-space: nowrap;
}
.passes-scrub {
    flex: 1;
    min-width: 60px;
    height: 4px;
    accent-color: var(--text-accent);
    cursor: ew-resize;
}
.passes-carousel-track {
    transition: transform 0.35s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.passes-carousel-slide img {
    cursor: zoom-in;
}


/* =========================================================
   HOME / END optional right media
========================================================= */

/* With media — reference layout: large title left, framed still right */
.landing-screen.has-media {
    display: grid;
    grid-template-columns: minmax(280px, 1fr) minmax(320px, 1.15fr);
    align-items: center;
    justify-content: center;
    column-gap: 48px;
    row-gap: 28px;
    padding: 6vh max(4%, calc((100% - 1180px) / 2));
    text-align: left;
    max-width: 100%;
}

.landing-screen.has-media .landing-main {
    max-width: none;
    width: 100%;
    text-align: left;
    align-items: flex-start;
    justify-content: center;
}

.landing-screen.has-media .eyebrow {
    margin-bottom: 16px;
}

.landing-screen.has-media .main-heading {
    font-size: clamp(40px, 5.8vw, 88px);
    line-height: 0.94;
    letter-spacing: -1.5px;
    margin-bottom: 36px;
    max-width: 11ch;
}

.landing-screen.has-media .artist-grid {
    justify-items: start;
    max-width: 340px;
    width: 100%;
}

.landing-screen.has-media .artist-card {
    max-width: 340px;
    min-height: 140px;
    padding: 24px 28px;
}

.landing-media {
    width: 100%;
    max-width: 640px;
    justify-self: end;
    aspect-ratio: 16 / 10;
    border: 1px solid rgba(201, 169, 98, 0.55);
    border-radius: 2px;
    overflow: hidden;
    background: #0a0a0a;
    box-shadow:
        0 24px 60px rgba(0, 0, 0, 0.55),
        0 0 0 1px rgba(0, 0, 0, 0.4);
}

/* End screen with media — same balanced pair */
.end-screen.has-media {
    display: grid;
    grid-template-columns: minmax(280px, 1fr) minmax(260px, 0.9fr);
    align-items: center;
    column-gap: 48px;
    row-gap: 28px;
    padding: 6vh max(4%, calc((100% - 1100px) / 2));
    text-align: left;
}

.end-screen.has-media .end-main {
    max-width: none;
    text-align: left;
    align-items: flex-start;
}

.end-media {
    width: 100%;
    max-width: 600px;
    justify-self: end;
    aspect-ratio: 16 / 10;
    border: 1px solid rgba(201, 169, 98, 0.55);
    border-radius: 2px;
    overflow: hidden;
    background: #0a0a0a;
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.55);
}

.hero-media-el {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}

@media (max-width: 960px) {
    .landing-screen.has-media,
    .end-screen.has-media {
        grid-template-columns: 1fr;
        text-align: center;
        padding: 40px 6%;
        row-gap: 28px;
    }
    .landing-screen.has-media .landing-main,
    .end-screen.has-media .end-main {
        align-items: center;
        text-align: center;
    }
    .landing-screen.has-media .main-heading {
        max-width: none;
    }
    .landing-screen.has-media .artist-grid {
        justify-items: center;
        max-width: 100%;
    }
    .landing-media,
    .end-media {
        justify-self: center;
        max-width: 640px;
    }
}

/* =========================================================
   RENDER PASSES — diagonal split wipe (no auto-loop)
========================================================= */

.passes-split {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    background: #000;
    border: 1px solid var(--border-accent);
    border-radius: var(--radius-md);
    overflow: hidden;
    box-shadow: var(--shadow-md);
}

.passes-split-layer {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
}

.passes-split-layer img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
    background: #000;
    cursor: zoom-in;
}

.passes-split-layer.is-base {
    z-index: 1;
}

.passes-split-layer.is-reveal {
    z-index: 2;
    /* diagonal wipe via clip-path */
    clip-path: polygon(0 0, var(--wipe, 100%) 0, var(--wipe, 100%) 100%, 0 100%);
    transition: clip-path 0.55s cubic-bezier(0.4, 0, 0.2, 1);
}

.passes-split-layer.is-reveal.wipe-from-left {
    clip-path: polygon(0 0, 0 0, 0 100%, 0 100%);
}

.passes-split.animating .passes-split-layer.is-reveal {
    clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%);
}

/* Prefer diagonal split like showreel wipe */
.passes-split-layer.is-reveal.diag {
    clip-path: polygon(0 0, 0 0, 0 100%);
    transition: clip-path 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}
.passes-split.animating .passes-split-layer.is-reveal.diag {
    clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%);
}

.passes-split-bar {
    position: absolute;
    left: 0; right: 0; bottom: 0;
    z-index: 5;
    height: 48px;
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 10px;
    padding: 0 12px;
    background: rgba(0, 0, 0, 0.82);
    border-top: 1px solid var(--border-subtle);
}
.passes-split-bar .passes-carousel-name {
    grid-column: 1 / -1;
    grid-row: 1;
    justify-self: center;
    text-align: center;
    pointer-events: none;
    z-index: 1;
    max-width: 55%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.passes-split-bar .passes-carousel-nav {
    grid-column: 3;
    grid-row: 1;
    justify-self: end;
    z-index: 2;
}


.project-artist {
    margin-top: 8px;
    font-size: var(--fs-small);
    letter-spacing: 2px;
    font-weight: 600;
    color: var(--text-accent);
    text-transform: uppercase;
}
.project-artist.is-override::before {
    content: "ARTIST · ";
    opacity: 0.7;
    letter-spacing: 1px;
}
"""

TEMPLATE_MAIN_JS = """/* =========================================================
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
        head.innerHTML = String(HOME.heading).replace(/\\n/g, '<br>');
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
"""

TEMPLATE_PROJECT_JS = """/* =========================================================
   PROJECT PAGE LOGIC
========================================================= */

(function () {

    const bodyProject = document.body.getAttribute('data-project');
    if (bodyProject === null) return;

    if (typeof PROJECTS === 'undefined' || typeof PATHS === 'undefined') {
        console.error('data.js not loaded');
        if (typeof showToast === 'function') showToast('DATA.JS MISSING');
        return;
    }

    const id = parseInt(bodyProject, 10);
    if (isNaN(id) || id < 0 || id >= PROJECTS.length) {
        console.error('Invalid project index:', bodyProject);
        return;
    }

    const project = PROJECTS[id];
    if (!project) return;

    const asset = (path) => {
        if (!path) return '';
        return (PATHS.assetBase || '') + path;
    };

    function basenameFromPath(path) {
        if (!path) return '';
        const s = String(path).replace(/\\\\/g, '/');
        const base = s.split('/').pop() || s;
        return base.replace(/\\.[^.]+$/, '');
    }

    function normalizePassItem(item) {
        if (!item) return null;
        if (typeof item === 'string') {
            return { src: item, name: basenameFromPath(item) };
        }
        if (typeof item === 'object') {
            const src = item.src || item.path || item.image || '';
            if (!src) return null;
            const name = item.name || item.label || item.title || basenameFromPath(src);
            return { src, name: String(name) };
        }
        return null;
    }

    function getProjectVideos(project) {
        const list = [];
        if (Array.isArray(project.videos) && project.videos.length) {
            project.videos.forEach((v, i) => {
                if (typeof v === 'string') {
                    list.push({ src: v, label: basenameFromPath(v) || ('Video ' + (i + 1)) });
                } else if (v && typeof v === 'object') {
                    const src = v.src || v.path || v.video || '';
                    if (!src) return;
                    list.push({
                        src,
                        label: v.label || v.name || basenameFromPath(src) || ('Video ' + (i + 1)),
                        poster: v.poster || ''
                    });
                }
            });
        }
        if (!list.length && project.video) {
            list.push({ src: project.video, label: 'Main', poster: project.poster || '' });
        }
        return list;
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    const setText = (elId, text) => {
        const el = document.getElementById(elId);
        if (el) el.textContent = text;
    };

    setText('projectNumber', `PROJECT ${String(id + 1).padStart(2, '0')}`);
    setText('projectTitle', project.title || '');
    const catEl = document.getElementById('projectCategory');
    if (catEl) {
        catEl.innerHTML = (project.category || '').replace(/ \\/ /g, '<br>');
    }
    // Optional per-project artist (falls back to global ARTIST.name when empty)
    const artistEl = document.getElementById('projectArtist');
    if (artistEl) {
        const local = (project.artistName || project.artist || '').trim();
        const globalName = (typeof ARTIST !== 'undefined' && ARTIST && ARTIST.name) ? ARTIST.name : '';
        const name = local || globalName;
        if (name) {
            artistEl.textContent = name;
            artistEl.style.display = '';
            artistEl.classList.toggle('is-override', !!local);
        } else {
            artistEl.textContent = '';
            artistEl.style.display = 'none';
        }
    }
    const descEl = document.getElementById('projectDescription');
    if (descEl) {
        descEl.innerHTML = (project.description || '').replace(/\\n/g, '<br>');
    }
    setText('pageCurrent', String(id + 1).padStart(2, '0'));
    setText('pageTotal', String(PROJECTS.length).padStart(2, '0'));

    const detailsEl = document.getElementById('projectDetails');
    if (detailsEl) {
        detailsEl.innerHTML = '';
        const details = project.details || {};
        const preferred = ['ROLE', 'TASK', 'DURATION', 'OUTPUT'];
        const keys = [
            ...preferred.filter(k => Object.prototype.hasOwnProperty.call(details, k)),
            ...Object.keys(details).filter(k => !preferred.includes(k)),
        ];
        keys.forEach(k => {
            const v = details[k];
            if (v === undefined || v === null) return;
            const d = document.createElement('div');
            d.className = 'detail';
            d.innerHTML = `
                <div class="detail-label">${escapeHtml(k)}</div>
                <div class="detail-value">${escapeHtml(String(v))}</div>
            `;
            detailsEl.appendChild(d);
        });
    }

    const toolsEl = document.getElementById('projectTools');
    if (toolsEl) {
        toolsEl.innerHTML = '';
        (project.tools || []).forEach(t => {
            const s = document.createElement('span');
            s.className = 'tool';
            s.textContent = t;
            toolsEl.appendChild(s);
        });
    }

    const contribEl = document.getElementById('contributionGrid');
    if (contribEl) {
        contribEl.innerHTML = '';
        (project.contributions || []).forEach(pair => {
            const num = Array.isArray(pair) ? pair[0] : (pair.num || '');
            const name = Array.isArray(pair) ? pair[1] : (pair.name || '');
            const c = document.createElement('div');
            c.className = 'breakdown-card';
            c.innerHTML = `<span>${escapeHtml(String(num))}</span><strong>${escapeHtml(String(name))}</strong>`;
            contribEl.appendChild(c);
        });
    }

    const video = document.getElementById('projectVideo');
    const progressBar = document.getElementById('progressBar');
    const progress = document.getElementById('progress');

    /* Poster: explicit field → after image → first gallery still */
    const posterPath = (
        project.poster ||
        project.after ||
        (project.gallery && project.gallery[0]) ||
        ''
    );

    const projectVideos = getProjectVideos(project);
    let currentVideoIndex = 0;

    function loadVideoAt(index, autoplay) {
        if (!video || !projectVideos.length) return;
        currentVideoIndex = Math.max(0, Math.min(index, projectVideos.length - 1));
        const entry = projectVideos[currentVideoIndex];
        const wasPaused = video.paused;
        const t = video.currentTime || 0;
        video.src = asset(entry.src);
        const p = entry.poster || posterPath || '';
        if (p) {
            video.setAttribute('poster', asset(p));
            video.poster = asset(p);
            const posterEl = document.getElementById('videoPosterOverlay');
            if (posterEl) posterEl.src = asset(p);
        }
        document.querySelectorAll('#videoSourceBar .video-source-btn').forEach((btn, i) => {
            btn.classList.toggle('active', i === currentVideoIndex);
        });
        video.load();
        if (autoplay || !wasPaused) {
            video.play().catch(() => {});
        }
        if (typeof showToast === 'function' && projectVideos.length > 1) {
            showToast(entry.label || ('VIDEO ' + (currentVideoIndex + 1)));
        }
    }

    // Video source switcher
    const sourceBar = document.getElementById('videoSourceBar');
    if (sourceBar) {
        sourceBar.innerHTML = '';
        if (projectVideos.length > 1) {
            projectVideos.forEach((entry, i) => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'video-source-btn' + (i === 0 ? ' active' : '');
                btn.textContent = entry.label || ('Video ' + (i + 1));
                btn.addEventListener('click', () => loadVideoAt(i, true));
                sourceBar.appendChild(btn);
            });
        }
    }

    if (video) {
        if (projectVideos.length) {
            video.src = asset(projectVideos[0].src);
            const p0 = projectVideos[0].poster || posterPath || '';
            if (p0) {
                video.setAttribute('poster', asset(p0));
                video.poster = asset(p0);
            }
        } else if (project.video) {
            video.src = asset(project.video);
            if (posterPath) {
                video.setAttribute('poster', asset(posterPath));
                video.poster = asset(posterPath);
            }
        }
        if (posterPath || (projectVideos[0] && projectVideos[0].poster)) {
            // poster handled above
        }

        // Overlay thumbnail (more reliable than native poster alone)
        let posterEl = document.getElementById('videoPosterOverlay');
        const wrapper = video.closest('.video-wrapper');
        if (wrapper && posterPath) {
            if (!posterEl) {
                posterEl = document.createElement('img');
                posterEl.id = 'videoPosterOverlay';
                posterEl.className = 'video-poster-overlay';
                posterEl.alt = 'Video thumbnail';
                wrapper.insertBefore(posterEl, video);
            }
            posterEl.src = asset(posterPath);
            posterEl.style.display = 'block';
            posterEl.onclick = () => {
                if (typeof window.togglePlay === 'function') window.togglePlay();
            };
        }

        const hidePoster = () => {
            if (posterEl) posterEl.classList.add('is-hidden');
        };
        const showPoster = () => {
            if (posterEl) posterEl.classList.remove('is-hidden');
        };

        video.addEventListener('play', hidePoster);
        video.addEventListener('playing', hidePoster);
        video.addEventListener('pause', () => {
            // Show thumbnail again only near the start
            if (video.currentTime < 0.25) showPoster();
        });
        video.addEventListener('ended', () => {
            video.currentTime = 0;
            showPoster();
        });

        video.load();

        video.addEventListener('timeupdate', () => {
            if (!video.duration || !progressBar) return;
            progressBar.style.width = (video.currentTime / video.duration * 100) + '%';
        });

        video.addEventListener('error', () => {
            if (typeof showToast === 'function') {
                showToast('VIDEO NOT FOUND OR FORMAT NOT SUPPORTED');
            }
            // Keep poster visible if video fails
            showPoster();
        });

        if (progress) {
            progress.addEventListener('click', (e) => {
                if (!video.duration) return;
                const rect = progress.getBoundingClientRect();
                video.currentTime = ((e.clientX - rect.left) / rect.width) * video.duration;
                hidePoster();
            });
        }
    }

    const chaptersEl = document.getElementById('chapters');
    if (chaptersEl) {
        chaptersEl.innerHTML = '';
        (project.chapters || []).forEach(ch => {
            const b = document.createElement('button');
            b.className = 'chapter';
            b.textContent = ch.name || '';
            b.onclick = () => {
                if (!video) return;
                video.currentTime = Number(ch.time) || 0;
                video.play().catch(() => {});
            };
            chaptersEl.appendChild(b);
        });
    }

    /* Gallery items: string path OR { src, caption } */
    function normalizeGalleryItem(item) {
        if (!item) return null;
        if (typeof item === 'string') return { src: item, caption: '' };
        if (typeof item === 'object') {
            const src = item.src || item.path || item.image || '';
            if (!src) return null;
            return { src, caption: item.caption || item.description || item.desc || '' };
        }
        return null;
    }

    const galleryItems = (project.gallery || []).map(normalizeGalleryItem).filter(Boolean);
    const passItemsEarly = (project.passes || []).map(normalizePassItem).filter(Boolean);

    // Unified full-view list (gallery stills OR render passes)
    let lightboxItems = [];
    let lightboxIndex = 0;
    let lightboxMode = 'gallery'; // 'gallery' | 'passes'

    const galleryEl = document.getElementById('gallery');
    if (galleryEl) {
        galleryEl.innerHTML = '';
        galleryItems.forEach((item, idx) => {
            const wrap = document.createElement('div');
            wrap.className = 'gallery-item';
            const el = document.createElement('img');
            el.src = asset(item.src);
            el.alt = item.caption || '';
            el.onerror = function () { wrap.style.display = 'none'; };
            el.onclick = () => openLightboxGallery(idx);
            wrap.appendChild(el);
            if (item.caption) {
                const cap = document.createElement('div');
                cap.className = 'gallery-caption';
                cap.textContent = item.caption;
                wrap.appendChild(cap);
            }
            galleryEl.appendChild(wrap);
        });
    }

    function updateLightbox() {
        const lb = document.getElementById('lightbox');
        const img = document.getElementById('lightboxImage');
        const cap = document.getElementById('lightboxCaption');
        const counter = document.getElementById('lightboxCounter');
        if (!lightboxItems.length) return;
        const item = lightboxItems[lightboxIndex];
        if (img) img.src = asset(item.src);
        const label = item.caption || item.name || '';
        if (cap) {
            cap.textContent = label;
            cap.style.display = label ? 'block' : 'none';
        }
        if (counter) counter.textContent = (lightboxIndex + 1) + ' / ' + lightboxItems.length;
        if (lb) lb.classList.add('active');
    }

    function openLightboxList(items, idx, mode) {
        lightboxItems = items || [];
        if (!lightboxItems.length) return;
        lightboxMode = mode || 'gallery';
        lightboxIndex = Math.max(0, Math.min(idx || 0, lightboxItems.length - 1));
        updateLightbox();
    }

    window.openLightboxGallery = (idx) => openLightboxList(galleryItems, idx, 'gallery');
    window.openLightboxPasses = (idx) => openLightboxList(passItemsEarly, idx, 'passes');

    window.openLightboxAt = (idx) => openLightboxGallery(idx);
    window.openLightbox = (src) => {
        // Prefer current mode list, then gallery, then passes
        const lists = [
            lightboxItems,
            galleryItems,
            passItemsEarly,
        ];
        for (const list of lists) {
            if (!list || !list.length) continue;
            const i = list.findIndex(g => asset(g.src) === src || g.src === src);
            if (i >= 0) {
                const mode = (list === passItemsEarly) ? 'passes' : 'gallery';
                openLightboxList(list, i, mode);
                return;
            }
        }
        // Fallback: single image
        openLightboxList([{ src: src.replace(/^\\.\\.\\//, '').replace(PATHS.assetBase || '', ''), caption: '' }], 0, 'gallery');
    };
    window.closeLightbox = () => {
        document.getElementById('lightbox')?.classList.remove('active');
    };
    window.lightboxPrev = (e) => {
        if (e) { e.preventDefault(); e.stopPropagation(); }
        if (!lightboxItems.length) return;
        lightboxIndex = (lightboxIndex - 1 + lightboxItems.length) % lightboxItems.length;
        updateLightbox();
    };
    window.lightboxNext = (e) => {
        if (e) { e.preventDefault(); e.stopPropagation(); }
        if (!lightboxItems.length) return;
        lightboxIndex = (lightboxIndex + 1) % lightboxItems.length;
        updateLightbox();
    };

    const beforeImage = document.getElementById('beforeImage');
    const afterImage = document.getElementById('afterImage');
    const compareSlider = document.getElementById('compareSlider');
    const compareLine = document.getElementById('compareLine');

    if (beforeImage) beforeImage.src = asset(project.before);
    if (afterImage) afterImage.src = asset(project.after);

    if (compareSlider && afterImage && compareLine) {
        const applyCompare = () => {
            const v = compareSlider.value;
            afterImage.style.clipPath = `inset(0 0 0 ${v}%)`;
            compareLine.style.left = v + '%';
        };
        compareSlider.addEventListener('input', applyCompare);
        applyCompare();
    }




    /* ---------- Render passes: diagonal split wipe + grid ---------- */
    const passItems = passItemsEarly;

    document.querySelectorAll('[data-media-tab]').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.getAttribute('data-media-tab');
            document.querySelectorAll('[data-media-tab]').forEach(b => b.classList.toggle('active', b === btn));
            document.querySelectorAll('.media-tab-panel').forEach(p => p.classList.remove('active'));
            if (tab === 'compare') {
                document.getElementById('mediaPanelCompare')?.classList.add('active');
            } else {
                document.getElementById('mediaPanelPasses')?.classList.add('active');
            }
        });
    });
    if (!passItems.length) {
        const passTab = document.querySelector('[data-media-tab="passes"]');
        if (passTab) passTab.style.display = 'none';
    }

    const splitRoot = document.getElementById('passesCarousel');
    const baseImg = document.getElementById('passesBaseImg');
    const revealImg = document.getElementById('passesRevealImg');
    const revealLayer = document.getElementById('passesReveal');
    const nameEl = document.getElementById('passesCarouselName');
    const dotsEl = document.getElementById('passesCarouselDots');
    let passIndex = 0;
    let animating = false;

    function setPassImages(fromIdx, toIdx) {
        if (!passItems.length) return;
        const from = passItems[fromIdx] || passItems[toIdx];
        const to = passItems[toIdx];
        if (baseImg) {
            baseImg.src = asset(from.src);
            baseImg.alt = from.name || '';
            baseImg.onclick = () => openLightboxPasses(fromIdx);
        }
        if (revealImg) {
            revealImg.src = asset(to.src);
            revealImg.alt = to.name || '';
            revealImg.onclick = () => openLightboxPasses(toIdx);
        }
    }

    function showPass(i, animate) {
        if (!passItems.length) return;
        const next = ((i % passItems.length) + passItems.length) % passItems.length;
        if (next === passIndex && !animate) {
            // initial paint
            setPassImages(next, next);
            if (revealLayer) {
                revealLayer.style.transition = 'none';
                revealLayer.classList.remove('diag');
                // full reveal of current
                revealLayer.style.clipPath = 'polygon(0 0, 100% 0, 100% 100%, 0 100%)';
            }
            if (nameEl) nameEl.textContent = passItems[next].name || '';
            if (dotsEl) {
                dotsEl.querySelectorAll('.passes-carousel-dot').forEach((d, di) => {
                    d.classList.toggle('active', di === next);
                });
            }
            passIndex = next;
            return;
        }
        if (animating) return;
        const prev = passIndex;
        passIndex = next;
        if (nameEl) nameEl.textContent = passItems[passIndex].name || '';
        if (dotsEl) {
            dotsEl.querySelectorAll('.passes-carousel-dot').forEach((d, di) => {
                d.classList.toggle('active', di === passIndex);
            });
        }
        if (!animate || !revealLayer || !baseImg || !revealImg) {
            setPassImages(passIndex, passIndex);
            if (revealLayer) {
                revealLayer.style.transition = 'none';
                revealLayer.style.clipPath = 'polygon(0 0, 100% 0, 100% 100%, 0 100%)';
            }
            return;
        }
        // Diagonal split wipe: base = previous, reveal = next
        animating = true;
        baseImg.src = asset(passItems[prev].src);
        baseImg.alt = passItems[prev].name || '';
        revealImg.src = asset(passItems[passIndex].src);
        revealImg.alt = passItems[passIndex].name || '';
        revealImg.onclick = () => openLightboxPasses(passIndex);
        baseImg.onclick = () => openLightboxPasses(prev);

        revealLayer.style.transition = 'none';
        revealLayer.classList.add('diag');
        // start collapsed on diagonal
        revealLayer.style.clipPath = 'polygon(0 0, 0 0, 0 100%)';
        // force reflow
        void revealLayer.offsetWidth;
        revealLayer.style.transition = 'clip-path 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
        requestAnimationFrame(() => {
            revealLayer.style.clipPath = 'polygon(0 0, 100% 0, 100% 100%, 0 100%)';
        });
        const done = () => {
            animating = false;
            // settle: both show current
            if (baseImg) {
                baseImg.src = asset(passItems[passIndex].src);
                baseImg.alt = passItems[passIndex].name || '';
                baseImg.onclick = () => openLightboxPasses(passIndex);
            }
            revealLayer.removeEventListener('transitionend', done);
        };
        revealLayer.addEventListener('transitionend', done);
        setTimeout(done, 700);
    }

    if (passItems.length && (baseImg || revealImg)) {
        if (dotsEl) {
            dotsEl.innerHTML = '';
            passItems.forEach((_, i) => {
                const d = document.createElement('span');
                d.className = 'passes-carousel-dot' + (i === 0 ? ' active' : '');
                d.title = passItems[i].name || '';
                d.addEventListener('click', () => showPass(i, true));
                dotsEl.appendChild(d);
            });
        }
        document.getElementById('passesPrev')?.addEventListener('click', () => showPass(passIndex - 1, true));
        document.getElementById('passesNext')?.addEventListener('click', () => showPass(passIndex + 1, true));
        showPass(0, false);
    } else if (splitRoot) {
        splitRoot.classList.add('empty');
        if (nameEl) nameEl.textContent = 'NO PASSES';
    }

    // Full grid below content
    const passesSection = document.getElementById('passesSection');
    const passesGrid = document.getElementById('passesGrid');
    if (passesSection && passesGrid && passItems.length) {
        passesSection.style.display = '';
        passesGrid.innerHTML = '';
        passItems.forEach((item, idx) => {
            const card = document.createElement('div');
            card.className = 'pass-card';
            const img = document.createElement('img');
            img.src = asset(item.src);
            img.alt = item.name || '';
            img.loading = 'lazy';
            img.onerror = function () { card.style.opacity = '0.4'; };
            const label = document.createElement('div');
            label.className = 'pass-card-name';
            label.textContent = item.name || '';
            card.appendChild(img);
            card.appendChild(label);
            card.addEventListener('click', () => openLightboxPasses(idx));
            passesGrid.appendChild(card);
        });
    }


    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');

    if (prevBtn) {
        if (id > 0) prevBtn.href = PROJECTS[id - 1].file;
        else prevBtn.href = '../index.html';
    }

    if (nextBtn) {
        if (id < PROJECTS.length - 1) {
            nextBtn.href = PROJECTS[id + 1].file;
        } else {
            // Always go to fixed end slide (not part of PROJECTS list)
            nextBtn.href = 'end.html';
        }
    }

    /* Playback speed + clip limit */
    let playRate = 1;
    let clipLimitSec = 0;
    let clipStart = 0;

    function applyPlayRate(announce) {
        if (!video) return;
        video.playbackRate = playRate;
        document.querySelectorAll('[data-rate]').forEach(btn => {
            btn.classList.toggle('active', parseFloat(btn.getAttribute('data-rate')) === playRate);
        });
        if (announce && typeof showToast === 'function') showToast(playRate + '× SPEED');
    }

    function applyClipLimit(announce) {
        document.querySelectorAll('[data-clip]').forEach(btn => {
            const v = btn.getAttribute('data-clip');
            const match = (clipLimitSec === 0 && v === 'full') || (String(clipLimitSec) === v);
            btn.classList.toggle('active', match);
        });
        if (announce && typeof showToast === 'function') {
            showToast(clipLimitSec === 0 ? 'FULL VIDEO' : ('CLIP ' + clipLimitSec + 's'));
        }
    }

    window.setPlayRate = (rate) => {
        playRate = Number(rate) || 1;
        applyPlayRate(true);
    };
    window.setClipLimit = (sec) => {
        if (sec === 'full' || sec === 0 || sec === '0') clipLimitSec = 0;
        else clipLimitSec = Number(sec) || 0;
        if (video) clipStart = video.currentTime || 0;
        applyClipLimit(true);
    };

    if (video) {
        video.addEventListener('timeupdate', () => {
            // After the selected clip length, continue the rest of the video at 1×
            if (clipLimitSec > 0 && video.currentTime >= clipStart + clipLimitSec) {
                clipLimitSec = 0;
                playRate = 1;
                video.playbackRate = 1;
                applyPlayRate(false);
                applyClipLimit(false); // highlight FULL again
                if (typeof showToast === 'function') showToast('CLIP DONE · 1× CONTINUE');
            }
        });
    }

    document.querySelectorAll('[data-rate]').forEach(btn => {
        btn.addEventListener('click', () => window.setPlayRate(btn.getAttribute('data-rate')));
    });
    document.querySelectorAll('[data-clip]').forEach(btn => {
        btn.addEventListener('click', () => window.setClipLimit(btn.getAttribute('data-clip')));
    });
    applyPlayRate(false);
    applyClipLimit(false);

    window.togglePlay = () => {
        if (!video) return;
        if (video.paused) {
            clipStart = video.currentTime || 0;
            video.playbackRate = playRate;
            video.play().catch(() => {});
        } else {
            video.pause();
        }
    };
    window.restartVideo = () => {
        if (!video) return;
        video.currentTime = 0;
        video.play().catch(() => {});
    };
    window.toggleMute = () => {
        if (!video) return;
        video.muted = !video.muted;
        if (typeof showToast === 'function') {
            showToast(video.muted ? 'MUTED' : 'AUDIO ON');
        }
    };
    window.fullscreenVideo = () => {
        if (!video) return;
        if (video.requestFullscreen) video.requestFullscreen();
        else if (video.webkitRequestFullscreen) video.webkitRequestFullscreen();
    };

    document.addEventListener('keydown', (e) => {
        const tag = (e.target && e.target.tagName) || '';
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
        if (document.getElementById('helpPanel')?.classList.contains('active')) return;

        const lbOpen = document.getElementById('lightbox')?.classList.contains('active');
        if (lbOpen) {
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                e.stopPropagation();
                window.lightboxPrev(e);
                return;
            }
            if (e.key === 'ArrowRight') {
                e.preventDefault();
                e.stopPropagation();
                window.lightboxNext(e);
                return;
            }
            if (e.key === 'Escape') {
                e.preventDefault();
                e.stopPropagation();
                window.closeLightbox();
                return;
            }
            return;
        }

        if (e.code === 'Space') {
            e.preventDefault();
            window.togglePlay();
        } else if (e.key === 'r' || e.key === 'R') {
            window.restartVideo();
        } else if (e.key === 'm' || e.key === 'M') {
            window.toggleMute();
        } else if (e.key === 'f' || e.key === 'F') {
            window.fullscreenVideo();
        }
    });

    if (video) {
        video.addEventListener('dblclick', window.fullscreenVideo);
    }

})();
"""

STARTER_ARTIST = {'name': 'ARTIST NAME', 'role': 'LIGHTING · SHADING · COMPOSITING'}

STARTER_HOME = {'eyebrow': 'COMPANY CREATIVE SHOWCASE', 'heading': 'SHADING DEPARTMENT\nSHOWCASE', 'mediaType': '', 'media': ''}

STARTER_END = {'eyebrow': 'PRESENTATION COMPLETE', 'heading': 'THANK YOU', 'note': '', 'mediaType': '', 'media': ''}

STARTER_FONT = {'family': 'Segoe UI, Arial, Helvetica, sans-serif', 'url': ''}

STARTER_HEADER = {'brand': 'ARTIST SHOWCASE · 2026'}

STARTER_THANKS = {'enabled': True, 'eyebrow': 'WITH GRATITUDE', 'heading': 'THANK YOU', 'sub': 'TO EVERY DEPARTMENT THAT MADE THIS POSSIBLE', 'note': '', 'departments': [{'name': 'MODELLING', 'text': ''}, {'name': 'TEXTURING', 'text': ''}, {'name': 'RIGGING', 'text': ''}, {'name': 'ANIMATION', 'text': ''}]}

STARTER_PROJECT = {'id': 0, 'file': 'project-01.html', 'title': 'NEW PROJECT', 'category': 'CATEGORY / SUB', 'description': '', 'video': '', 'poster': '', 'details': {}, 'tools': [], 'contributions': [], 'chapters': [], 'gallery': [], 'before': '', 'after': '', 'passes': [], 'videos': [], 'artistName': '', 'showArtist': True, 'status': '', 'tags': [], 'clientHidden': False}


def _write_text(path, content, force=False):
    """Write content if missing or force=True. Returns True if written."""
    if os.path.isfile(path) and not force:
        return False
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def project_dirs(base=None):
    """Return standard folder paths for a showcase root."""
    root = base or BASE_DIR
    return {
        "root": root,
        "js": os.path.join(root, "js"),
        "css": os.path.join(root, "css"),
        "projects": os.path.join(root, "projects"),
        "assets": os.path.join(root, "assets"),
        "assets_images": os.path.join(root, "assets", "images"),
        "assets_videos": os.path.join(root, "assets", "videos"),
    }


def _normalize_cache_buster(content):
    for old in (
        "20260924a", "20260924b", "20260924c", "20260924d",
        "20260924e", "20260924f", "20260924g", "20260924h",
        "20260924i", "20260924j",
    ):
        content = content.replace("?v=" + old, "?v=" + CACHE_BUSTER)
    return content


def _starter_data_js(with_sample=True):
    paths_block = (
        "/* =========================================================\n"
        "   PATHS — resolve asset URLs from any page location\n"
        "========================================================= */\n\n"
        "const PATHS = {\n"
        "    assetBase: window.location.pathname.includes('/projects/')\n"
        "        ? '../'\n"
        "        : ''\n"
        "};\n"
    )
    projects = [dict(STARTER_PROJECT)] if with_sample else []
    return (
        "/* =========================================================\n"
        "   ARTIST + PROJECT DATA\n"
        "   This file is JSON-compatible. Edited by Python app.\n"
        "========================================================= */\n\n"
        "const ARTIST = " + json.dumps(STARTER_ARTIST, indent=4) + ";\n\n"
        "const HOME = " + json.dumps(STARTER_HOME, indent=4) + ";\n\n"
        "const END = " + json.dumps(STARTER_END, indent=4) + ";\n\n"
        "const FONT = " + json.dumps(STARTER_FONT, indent=4) + ";\n\n"
        "const HEADER = " + json.dumps(STARTER_HEADER, indent=4) + ";\n\n"
        "const THANKS = " + json.dumps(STARTER_THANKS, indent=4) + ";\n\n"
        "const PROJECTS = " + json.dumps(projects, indent=4) + ";\n\n"
        + paths_block
    )


def scaffold_project(base=None, force=False, with_sample=True):
    """
    Create complete Artist Showcase folder structure and shell files.

    Layout:
      root/
        index.html, thanks.html, README.txt, editor.py (copy yourself)
        css/style.css
        js/data.js, main.js, project.js
        projects/end.html, project-01.html
        assets/images/, assets/videos/, assets/images/project-01/

    force=True overwrites HTML/CSS/JS shells (never overwrites existing data.js).
    Returns list of created/updated paths relative to root.
    """
    d = project_dirs(base)
    root = d["root"]
    created = []

    for key in ("js", "css", "projects", "assets_images", "assets_videos"):
        os.makedirs(d[key], exist_ok=True)

    shells = {
        os.path.join(root, "index.html"): TEMPLATE_INDEX_HTML,
        os.path.join(root, "thanks.html"): TEMPLATE_THANKS_HTML,
        os.path.join(d["projects"], "end.html"): TEMPLATE_END_HTML,
        os.path.join(d["css"], "style.css"): TEMPLATE_STYLE_CSS,
        os.path.join(d["js"], "main.js"): TEMPLATE_MAIN_JS,
        os.path.join(d["js"], "project.js"): TEMPLATE_PROJECT_JS,
    }
    for path, content in shells.items():
        content = _normalize_cache_buster(content)
        if _write_text(path, content, force=force):
            created.append(os.path.relpath(path, root))

    data_js = os.path.join(d["js"], "data.js")
    if not os.path.isfile(data_js):
        _write_text(data_js, _starter_data_js(with_sample=with_sample), force=True)
        created.append(os.path.relpath(data_js, root))

    if with_sample:
        img_dir = os.path.join(d["assets_images"], "project-01")
        os.makedirs(img_dir, exist_ok=True)
        proj_html = os.path.join(d["projects"], "project-01.html")
        if (not os.path.isfile(proj_html)) or force:
            try:
                html = PROJECT_HTML_TEMPLATE.format(
                    title="NEW PROJECT",
                    id=0,
                    num="01",
                    cache=CACHE_BUSTER,
                )
            except Exception:
                html = TEMPLATE_END_HTML
            _write_text(proj_html, html, force=True)
            rel = os.path.relpath(proj_html, root)
            if rel not in created:
                created.append(rel)

    readme = os.path.join(root, "README.txt")
    readme_text = (
        "Artist Showcase — generated project\n"
        "=====================================\n\n"
        "Open index.html in a browser (local server recommended).\n\n"
        "Edit content:\n"
        "  python editor.py\n\n"
        "Create a NEW empty showcase elsewhere:\n"
        "  python editor.py --init ./my-new-showcase\n\n"
        "Repair / regenerate shell files (keeps data.js):\n"
        "  python editor.py --scaffold-force\n\n"
        "Folders:\n"
        "  assets/images/  — stills, passes, posters\n"
        "  assets/videos/  — project videos\n"
        "  css/            — style.css\n"
        "  js/             — data.js (content), main.js, project.js\n"
        "  projects/       — project-XX.html + end.html\n"
    )
    if _write_text(readme, readme_text, force=force):
        created.append("README.txt")

    for folder in (d["assets_images"], d["assets_videos"]):
        keep = os.path.join(folder, ".gitkeep")
        if not os.path.isfile(keep):
            _write_text(keep, "", force=True)

    return created


def ensure_project_structure(base=None):
    """Create any missing folders/shell files without overwriting existing ones."""
    return scaffold_project(base=base, force=False, with_sample=True)



# =========================================================
# Safety Net — Auto-Repair Non-JSON data.js
# =========================================================

def _strip_line_comments(s: str) -> str:
    result = []
    i = 0
    n = len(s)
    in_string = False
    string_char = None
    escape = False
    while i < n:
        c = s[i]
        if escape:
            result.append(c)
            escape = False
            i += 1
            continue
        if c == "\\" and in_string:
            result.append(c)
            escape = True
            i += 1
            continue
        if not in_string:
            if c in ('"', "'"):
                in_string = True
                string_char = c
                result.append(c)
                i += 1
                continue
            if c == "/" and i + 1 < n and s[i + 1] == "/":
                while i < n and s[i] not in "\r\n":
                    i += 1
                continue
            result.append(c)
            i += 1
            continue
        else:
            result.append(c)
            if c == string_char:
                in_string = False
                string_char = None
            i += 1
    return "".join(result)


def _single_to_double_quotes(s: str) -> str:
    result = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == '"':
            result.append(c)
            i += 1
            while i < n:
                c2 = s[i]
                result.append(c2)
                if c2 == "\\" and i + 1 < n:
                    result.append(s[i + 1])
                    i += 2
                    continue
                if c2 == '"':
                    i += 1
                    break
                i += 1
            continue
        if c == "'":
            result.append('"')
            i += 1
            while i < n:
                c2 = s[i]
                if c2 == "\\" and i + 1 < n:
                    nxt = s[i + 1]
                    if nxt == "'":
                        result.append("'")
                    elif nxt == '"':
                        result.append('\\"')
                    else:
                        result.append(c2)
                        result.append(nxt)
                    i += 2
                    continue
                if c2 == "'":
                    result.append('"')
                    i += 1
                    break
                if c2 == '"':
                    result.append('\\"')
                    i += 1
                    continue
                result.append(c2)
                i += 1
            continue
        result.append(c)
        i += 1
    return "".join(result)


def repair_js_object_literal(text: str) -> str:
    if not text or not text.strip():
        return text
    s = text
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
    s = _strip_line_comments(s)
    s = _single_to_double_quotes(s)
    s = re.sub(
        r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:',
        r'\1"\2":',
        s
    )
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r",\s*([}\]])", r"\1", s)
    return s.strip()


def extract_js_literal(content: str, const_name: str) -> str:
    pattern = rf"const\s+{re.escape(const_name)}\s*=\s*"
    m = re.search(pattern, content)
    if not m:
        raise ValueError(f"Could not find const {const_name} in data.js")
    start = m.end()
    while start < len(content) and content[start] in " \t\r\n":
        start += 1
    if start >= len(content):
        raise ValueError(f"Empty value for const {const_name}")
    opener = content[start]
    if opener not in "{[":
        raise ValueError(f"Expected {{ or [ after const {const_name}, got {opener!r}")
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_string = False
    string_char = None
    escape = False
    i = start
    while i < len(content):
        c = content[i]
        if escape:
            escape = False
            i += 1
            continue
        if in_string:
            if c == "\\":
                escape = True
            elif c == string_char:
                in_string = False
            i += 1
            continue
        if c in ('"', "'"):
            in_string = True
            string_char = c
            i += 1
            continue
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return content[start : i + 1]
        i += 1
    raise ValueError(f"Unbalanced braces/brackets for const {const_name}")


def load_data_js():
    if not os.path.isfile(DATA_JS):
        raise FileNotFoundError(f"data.js not found at: {DATA_JS}")

    with open(DATA_JS, "r", encoding="utf-8") as f:
        content = f.read()

    artist_raw = extract_js_literal(content, "ARTIST")
    projects_raw = extract_js_literal(content, "PROJECTS")

    repaired = False

    def try_parse(raw: str, label: str):
        nonlocal repaired
        try:
            return json.loads(raw)
        except json.JSONDecodeError as first_err:
            fixed = repair_js_object_literal(raw)
            try:
                obj = json.loads(fixed)
                repaired = True
                return obj
            except json.JSONDecodeError as second_err:
                raise ValueError(
                    f"Could not parse {label} even after auto-repair.\\n"
                    f"Original error: {first_err}\\n"
                    f"After repair:   {second_err}\\n"
                    f"Repaired snippet (first 400 chars):\\n{fixed[:400]}"
                ) from second_err

    artist = try_parse(artist_raw, "ARTIST")
    projects = try_parse(projects_raw, "PROJECTS")

    if not isinstance(artist, dict):
        raise ValueError("ARTIST must be an object")
    if not isinstance(projects, list):
        raise ValueError("PROJECTS must be an array")

    for i, p in enumerate(projects):
        if not isinstance(p, dict):
            raise ValueError(f"PROJECTS[{i}] must be an object")
        p.setdefault("id", i)
        p.setdefault("file", f"project-{i + 1:02d}.html")
        p.setdefault("title", f"Project {i + 1}")
        p.setdefault("category", "")
        p.setdefault("description", "")
        p.setdefault("video", "")
        p.setdefault("poster", "")
        p.setdefault("details", {})
        p.setdefault("tools", [])
        p.setdefault("contributions", [])
        p.setdefault("chapters", [])
        p.setdefault("gallery", [])
        p.setdefault("before", "")
        p.setdefault("after", "")
        p.setdefault("passes", [])
        p.setdefault("videos", [])
        p.setdefault("artistName", "")
        p.setdefault("showArtist", True)
        p.setdefault("status", "")
        p.setdefault("tags", [])
        p.setdefault("clientHidden", False)
        fixed_chapters = []
        for ch in p["chapters"]:
            if isinstance(ch, dict) and "name" in ch:
                fixed_chapters.append({
                    "name": str(ch.get("name", "")),
                    "time": float(ch.get("time", 0) or 0)
                })
            elif isinstance(ch, (list, tuple)) and len(ch) >= 2:
                fixed_chapters.append({"name": str(ch[0]), "time": float(ch[1])})
        p["chapters"] = fixed_chapters
        fixed_contrib = []
        for c in p["contributions"]:
            if isinstance(c, (list, tuple)) and len(c) >= 2:
                fixed_contrib.append([str(c[0]), str(c[1])])
            elif isinstance(c, dict):
                fixed_contrib.append([
                    str(c.get("num", c.get("id", ""))),
                    str(c.get("name", c.get("title", "")))
                ])
        p["contributions"] = fixed_contrib

    thanks = {
        "enabled": False,
        "eyebrow": "WITH GRATITUDE",
        "heading": "THANK YOU",
        "sub": "TO EVERY DEPARTMENT THAT MADE THIS POSSIBLE",
        "note": "",
        "departments": [
            {"name": "MODELLING", "text": ""},
            {"name": "TEXTURING", "text": ""},
            {"name": "RIGGING", "text": ""},
            {"name": "ANIMATION", "text": ""},
        ],
    }
    try:
        thanks_raw = extract_js_literal(content, "THANKS")
        thanks = try_parse(thanks_raw, "THANKS")
        if not isinstance(thanks, dict):
            thanks = {"enabled": False}
        thanks.setdefault("enabled", False)
        thanks.setdefault("eyebrow", "WITH GRATITUDE")
        thanks.setdefault("heading", "THANK YOU")
        thanks.setdefault("sub", "")
        thanks.setdefault("note", "")
        thanks.setdefault("departments", [])
    except Exception:
        pass

    def load_optional(name, defaults):
        try:
            raw = extract_js_literal(content, name)
            obj = try_parse(raw, name)
            if isinstance(obj, dict):
                out = dict(defaults)
                out.update(obj)
                return out
        except Exception:
            pass
        return dict(defaults)

    home = load_optional("HOME", {
        "eyebrow": "COMPANY CREATIVE SHOWCASE",
        "heading": "SHADING DEPARTMENT\nSHOWCASE",
        "mediaType": "",
        "media": "",
    })
    end = load_optional("END", {
        "eyebrow": "PRESENTATION COMPLETE",
        "heading": "THANK YOU",
        "note": "",
        "mediaType": "",
        "media": "",
    })
    font = load_optional("FONT", {
        "family": "Segoe UI, Arial, Helvetica, sans-serif",
        "url": "",
    })
    header = load_optional("HEADER", {
        "brand": "ARTIST SHOWCASE · 2026",
    })

    for p in projects:
        fixed_gal = []
        for g in p.get("gallery") or []:
            if isinstance(g, str):
                fixed_gal.append(g)
            elif isinstance(g, dict):
                src = g.get("src") or g.get("path") or g.get("image") or ""
                if src:
                    cap = g.get("caption") or g.get("description") or g.get("desc") or ""
                    if cap:
                        fixed_gal.append({"src": src, "caption": str(cap)})
                    else:
                        fixed_gal.append(src)
        p["gallery"] = fixed_gal

        fixed_passes = []
        for g in p.get("passes") or []:
            if isinstance(g, str) and g.strip():
                fixed_passes.append(g.strip())
            elif isinstance(g, dict):
                src = (g.get("src") or g.get("path") or g.get("image") or "").strip()
                if not src:
                    continue
                name = (g.get("name") or g.get("label") or g.get("title") or "").strip()
                if name:
                    fixed_passes.append({"src": src, "name": name})
                else:
                    fixed_passes.append(src)
        p["passes"] = fixed_passes

        fixed_videos = []
        for v in p.get("videos") or []:
            if isinstance(v, str) and v.strip():
                fixed_videos.append(v.strip())
            elif isinstance(v, dict):
                src = (v.get("src") or v.get("path") or v.get("video") or "").strip()
                if not src:
                    continue
                entry = {"src": src}
                label = (v.get("label") or v.get("name") or "").strip()
                if label:
                    entry["label"] = label
                poster = (v.get("poster") or "").strip()
                if poster:
                    entry["poster"] = poster
                fixed_videos.append(entry if (label or poster) else src)
        p["videos"] = fixed_videos

    if repaired:
        try:
            save_data_js(artist, projects, thanks, home, end, font, header)
        except Exception:
            pass

    return artist, projects, thanks, home, end, font, header


def save_data_js(artist, projects, thanks=None, home=None, end=None, font=None, header=None):
    paths_block = """
/* =========================================================
   PATHS — resolve asset URLs from any page location
========================================================= */

const PATHS = {
    assetBase: window.location.pathname.includes('/projects/')
        ? '../'
        : ''
};
"""

    if os.path.isfile(DATA_JS):
        with open(DATA_JS, "r", encoding="utf-8") as f:
            original = f.read()
        paths_match = re.search(
            r"(/\*\s*=+\s*\n\s*PATHS.*?)$",
            original,
            re.DOTALL
        )
        if paths_match:
            paths_block = paths_match.group(1)

    artist_json = json.dumps(artist, indent=4, ensure_ascii=False)
    projects_json = json.dumps(projects, indent=4, ensure_ascii=False)

    thanks_block = ""
    if thanks is not None:
        thanks_json = json.dumps(thanks, indent=4, ensure_ascii=False)
        thanks_block = f"""
/* =========================================================
   THANKS SCREEN — optional slide after HOME
   Set "enabled": true to show, false to hide (skip to projects)
========================================================= */
const THANKS = {thanks_json};

"""

    home_block = ""
    if home is not None:
        home_json = json.dumps(home, indent=4, ensure_ascii=False)
        home_block = f"""
/* =========================================================
   HOME SCREEN
========================================================= */
const HOME = {home_json};

"""

    end_block = ""
    if end is not None:
        end_json = json.dumps(end, indent=4, ensure_ascii=False)
        end_block = f"""
/* =========================================================
   END SCREEN
========================================================= */
const END = {end_json};

"""

    font_block = ""
    if font is not None:
        font_json = json.dumps(font, indent=4, ensure_ascii=False)
        font_block = f"""
/* =========================================================
   CUSTOM FONT
========================================================= */
const FONT = {font_json};

"""

    header_block = ""
    if header is not None:
        header_json = json.dumps(header, indent=4, ensure_ascii=False)
        header_block = f"""
/* =========================================================
   HEADER — top bar brand
========================================================= */
const HEADER = {header_json};

"""

    new_content = f"""/* =========================================================
   ARTIST + PROJECT DATA
   This file is JSON-compatible. Edited by Python app.
   Auto-repaired on load if non-strict JS was present.
========================================================= */

const ARTIST = {artist_json};
{home_block}{end_block}{font_block}{header_block}{thanks_block}
const PROJECTS = {projects_json};

{paths_block}
"""

    os.makedirs(os.path.dirname(DATA_JS), exist_ok=True)
    with open(DATA_JS, "w", encoding="utf-8") as f:
        f.write(new_content)


# =========================================================
# Auto-generate project HTML pages
# =========================================================

PROJECT_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} · Artist Showcase 2026</title>
    <link rel="stylesheet" href="../css/style.css?v={cache}">
</head>

<!-- data-project="{id}" → maps to PROJECTS[{id}] in js/data.js -->
<body class="theme-dark" data-project="{id}">

<div id="app">

    <!-- =====================================================
         🔒 LOCKED SHELL — DO NOT EDIT
    ====================================================== -->

    <header class="topbar">
        <div class="topbar-left">
            <button class="sidebar-toggle-btn" onclick="toggleSidebar()" title="Toggle sidebar (S)">
                <span class="hamburger-line"></span>
                <span class="hamburger-line"></span>
                <span class="hamburger-line"></span>
            </button>
        </div>

        <div class="topbar-center">
            <div class="brand">ARTIST SHOWCASE · 2026</div>
        </div>

        <div class="topbar-right">
            <button class="theme-toggle-btn" id="themeToggleBtn" onclick="toggleTheme()" title="Toggle theme (T)">
                <span class="theme-icon">☀</span>
            </button>
            <div class="page-counter">
                <strong id="pageCurrent">{num}</strong>
                /
                <span id="pageTotal">{num}</span>
            </div>
        </div>
    </header>

    <div class="layout">

        <aside class="sidebar collapsed" id="sidebar">
            <div class="sidebar-header">
                <span class="sidebar-title">PROJECTS</span>
            </div>
            <nav class="sidebar-nav" id="sidebarNav"></nav>
            <div class="sidebar-footer">
                <div class="artist-info-mini">
                    <div class="artist-name-mini" id="sidebarArtistName"></div>
                    <div class="artist-role-mini" id="sidebarArtistRole"></div>
                </div>
                <a class="back-home-btn" href="../index.html">← HOME</a>
            </div>
        </aside>

        <main class="content">
            <div class="project-area" id="projectArea">

    <!-- =====================================================
         ✏️ EDITABLE CONTENT — auto-filled from PROJECTS[{id}]
         All text/images/videos come from js/data.js
    ====================================================== -->

                <div class="project-title-row">
                    <div class="section-label" id="projectNumber"></div>
                    <div class="project-title-stack">
                        <h2 class="project-title" id="projectTitle"></h2>
                        <div class="project-artist" id="projectArtist"></div>
                        <div id="projectStatus" class="tag-pill" style="display:none"></div>
                        <div id="projectTags" class="project-tags"></div>
                    </div>
                    <div class="project-category" id="projectCategory"></div>
                </div>

                <div class="project-grid">

                    <div class="project-description">
                        <div class="section-label">PROJECT BREAKDOWN</div>
                        <p class="description-text" id="projectDescription"></p>

                        <div class="details-grid" id="projectDetails"></div>

                        <div class="section-label" style="margin-top:25px">SOFTWARE</div>
                        <div class="tools" id="projectTools"></div>

                        <div class="breakdown-section">
                            <div class="section-label">MY CONTRIBUTION</div>
                            <div class="breakdown-grid" id="contributionGrid"></div>
                        </div>

                        <div class="breakdown-section">
                            <div class="section-label">PROJECT STILLS</div>
                            <div class="gallery" id="gallery"></div>
                        </div>
                    </div>

                    <div class="media-area">
                        <div class="video-source-bar" id="videoSourceBar"></div>
                        <div class="video-wrapper">
                            <div class="media-label">PROJECT VIDEO</div>
                            <video id="projectVideo" preload="metadata" playsinline>
                                Your browser does not support video.
                            </video>
                        </div>

                        <div class="video-controls">
                            <button class="control-btn" onclick="togglePlay()">▶ / ❚❚</button>
                            <button class="control-btn" onclick="restartVideo()">RESTART</button>
                            <button class="control-btn" onclick="toggleMute()">MUTE</button>
                            <div class="progress" id="progress">
                                <div class="progress-bar" id="progressBar"></div>
                            </div>
                            <button class="control-btn" onclick="fullscreenVideo()">FULL</button>
                        </div>

                        <div class="video-extra-controls">
                            <span class="video-extra-label">SPEED</span>
                            <button class="control-btn" data-rate="0.5" type="button">0.5×</button>
                            <button class="control-btn active" data-rate="1" type="button">1×</button>
                            <button class="control-btn" data-rate="2" type="button">2×</button>
                            <button class="control-btn" data-rate="2.5" type="button">2.5×</button>
                            <span class="video-extra-sep"></span>
                            <span class="video-extra-label">CLIP</span>
                            <button class="control-btn active" data-clip="full" type="button">FULL</button>
                            <button class="control-btn" data-clip="15" type="button">15s</button>
                            <button class="control-btn" data-clip="30" type="button">30s</button>
                            <button class="control-btn" data-clip="45" type="button">45s</button>
                        </div>

                        <div class="section-label">BREAKDOWN CHAPTERS</div>
                        <div class="chapters" id="chapters"></div>

                        <div class="media-tabs" id="mediaTabs">
                            <button type="button" class="media-tab-btn active" data-media-tab="compare">BEFORE / AFTER</button>
                            <button type="button" class="media-tab-btn" data-media-tab="passes">RENDER PASSES</button>
                        </div>
                        <div class="media-tab-panel active" id="mediaPanelCompare">
                            <div class="compare">
                                <img id="beforeImage" src="" alt="Before">
                                <img id="afterImage" class="after-image" src="" alt="After">
                                <div class="compare-line" id="compareLine"></div>
                                <div class="compare-label before-label">BEFORE</div>
                                <div class="compare-label after-label">FINAL</div>
                                <input type="range" min="0" max="100" value="50" class="compare-slider" id="compareSlider">
                            </div>
                        </div>
                        <div class="media-tab-panel" id="mediaPanelPasses">
                            <div class="passes-split" id="passesCarousel">
                                <div class="passes-split-layer is-base" id="passesBase">
                                    <img id="passesBaseImg" src="" alt="">
                                </div>
                                <div class="passes-split-layer is-reveal diag" id="passesReveal">
                                    <img id="passesRevealImg" src="" alt="">
                                </div>
                                <div class="passes-split-bar">
                                    <div class="passes-carousel-name" id="passesCarouselName">—</div>
                                    <div class="passes-carousel-nav">
                                        <button type="button" class="passes-carousel-btn" id="passesPrev" title="Previous">‹</button>
                                        <div class="passes-carousel-dots" id="passesCarouselDots"></div>
                                        <button type="button" class="passes-carousel-btn" id="passesNext" title="Next">›</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                </div>

                <section class="passes-section" id="passesSection" style="display:none">
                    <div class="section-label">RENDER PASSES</div>
                    <div class="passes-grid" id="passesGrid"></div>
                </section>

            </div>
        </main>
    </div>

    <footer class="bottom-bar">
        <a class="bottom-button" id="prevBtn" href="#">← PREVIOUS</a>
        <div class="help-text">
            ← → NAVIGATE · SPACE PLAY · F FULLSCREEN · H HELP · S SIDEBAR · T THEME
        </div>
        <a class="bottom-button" id="nextBtn" href="#">NEXT →</a>
    </footer>

    <div class="help-panel" id="helpPanel">
        <div class="help-box">
            <h2>PRESENTATION CONTROLS</h2>
            <div class="shortcut"><span>Next project</span><span class="key">→</span></div>
            <div class="shortcut"><span>Previous project</span><span class="key">←</span></div>
            <div class="shortcut"><span>Play / Pause</span><span class="key">SPACE</span></div>
            <div class="shortcut"><span>Restart video</span><span class="key">R</span></div>
            <div class="shortcut"><span>Fullscreen</span><span class="key">F</span></div>
            <div class="shortcut"><span>Mute</span><span class="key">M</span></div>
            <div class="shortcut"><span>Toggle sidebar</span><span class="key">S</span></div>
            <div class="shortcut"><span>Toggle theme</span><span class="key">T</span></div>
            <div class="shortcut"><span>Close help</span><span class="key">H / ESC</span></div>
        </div>
    </div>

    <div class="lightbox" id="lightbox" onclick="closeLightbox()">
        <div class="lightbox-close" onclick="closeLightbox()">×</div>
        <button class="lightbox-nav lightbox-prev" type="button" onclick="lightboxPrev(event)" title="Previous">‹</button>
        <img id="lightboxImage" src="" alt="" onclick="event.stopPropagation()">
        <button class="lightbox-nav lightbox-next" type="button" onclick="lightboxNext(event)" title="Next">›</button>
        <div class="lightbox-caption" id="lightboxCaption" onclick="event.stopPropagation()"></div>
        <div class="lightbox-counter" id="lightboxCounter"></div>
    </div>

    <div class="toast" id="toast">READY</div>

</div>

<script src="../js/data.js?v={cache}"></script>
<script src="../js/main.js?v={cache}"></script>
<script src="../js/features.js?v={cache}"></script>
<script src="../js/project.js?v={cache}"></script>
</body>
</html>
"""


def generate_project_html(project_id: int, file_name: str, title: str = "NEW PROJECT") -> str:
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    img_folder = os.path.join(ASSETS_IMAGES, f"project-{project_id + 1:02d}")
    os.makedirs(img_folder, exist_ok=True)
    os.makedirs(ASSETS_VIDEOS, exist_ok=True)

    num = f"{project_id + 1:02d}"
    safe_title = (title or "Project").replace("<", "").replace(">", "")
    html = PROJECT_HTML_TEMPLATE.format(
        id=project_id,
        num=num,
        title=safe_title,
        cache=CACHE_BUSTER,
    )

    out_path = os.path.join(PROJECTS_DIR, file_name)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


def backup_data_js(keep: int = 10):
    if not os.path.isfile(DATA_JS):
        return None
    bak_dir = os.path.join(BASE_DIR, "js", "backups")
    os.makedirs(bak_dir, exist_ok=True)
    import time
    from pathlib import Path
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(bak_dir, f"data.js.bak.{stamp}")
    shutil.copy2(DATA_JS, dest)
    bak_files = sorted(
        [os.path.join(bak_dir, f) for f in os.listdir(bak_dir) if f.startswith("data.js.bak.")],
        key=os.path.getmtime,
        reverse=True,
    )
    for old in bak_files[keep:]:
        try:
            os.remove(old)
        except OSError:
            pass
    return dest


def ensure_asset_folders(projects):
    created = []
    os.makedirs(ASSETS_VIDEOS, exist_ok=True)
    for i, _ in enumerate(projects):
        folder = os.path.join(ASSETS_IMAGES, f"project-{i + 1:02d}")
        if not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
            created.append(folder)
    return created


def validate_project_assets(projects):
    issues = []
    for i, p in enumerate(projects):
        label = f"[{i + 1:02d}] {p.get('title', '(untitled)')}"
        if not (p.get("title") or "").strip():
            issues.append(f"{label}: empty title")
        if not (p.get("file") or "").strip():
            issues.append(f"{label}: missing HTML file name")
        else:
            html_path = os.path.join(PROJECTS_DIR, p["file"])
            if not os.path.isfile(html_path):
                issues.append(f"{label}: HTML not found → projects/{p['file']}")
        for key in ("video", "before", "after"):
            rel = (p.get(key) or "").strip()
            if not rel:
                issues.append(f"{label}: no {key} path set")
                continue
            abs_path = os.path.join(BASE_DIR, rel.replace("/", os.sep))
            if not os.path.isfile(abs_path):
                issues.append(f"{label}: missing {key} file → {rel}")
        for g in p.get("gallery") or []:
            if not g:
                continue
            if isinstance(g, dict):
                gpath = g.get("src") or g.get("path") or g.get("image") or ""
            else:
                gpath = str(g)
            if not gpath:
                continue
            abs_path = os.path.join(BASE_DIR, gpath.replace("/", os.sep))
            if not os.path.isfile(abs_path):
                issues.append(f"{label}: missing gallery image → {gpath}")
        for g in p.get("passes") or []:
            if not g:
                continue
            if isinstance(g, dict):
                gpath = g.get("src") or g.get("path") or ""
            else:
                gpath = str(g)
            if not gpath:
                continue
            abs_path = os.path.join(BASE_DIR, gpath.replace("/", os.sep))
            if not os.path.isfile(abs_path):
                issues.append(f"{label}: missing pass image → {gpath}")
        for v in p.get("videos") or []:
            if isinstance(v, dict):
                vpath = v.get("src") or v.get("path") or ""
            else:
                vpath = str(v) if v else ""
            if not vpath:
                continue
            abs_path = os.path.join(BASE_DIR, vpath.replace("/", os.sep))
            if not os.path.isfile(abs_path):
                issues.append(f"{label}: missing extra video → {vpath}")
        if p.get("id") != i:
            issues.append(f"{label}: id={p.get('id')} but index is {i} (will fix on save)")
    return issues


def regenerate_all_html(projects, overwrite=True):
    written = []
    for i, p in enumerate(projects):
        p["id"] = i
        file_name = p.get("file") or f"project-{i + 1:02d}.html"
        p["file"] = file_name
        out = generate_project_html(i, file_name, p.get("title", "Project"))
        written.append(out)
    return written


def sync_html_data_project_attrs(projects):
    updated = []
    for i, p in enumerate(projects):
        file_name = p.get("file") or ""
        if not file_name:
            continue
        path = os.path.join(PROJECTS_DIR, file_name)
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        new_text, n = re.subn(
            r'data-project\s*=\s*["\']?\d+["\']?',
            f'data-project="{i}"',
            text,
            count=1,
        )
        title = (p.get("title") or "Project").replace("<", "").replace(">", "")
        new_text2, n2 = re.subn(
            r"<title>.*?</title>",
            f"<title>{title} · Artist Showcase 2026</title>",
            new_text,
            count=1,
            flags=re.DOTALL,
        )
        if n or n2:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_text2)
            updated.append(path)
    return updated


def export_json(artist, projects, dest_path: str, thanks=None) -> None:
    payload = {"artist": artist, "projects": projects}
    if thanks is not None:
        payload["thanks"] = thanks
    with open(dest_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def import_json(src_path: str):
    with open(src_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    artist = payload.get("artist") or {}
    projects = payload.get("projects") or []
    thanks = payload.get("thanks")
    if not isinstance(artist, dict) or not isinstance(projects, list):
        raise ValueError("JSON must contain 'artist' object and 'projects' array")
    for i, p in enumerate(projects):
        p["id"] = i
    return artist, projects, thanks, home, end, font, header


# =========================================================
# Helpers
# =========================================================

def sanitize_filename(name):
    name = name.replace(" ", "_")
    name = re.sub(r"[^\w\-.]+", "_", name)
    return name


def safe_copy(src, dst_folder):
    if not os.path.isfile(src):
        return None
    os.makedirs(dst_folder, exist_ok=True)

    filename = sanitize_filename(os.path.basename(src))
    dst = os.path.join(dst_folder, filename)

    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copy2(src, dst)

    rel = os.path.relpath(dst, BASE_DIR).replace("\\", "/")
    return rel


def rel_to_abs(rel_path):
    return os.path.join(BASE_DIR, rel_path.replace("/", os.sep))


# =========================================================
# Reusable widgets
# =========================================================

class SectionDivider(QFrame):
    """A horizontal labeled divider for separating form sections."""
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setObjectName("sectionDivider")
        self.setFrameShape(QFrame.Shape.NoFrame)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 14, 0, 6)
        row.setSpacing(10)

        left = QFrame()
        left.setObjectName("dividerLine")
        left.setFixedHeight(1)
        left.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        label = QLabel(text)
        label.setObjectName("dividerLabel")

        right = QFrame()
        right.setObjectName("dividerLine")
        right.setFixedHeight(1)
        right.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        row.addWidget(left, 1)
        if text:
            row.addWidget(label, 0)
        row.addWidget(right, 1)


class FilePickerRow(QWidget):
    def __init__(self, label, value="", filetypes=None, dest_folder=None, parent=None):
        super().__init__(parent)
        self.filetypes = filetypes or [("All files", "*.*")]
        self.dest_folder = dest_folder

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.edit = QLineEdit(value)
        self.edit.setPlaceholderText(f"{label} path…")

        self.btn = QPushButton("Browse…")
        self.btn.setFixedWidth(88)
        self.btn.clicked.connect(self.browse)

        layout.addWidget(self.edit, 1)
        layout.addWidget(self.btn)

    def browse(self):
        filters = ";;".join([f"{name} ({pat})" for name, pat in self.filetypes])
        path, _ = QFileDialog.getOpenFileName(self, "Select file", "", filters)
        if not path:
            return
        if self.dest_folder:
            rel = safe_copy(path, self.dest_folder)
            if rel:
                self.edit.setText(rel)
        else:
            self.edit.setText(path)

    def text(self):
        return self.edit.text().strip()

    def setText(self, value):
        self.edit.setText(value or "")


class GalleryPicker(QWidget):
    def __init__(self, values=None, dest_folder=None, parent=None):
        super().__init__(parent)
        self.dest_folder = dest_folder

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.text = QTextEdit()
        self.text.setPlaceholderText("One image path per line. Optional caption: path | short description")
        self.text.setFixedHeight(88)
        if values:
            self.setValues(values)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("＋ Add images…")
        self.btn_add.clicked.connect(self.add_images)
        btn_row.addWidget(self.btn_add)
        btn_row.addStretch()

        layout.addWidget(self.text)
        layout.addLayout(btn_row)

    def add_images(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select images", "",
            "Images (*.jpg *.jpeg *.png *.webp);;All files (*.*)"
        )
        if not paths:
            return
        rels = []
        for p in paths:
            if self.dest_folder:
                rel = safe_copy(p, self.dest_folder)
                if rel:
                    rels.append(rel)
            else:
                rels.append(p)

        existing = self.text.toPlainText().strip()
        joined = "\n".join(rels)
        self.text.setPlainText((existing + "\n" + joined) if existing else joined)

    def values(self):
        out = []
        for line in self.text.toPlainText().splitlines():
            line = line.strip()
            if not line:
                continue
            if " | " in line:
                src, cap = line.split(" | ", 1)
                src, cap = src.strip(), cap.strip()
                if src and cap:
                    out.append({"src": src, "caption": cap})
                elif src:
                    out.append(src)
            else:
                out.append(line)
        return out

    def setValues(self, values):
        lines = []
        for v in values or []:
            if isinstance(v, dict):
                src = v.get("src") or v.get("path") or ""
                cap = v.get("caption") or v.get("description") or ""
                lines.append(f"{src} | {cap}" if cap else src)
            else:
                lines.append(str(v))
        self.text.setPlainText("\n".join(lines))


class NamedImagePicker(QWidget):
    def __init__(self, values=None, dest_folder=None, placeholder=None, parent=None):
        super().__init__(parent)
        self.dest_folder = dest_folder
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.text = QTextEdit()
        self.text.setPlaceholderText(
            placeholder
            or "One image per line. Optional name: path | PassName\n"
               "e.g. assets/images/project-01/VickeryAttic.AO.png | VickeryAttic.AO"
        )
        self.text.setFixedHeight(116)
        if values:
            self.setValues(values)
        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("＋ Add images…")
        self.btn_add.clicked.connect(self.add_images)
        btn_row.addWidget(self.btn_add)
        btn_row.addStretch()
        layout.addWidget(self.text)
        layout.addLayout(btn_row)

    def add_images(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select pass images", "",
            "Images (*.jpg *.jpeg *.png *.webp *.exr *.tif *.tiff);;All files (*.*)"
        )
        if not paths:
            return
        lines = []
        for p in paths:
            if self.dest_folder:
                rel = safe_copy(p, self.dest_folder)
            else:
                rel = p
            if not rel:
                continue
            stem = os.path.splitext(os.path.basename(p))[0]
            lines.append(f"{rel} | {stem}")
        existing = self.text.toPlainText().strip()
        joined = "\n".join(lines)
        self.text.setPlainText((existing + "\n" + joined) if existing else joined)

    def values(self):
        out = []
        for line in self.text.toPlainText().splitlines():
            line = line.strip()
            if not line:
                continue
            if " | " in line:
                src, name = line.split(" | ", 1)
                src, name = src.strip(), name.strip()
                if src and name:
                    out.append({"src": src, "name": name})
                elif src:
                    out.append(src)
            else:
                out.append(line)
        return out

    def setValues(self, values):
        lines = []
        for v in values or []:
            if isinstance(v, dict):
                src = v.get("src") or v.get("path") or ""
                name = v.get("name") or v.get("label") or ""
                lines.append(f"{src} | {name}" if name else src)
            else:
                lines.append(str(v))
        self.text.setPlainText("\n".join(lines))


class VideosPicker(QWidget):
    def __init__(self, values=None, dest_folder=None, parent=None):
        super().__init__(parent)
        self.dest_folder = dest_folder
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.text = QTextEdit()
        self.text.setPlaceholderText(
            "Optional multi-video list (leave empty to use single Video field only).\n"
            "One per line: path | Label\n"
            "e.g. assets/videos/main.mp4 | Main Lookdev"
        )
        self.text.setFixedHeight(88)
        if values:
            self.setValues(values)
        btn_row = QHBoxLayout()
        btn = QPushButton("＋ Add videos…")
        btn.clicked.connect(self.add_videos)
        btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addWidget(self.text)
        layout.addLayout(btn_row)

    def add_videos(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select videos", "",
            "Videos (*.mp4 *.webm *.mov *.mkv);;All files (*.*)"
        )
        if not paths:
            return
        lines = []
        for p in paths:
            if self.dest_folder:
                rel = safe_copy(p, self.dest_folder)
            else:
                rel = p
            if not rel:
                continue
            stem = os.path.splitext(os.path.basename(p))[0]
            lines.append(f"{rel} | {stem}")
        existing = self.text.toPlainText().strip()
        joined = "\n".join(lines)
        self.text.setPlainText((existing + "\n" + joined) if existing else joined)

    def values(self):
        out = []
        for line in self.text.toPlainText().splitlines():
            line = line.strip()
            if not line:
                continue
            if " | " in line:
                src, label = line.split(" | ", 1)
                src, label = src.strip(), label.strip()
                if src and label:
                    out.append({"src": src, "label": label})
                elif src:
                    out.append(src)
            else:
                out.append(line)
        return out

    def setValues(self, values):
        lines = []
        for v in values or []:
            if isinstance(v, dict):
                src = v.get("src") or v.get("path") or ""
                label = v.get("label") or v.get("name") or ""
                lines.append(f"{src} | {label}" if label else src)
            else:
                lines.append(str(v))
        self.text.setPlainText("\n".join(lines))


# =========================================================
# Main Window
# =========================================================


# =========================================================
# Live preview for Home / End screens (no WebEngine required)
# =========================================================


class ScreenPreviewWidget(QWidget):
    """Scaled visual preview of Home / End / Thanks / Project screens."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = "home"  # home | end | thanks | project
        self._brand = "ARTIST SHOWCASE · 2026"
        self._eyebrow = ""
        self._heading = ""
        self._sub = ""
        self._note = ""
        self._media_type = ""
        self._media_path = ""
        self._artist_name = ""
        self._artist_role = ""
        self._project_count = 0
        self._depts = []  # list of (name, text)
        self._enabled = True
        self._category = ""
        self._description = ""
        self._project_artist = ""  # per-project optional
        self._pixmap = None
        self.setMinimumWidth(280)
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_mode(self, mode: str):
        self._mode = mode if mode in ("home", "end", "thanks", "project") else "home"
        self.update()

    def set_data(self, **kw):
        self._brand = kw.get("brand") or self._brand or "ARTIST SHOWCASE · 2026"
        if "eyebrow" in kw:
            self._eyebrow = kw.get("eyebrow") or ""
        if "heading" in kw:
            self._heading = kw.get("heading") or ""
        if "sub" in kw:
            self._sub = kw.get("sub") or ""
        if "note" in kw:
            self._note = kw.get("note") or ""
        if "media_type" in kw:
            mt = (kw.get("media_type") or "").lower()
            self._media_type = "" if mt in ("", "(none)", "none") else mt
        if "media_path" in kw:
            self._media_path = kw.get("media_path") or ""
        if "artist_name" in kw:
            self._artist_name = kw.get("artist_name") or ""
        if "artist_role" in kw:
            self._artist_role = kw.get("artist_role") or ""
        if "project_count" in kw:
            self._project_count = int(kw.get("project_count") or 0)
        if "depts" in kw:
            self._depts = kw.get("depts") or []
        if "enabled" in kw:
            self._enabled = bool(kw.get("enabled"))
        if "category" in kw:
            self._category = kw.get("category") or ""
        if "description" in kw:
            self._description = kw.get("description") or ""
        if "project_artist" in kw:
            self._project_artist = kw.get("project_artist") or ""
        self._load_pixmap()
        self.update()

    def _load_pixmap(self):
        self._pixmap = None
        if not self._media_path or self._media_type == "video":
            return
        full = self._media_path
        if not os.path.isabs(full):
            full = os.path.join(BASE_DIR, full.replace("/", os.sep))
        if os.path.isfile(full):
            pm = QPixmap(full)
            if not pm.isNull():
                self._pixmap = pm

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(10, 10, 10))
        p.setPen(QPen(QColor(40, 36, 28), 1))
        p.drawRect(0, 0, w - 1, h - 1)

        # Brand bar
        p.fillRect(0, 0, w, 26, QColor(14, 14, 14))
        p.setPen(QColor(180, 160, 100))
        f_brand = QFont("Segoe UI", 8)
        p.setFont(f_brand)
        p.drawText(QRect(0, 0, w, 26), Qt.AlignmentFlag.AlignCenter, self._brand)

        pad = 16
        top = 34
        area_h = h - top - 10

        if self._mode == "thanks":
            self._paint_thanks(p, pad, top, w - 2 * pad, area_h)
        elif self._mode == "project":
            self._paint_project(p, pad, top, w - 2 * pad, area_h)
        elif self._mode in ("home", "end"):
            has_media = bool(self._media_type and self._media_path)
            if has_media:
                left_w = int(w * 0.48)
                right_x = left_w + 10
                right_w = w - right_x - pad
                self._paint_text_block(p, pad, top, left_w - pad, area_h)
                self._paint_media(p, right_x, top + 6, right_w, area_h - 12)
            else:
                self._paint_text_block(p, pad, top, w - 2 * pad, area_h, centered=True)
        p.end()

    def _paint_text_block(self, p, x, y, bw, bh, centered=False):
        text_align = (
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
            if centered
            else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        cy = y
        p.setPen(QColor(201, 169, 98))
        f_eye = QFont("Segoe UI", 8, QFont.Weight.DemiBold)
        p.setFont(f_eye)
        p.drawText(QRect(x, cy, bw, 16), text_align, (self._eyebrow or "").upper())
        cy += 20
        p.setPen(QColor(245, 245, 245))
        f_head = QFont("Segoe UI", 16, QFont.Weight.Light)
        p.setFont(f_head)
        heading = (self._heading or "").replace("\\n", "\n")
        head_rect = QRect(x, cy, bw, min(110, int(bh * 0.36)))
        p.drawText(head_rect, text_align | Qt.TextFlag.TextWordWrap, heading)
        fm = p.fontMetrics()
        lines = heading.count("\n") + 1
        cy += min(110, max(fm.height() * lines + 6, 40)) + 10

        if self._mode == "home":
            card_w = min(bw, 210) if not centered else min(bw, 230)
            card_h = 80
            cx = x + (bw - card_w) // 2 if centered else x
            card = QRect(cx, cy, card_w, card_h)
            p.setBrush(QBrush(QColor(22, 20, 14, 180)))
            p.setPen(QPen(QColor(201, 169, 98, 140), 1))
            p.drawRect(card)
            p.setPen(QColor(160, 150, 120))
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
            count = f"{self._project_count:02d} PROJECTS" if self._project_count else "PROJECTS"
            p.drawText(QRect(cx, cy + 10, card_w, 14), Qt.AlignmentFlag.AlignHCenter, count)
            p.setPen(QColor(240, 240, 240))
            p.setFont(QFont("Segoe UI", 10))
            p.drawText(QRect(cx, cy + 28, card_w, 20), Qt.AlignmentFlag.AlignHCenter, self._artist_name or "ARTIST")
            p.setPen(QColor(201, 169, 98))
            p.setFont(QFont("Segoe UI", 7))
            p.drawText(QRect(cx, cy + 50, card_w, 14), Qt.AlignmentFlag.AlignHCenter, self._artist_role or "")
        else:
            if self._note:
                p.setPen(QColor(160, 160, 160))
                p.setFont(QFont("Segoe UI", 9))
                p.drawText(QRect(x, cy, bw, 48), text_align | Qt.TextFlag.TextWordWrap, self._note)

    def _paint_media(self, p, x, y, mw, mh):
        aspect = 16 / 10
        box_w, box_h = mw, int(mw / aspect)
        if box_h > mh:
            box_h = mh
            box_w = int(box_h * aspect)
        bx = x + (mw - box_w) // 2
        by = y + (mh - box_h) // 2
        frame = QRect(bx, by, box_w, box_h)
        p.setBrush(QBrush(QColor(8, 8, 8)))
        p.setPen(QPen(QColor(201, 169, 98, 160), 1))
        p.drawRect(frame)
        if self._media_type == "video":
            p.setPen(QColor(180, 180, 180))
            p.setFont(QFont("Segoe UI", 10))
            p.drawText(frame, Qt.AlignmentFlag.AlignCenter, "▶ VIDEO")
        elif self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                box_w - 2, box_h - 2,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            sx = max(0, (scaled.width() - (box_w - 2)) // 2)
            sy = max(0, (scaled.height() - (box_h - 2)) // 2)
            p.drawPixmap(bx + 1, by + 1, scaled, sx, sy, box_w - 2, box_h - 2)
        else:
            p.setPen(QColor(100, 100, 100))
            p.setFont(QFont("Segoe UI", 9))
            p.drawText(frame, Qt.AlignmentFlag.AlignCenter, "IMAGE")

    def _paint_thanks(self, p, x, y, bw, bh):
        if not self._enabled:
            p.setPen(QColor(120, 120, 120))
            p.setFont(QFont("Segoe UI", 11))
            p.drawText(QRect(x, y, bw, bh), Qt.AlignmentFlag.AlignCenter, "Thanks slide is OFF\n(hidden in presentation)")
            return
        cy = y + 4
        p.setPen(QColor(201, 169, 98))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.drawText(QRect(x, cy, bw, 16), Qt.AlignmentFlag.AlignHCenter, (self._eyebrow or "").upper())
        cy += 22
        p.setPen(QColor(245, 245, 245))
        p.setFont(QFont("Segoe UI", 18, QFont.Weight.Light))
        p.drawText(QRect(x, cy, bw, 28), Qt.AlignmentFlag.AlignHCenter, self._heading or "THANK YOU")
        cy += 32
        if self._sub:
            p.setPen(QColor(160, 150, 120))
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(QRect(x, cy, bw, 16), Qt.AlignmentFlag.AlignHCenter, self._sub)
            cy += 20
        if self._note:
            p.setPen(QColor(140, 140, 140))
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(QRect(x, cy, bw, 28), Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap, self._note)
            cy += 32
        # Department cards in grid
        depts = self._depts[:6]
        if not depts:
            return
        cols = 2 if len(depts) > 1 else 1
        gap = 8
        card_w = (bw - gap * (cols - 1)) // cols
        card_h = 52
        for i, (name, txt) in enumerate(depts):
            col, row = i % cols, i // cols
            cx = x + col * (card_w + gap)
            cy2 = cy + row * (card_h + gap)
            if cy2 + card_h > y + bh:
                break
            r = QRect(cx, cy2, card_w, card_h)
            p.setBrush(QBrush(QColor(22, 20, 14, 160)))
            p.setPen(QPen(QColor(201, 169, 98, 100), 1))
            p.drawRect(r)
            p.setPen(QColor(201, 169, 98))
            p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            p.drawText(QRect(cx + 8, cy2 + 6, card_w - 16, 14), Qt.AlignmentFlag.AlignLeft, (name or "").upper())
            p.setPen(QColor(150, 150, 150))
            p.setFont(QFont("Segoe UI", 7))
            snippet = (txt or "")[:80]
            p.drawText(QRect(cx + 8, cy2 + 22, card_w - 16, 26), Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, snippet)

    def _paint_project(self, p, x, y, bw, bh):
        cy = y + 6
        p.setPen(QColor(201, 169, 98))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        p.drawText(QRect(x, cy, bw, 14), Qt.AlignmentFlag.AlignLeft, "PROJECT")
        cy += 18
        p.setPen(QColor(245, 245, 245))
        p.setFont(QFont("Segoe UI", 15, QFont.Weight.Light))
        p.drawText(QRect(x, cy, bw, 28), Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, self._heading or "Untitled")
        cy += 32
        if self._category:
            p.setPen(QColor(160, 150, 120))
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(QRect(x, cy, bw, 16), Qt.AlignmentFlag.AlignLeft, self._category)
            cy += 20
        # Optional per-project artist
        artist_line = self._project_artist or self._artist_name
        if artist_line:
            p.setPen(QColor(201, 169, 98))
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            label = self._project_artist if self._project_artist else self._artist_name
            tag = "ARTIST" if self._project_artist else "ARTIST (global)"
            p.drawText(QRect(x, cy, bw, 14), Qt.AlignmentFlag.AlignLeft, f"{tag}:  {label}")
            cy += 20
        if self._description:
            p.setPen(QColor(150, 150, 150))
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(
                QRect(x, cy, bw, bh - (cy - y) - 8),
                Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
                self._description[:280],
            )




class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Artist Showcase — Data Editor")
        self.resize(1480, 920)
        self.setMinimumSize(1180, 720)

        try:
            self.artist, self.projects, self.thanks, self.home, self.end, self.font, self.header = load_data_js()
        except Exception as e:
            QMessageBox.critical(
                None, "Load error",
                f"Failed to load js/data.js:\n\n{e}\n\n"
                "The editor will start with empty defaults."
            )
            self.artist = {"name": "ARTIST NAME", "role": "ROLE"}
            self.thanks = {
                "enabled": False,
                "eyebrow": "WITH GRATITUDE",
                "heading": "THANK YOU",
                "sub": "",
                "note": "",
                "departments": [
                    {"name": "MODELLING", "text": ""},
                    {"name": "TEXTURING", "text": ""},
                    {"name": "RIGGING", "text": ""},
                    {"name": "ANIMATION", "text": ""},
                ],
            }
            self.projects = [{
                "id": 0,
                "file": "project-01.html",
                "title": "NEW PROJECT",
                "category": "CATEGORY",
                "description": "",
                "video": "",
                "poster": "",
                "details": {},
                "tools": [],
                "contributions": [],
                "chapters": [],
                "gallery": [],
                "before": "",
                "after": "",
                "passes": [],
                "videos": []
            }]
            self.home = {
                "eyebrow": "COMPANY CREATIVE SHOWCASE",
                "heading": "SHADING DEPARTMENT\nSHOWCASE",
                "mediaType": "",
                "media": "",
            }
            self.end = {
                "eyebrow": "PRESENTATION COMPLETE",
                "heading": "THANK YOU",
                "note": "",
                "mediaType": "",
                "media": "",
            }
            self.font = {
                "family": "Segoe UI, Arial, Helvetica, sans-serif",
                "url": "",
            }
        self.current_index = 0
        self.entries = {}
        self._unsaved = False
        self._loading_form = False
        self._compact_mode = True
        self._preview_enabled = True
        self._project_locked = False
        self._editor_theme = "dark"  # dark | light | slate

        self._build_toolbar()
        self._build_ui()
        self._build_status_bar()
        self._apply_styles()
        self._install_shortcuts()
        self._wire_dirty_signals()

        self._load_project_list()
        self._load_project(0)
        self._sync_toolbar_info()
        self._mark_clean()

    # ---------- Menu + compact toolbar (works on small → large screens) ----------
    def _build_toolbar(self):
        def mk(text, tip, slot, shortcut=None):
            act = QAction(text, self)
            act.setToolTip(tip)
            if shortcut:
                act.setShortcut(shortcut)
            act.triggered.connect(slot)
            return act

        # ---- Menu bar (all commands, no crowding) ----
        mb = self.menuBar()

        m_file = mb.addMenu("&File")
        self.save_action = mk("Save", "Save current project", self.save_current_project, "Ctrl+S")
        self.save_all_action = mk("Save All", "Save everything to js/data.js", self.save_all, "Ctrl+Shift+S")
        m_file.addAction(self.save_action)
        m_file.addAction(self.save_all_action)
        m_file.addSeparator()
        m_file.addAction(mk("Reload from Disk", "Reload data.js from disk", self.reload_from_disk, "Ctrl+R"))
        m_file.addAction(mk("Repair data.js", "Force repair data.js", self.force_repair))
        m_file.addAction(mk("Backup…", "Snapshot data.js version", self.backup_version))
        m_file.addSeparator()
        m_file.addAction(mk("Export JSON…", "Export JSON", self.export_json_action))
        m_file.addAction(mk("Import JSON…", "Import JSON", self.import_json_action))
        m_file.addAction(mk("Zip Delivery…", "Export client zip (no editor)", self.export_delivery_zip))
        m_file.addSeparator()
        m_file.addAction(mk("New Showcase…", "Create a full new showcase folder", self.new_showcase_folder, "Ctrl+Shift+N"))

        m_project = mb.addMenu("&Project")
        m_project.addAction(mk("New Project", "Create a new project page", self.add_project, "Ctrl+N"))
        m_project.addAction(mk("Duplicate Project", "Duplicate current project", self.duplicate_project, "Ctrl+D"))
        self.delete_action = mk("Delete Project", "Delete current project", self.delete_project, "Delete")
        m_project.addAction(self.delete_action)
        m_project.addSeparator()
        m_project.addAction(mk("Validate Assets", "Check for missing assets", self.validate_assets, "Ctrl+Shift+V"))
        m_project.addAction(mk("Regenerate HTML", "Regenerate HTML pages", self.regenerate_html_menu))
        m_project.addAction(mk("Bulk Import Stills…", "Import folder into gallery", self.bulk_import_gallery))

        m_run = mb.addMenu("&Run")
        m_run.addAction(mk("Run Showcase", "Open final showcase (index.html) in browser", self.run_showcase_html, "F5"))
        m_run.addAction(mk("Open Project Page", "Open current project HTML in browser", self.run_current_project_html, "F6"))
        m_run.addAction(mk("Open Pass Viewer", "Open Pass Breakdown viewer", self._open_breakdown_viewer, "F7"))
        m_run.addSeparator()
        m_run.addAction(mk("Publish Project", "Save All + project viewer + open project page", self.publish_project, "F8"))
        m_run.addAction(mk("Publish All Projects", "Save All + write viewers for every project", self.publish_all_projects))
        m_run.addAction(mk("Asset Health…", "List missing/broken pass & media images", self.asset_health_panel, "F9"))
        m_run.addAction(mk("Client Package…", "Zip site + viewer (no editor) for delivery", self.export_client_package))

        m_view = mb.addMenu("&View")
        self.act_preview = mk("Toggle Live Preview", "Show or hide live previews", self._toggle_preview)
        self.act_density = mk("Toggle Compact Layout", "Compact / comfortable spacing", self._toggle_density)
        m_view.addAction(self.act_preview)
        m_view.addAction(self.act_density)
        m_view.addSeparator()
        self.act_lock = mk("Lock Project (presenting)", "Block edits while presenting", self.toggle_project_lock)
        self.act_lock.setCheckable(True)
        m_view.addAction(self.act_lock)
        m_view.addSeparator()
        m_view.addAction(mk("Undock Preview Window", "Open preview on a separate window / second monitor", self.undock_preview_window, "Ctrl+Shift+P"))
        m_view.addAction(mk("Undock Pass Breakdown", "Open Pass Breakdown in its own window", self.undock_pass_breakdown))
        m_view.addAction(mk("Redock Floating Windows", "Bring undocked windows back", self.redock_floating_windows))
        m_view.addSeparator()
        m_view.addAction(mk("Relink Missing Assets…", "Search project folders and fix broken image paths", self.relink_missing_assets, "Ctrl+Shift+R"))
        self.act_watch = mk("Watch Project Folder", "Auto-detect new images in project assets folder", self.toggle_watch_folder)
        self.act_watch.setCheckable(True)
        m_view.addAction(self.act_watch)
        m_view.addAction(mk("Dock Preview Panel", "Native dockable preview (like Nuke)", self.toggle_preview_dock))

        m_help = mb.addMenu("&Help")
        m_help.addAction(mk("Studio Guide", "How to use Showcase + Pass Breakdown", self.show_help_guide, "F1"))
        m_help.addAction(mk("Keyboard Shortcuts", "All shortcuts", self.show_help_shortcuts))
        m_help.addAction(mk("Voice-over & Soundtrack", "How VO and audio work", self.show_help_audio))
        m_help.addSeparator()
        m_help.addAction(mk("About Studio", "Version and components", self.show_help_about))

        # ---- Compact primary toolbar ----
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(16, 16))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        try:
            tb.setStyleSheet("QToolBar { spacing: 4px; padding: 2px 6px; }")
        except Exception:
            pass
        self.addToolBar(tb)

        tb.addAction(self.save_all_action)
        tb.addAction(self.save_action)
        tb.addSeparator()

        # Project overflow menu button
        self.btn_project_menu = QToolButton()
        self.btn_project_menu.setText("Project ▾")
        self.btn_project_menu.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_project_menu.setFixedHeight(28)
        self.btn_project_menu.setToolTip("Project actions")
        pm = QMenu(self.btn_project_menu)
        pm.addAction(mk("New Project", "Create a new project page", self.add_project))
        pm.addAction(mk("Duplicate", "Duplicate current project", self.duplicate_project))
        pm.addAction(self.delete_action)
        pm.addSeparator()
        pm.addAction(mk("Validate", "Check for missing assets", self.validate_assets))
        pm.addAction(mk("Regen HTML", "Regenerate HTML pages", self.regenerate_html_menu))
        pm.addAction(mk("Bulk stills…", "Import folder into gallery", self.bulk_import_gallery))
        self.btn_project_menu.setMenu(pm)
        tb.addWidget(self.btn_project_menu)

        # Tools overflow
        self.btn_tools_menu = QToolButton()
        self.btn_tools_menu.setText("Tools ▾")
        self.btn_tools_menu.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_tools_menu.setFixedHeight(28)
        self.btn_tools_menu.setToolTip("File tools & utilities")
        tm = QMenu(self.btn_tools_menu)
        tm.addAction(mk("Reload", "Reload data.js from disk", self.reload_from_disk))
        tm.addAction(mk("Repair", "Force repair data.js", self.force_repair))
        tm.addAction(mk("Backup", "Snapshot data.js", self.backup_version))
        tm.addSeparator()
        tm.addAction(mk("Export JSON…", "Export JSON", self.export_json_action))
        tm.addAction(mk("Import JSON…", "Import JSON", self.import_json_action))
        tm.addAction(mk("Zip Delivery…", "Client zip", self.export_delivery_zip))
        tm.addSeparator()
        tm.addAction(mk("New Showcase…", "Create a full new showcase folder", self.new_showcase_folder))
        self.btn_tools_menu.setMenu(tm)
        tb.addWidget(self.btn_tools_menu)

        tb.addSeparator()
        tb.addAction(mk("▶ Run", "Open final showcase in browser (F5)", self.run_showcase_html, "F5"))
        tb.addAction(mk("Page", "Open current project page (F6)", self.run_current_project_html, "F6"))
        tb.addAction(mk("Viewer", "Open Pass Breakdown viewer (F7)", self._open_breakdown_viewer, "F7"))
        tb.addAction(mk("Publish", "Save All + viewer + open project page (F8)", self.publish_project, "F8"))

        # Keep a reference for code that looked for tb_delete_btn
        self.tb_delete_btn = None

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        self.preview_toggle_btn = QPushButton("Preview")
        self.preview_toggle_btn.setObjectName("ghostBtn")
        self.preview_toggle_btn.setFixedHeight(28)
        self.preview_toggle_btn.setToolTip("Show or hide live previews")
        self.preview_toggle_btn.clicked.connect(self._toggle_preview)
        tb.addWidget(self.preview_toggle_btn)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "Slate"])
        self.theme_combo.setFixedHeight(28)
        self.theme_combo.setFixedWidth(78)
        self.theme_combo.setToolTip("Editor color theme")
        self.theme_combo.currentIndexChanged.connect(self._on_editor_theme_changed)
        tb.addWidget(self.theme_combo)

        self.density_btn = QPushButton("Compact")
        self.density_btn.setObjectName("ghostBtn")
        self.density_btn.setFixedHeight(28)
        self.density_btn.setToolTip("Toggle compact / comfortable layout")
        self.density_btn.clicked.connect(self._toggle_density)
        tb.addWidget(self.density_btn)

        self.tb_info = QLabel("01 / 01")
        self.tb_info.setObjectName("toolbarInfo")
        tb.addWidget(self.tb_info)

        self.tb_dirty = QLabel("●")
        self.tb_dirty.setObjectName("dirtyDot")
        self.tb_dirty.setToolTip("Unsaved changes")
        self.tb_dirty.setVisible(False)
        tb.addWidget(self.tb_dirty)

    def _toggle_density(self):
        self._compact_mode = not self._compact_mode
        self.density_btn.setText("Compact" if self._compact_mode else "Cozy")
        self._apply_styles()
        try:
            self._sync_rpb_theme()
        except Exception:
            pass
        self._load_project(self.current_index)

    def _toggle_preview(self):
        self._preview_enabled = not getattr(self, "_preview_enabled", True)
        if hasattr(self, "preview_toggle_btn"):
            self.preview_toggle_btn.setText(
                "Preview" if self._preview_enabled else "Preview off"
            )
        self._apply_preview_visibility()

    def _apply_preview_visibility(self):
        on = getattr(self, "_preview_enabled", True)
        for name in ("screen_preview", "thanks_preview", "project_preview"):
            w = getattr(self, name, None)
            if w is not None:
                # hide whole parent panel when possible
                parent = w.parent()
                if parent is not None and parent is not self:
                    parent.setVisible(on)
                else:
                    w.setVisible(on)
        # Screens / Thanks splitters: collapse preview pane
        for attr in ("_screens_split", "_thanks_split"):
            sp = getattr(self, attr, None)
            if sp is not None and sp.count() >= 2:
                sp.widget(1).setVisible(on)

    def _on_editor_theme_changed(self, idx):
        themes = ("dark", "light", "slate")
        self._editor_theme = themes[idx] if 0 <= idx < len(themes) else "dark"
        self._apply_styles()
        self._sync_rpb_theme()

    def _sync_rpb_theme(self):
        """Keep Pass Breakdown tab styled like the main Showcase editor."""
        rpb = getattr(self, "_rpb_editor", None)
        if rpb is None:
            return
        theme = getattr(self, "_editor_theme", "dark")
        try:
            if hasattr(rpb, "apply_host_theme"):
                rpb.apply_host_theme(theme)
            else:
                # Fallback: inherit palette via empty child stylesheet cascade
                rpb.setStyleSheet(self.styleSheet())
        except Exception:
            pass

    def new_showcase_folder(self):
        """Ask user where to create a full new showcase project."""
        target = QFileDialog.getExistingDirectory(
            self,
            "Choose folder for new showcase",
            BASE_DIR,
        )
        if not target:
            return
        # If folder not empty, offer subfolder name
        existing = [x for x in os.listdir(target) if not x.startswith(".")]
        if existing:
            name, ok = QInputDialog.getText(
                self,
                "New Showcase",
                "Folder is not empty.\nCreate a subfolder with this name:",
                text="my-showcase",
            )
            if not ok or not name.strip():
                return
            target = os.path.join(target, name.strip())
            os.makedirs(target, exist_ok=True)
        try:
            src_editor = os.path.abspath(__file__)
            dest_editor = os.path.join(target, "editor.py")
            if os.path.abspath(dest_editor) != src_editor:
                shutil.copy2(src_editor, dest_editor)
            created = scaffold_project(base=target, force=True, with_sample=True)
            msg = "Created showcase at:\n{}\n\n{} file(s).".format(
                target, len(created)
            )
            QMessageBox.information(self, "Showcase created", msg)
            self.status.showMessage("Showcase created: " + target, 5000)
        except Exception as e:
            QMessageBox.critical(self, "Showcase error", str(e))

    # ---------- Layout ----------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.main_tabs = QTabWidget()
        self.main_tabs.setDocumentMode(True)
        self.main_tabs.setMovable(False)
        outer.addWidget(self.main_tabs, 1)

        # ===== TAB: Artist =====
        artist_page = QWidget()
        artist_layout = QVBoxLayout(artist_page)
        artist_layout.setContentsMargins(28, 24, 28, 24)
        artist_layout.setSpacing(14)

        artist_layout.addWidget(self._make_header(
            "Artist profile",
            "Name and role shown on the home card, sidebar and end slide."
        ))

        artist_box = QGroupBox("IDENTITY")
        artist_form = QFormLayout(artist_box)
        artist_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        artist_form.setHorizontalSpacing(22)
        artist_form.setVerticalSpacing(12)
        artist_form.setContentsMargins(18, 22, 18, 18)

        self.artist_name_edit = QLineEdit(self.artist.get("name", ""))
        self.artist_name_edit.setPlaceholderText("e.g. KUSHAL SHARMA")
        self.artist_role_edit = QLineEdit(self.artist.get("role", ""))
        self.artist_role_edit.setPlaceholderText("e.g. LIGHTING · SHADING · COMPOSITING")
        artist_form.addRow("Name", self.artist_name_edit)
        artist_form.addRow("Role", self.artist_role_edit)

        artist_layout.addWidget(artist_box)
        artist_layout.addStretch(1)

        # ===== TAB: Dashboard (home) =====
        dash = QWidget()
        dash_l = QVBoxLayout(dash)
        dash_l.setContentsMargins(28, 24, 28, 24)
        dash_l.setSpacing(14)
        dh = QLabel("STUDIO DASHBOARD")
        dh.setObjectName("pageTitle")
        dash_l.addWidget(dh)
        ds = QLabel("Continue your showcase · check health · publish for review")
        ds.setObjectName("pageSubtitle")
        dash_l.addWidget(ds)

        # Quick actions grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        def _dash_btn(text, tip, slot, primary=False):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.setMinimumHeight(40)
            if primary:
                b.setObjectName("primaryBtn")
            b.clicked.connect(slot)
            return b

        grid.addWidget(_dash_btn("▶  Run Showcase", "Open site in browser (F5)", self.run_showcase_html, True), 0, 0)
        grid.addWidget(_dash_btn("Publish project", "Save + viewer + open page (F8)", self.publish_project, True), 0, 1)
        grid.addWidget(_dash_btn("Open project page", "Current project HTML (F6)", self.run_current_project_html), 0, 2)
        grid.addWidget(_dash_btn("Asset Health", "Find missing images (F9)", self.asset_health_panel), 1, 0)
        grid.addWidget(_dash_btn("Pass Breakdown", "Go to breakdown tab", lambda: self.main_tabs.setCurrentIndex(self._tab_index("Pass Breakdown"))), 1, 1)
        grid.addWidget(_dash_btn("Presenter checklist", "Pre-show safety checks", self.presenter_checklist), 1, 2)
        grid.addWidget(_dash_btn("Snapshot version", "Backup data before client send", self.snapshot_version), 2, 0)
        grid.addWidget(_dash_btn("Project template…", "Interior / Car / Character starter", self.apply_project_template), 2, 1)
        grid.addWidget(_dash_btn("Self-check", "Python packages + folder writable", self.startup_self_check), 2, 2)
        grid.addWidget(_dash_btn("Relink assets", "Find & fix missing images in asset folders", self.relink_missing_assets), 3, 0)
        grid.addWidget(_dash_btn("Undock preview", "Preview window for second monitor", self.undock_preview_window), 3, 1)
        dash_l.addLayout(grid)

        self.dash_status = QLabel("")
        self.dash_status.setObjectName("pageSubtitle")
        self.dash_status.setWordWrap(True)
        dash_l.addWidget(self.dash_status)
        self.dash_recent = QLabel("")
        self.dash_recent.setWordWrap(True)
        dash_l.addWidget(self.dash_recent)
        dash_l.addStretch(1)
        self.main_tabs.addTab(dash, "  Home  ")

        self.main_tabs.addTab(artist_page, "  Artist  ")


        # ===== TAB: Thanks + live preview =====
        thanks = getattr(self, "thanks", None) or {}
        thanks_page = QWidget()
        thanks_split = QSplitter(Qt.Orientation.Horizontal)
        thanks_split.setChildrenCollapsible(False)
        self._thanks_split = thanks_split

        thanks_scroll = QScrollArea()
        thanks_scroll.setWidgetResizable(True)
        thanks_scroll.setFrameShape(QFrame.Shape.NoFrame)
        thanks_inner = QWidget()
        thanks_layout = QVBoxLayout(thanks_inner)
        thanks_layout.setContentsMargins(20, 18, 16, 18)
        thanks_layout.setSpacing(14)

        thanks_layout.addWidget(self._make_header(
            "Thanks screen",
            "Optional slide after Home. Live preview on the right."
        ))

        thanks_box = QGroupBox("SLIDE CONTENT")
        thanks_form = QFormLayout(thanks_box)
        thanks_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        thanks_form.setHorizontalSpacing(18)
        thanks_form.setVerticalSpacing(10)
        thanks_form.setContentsMargins(14, 16, 14, 12)

        self.thanks_enabled = QCheckBox("Show thanks slide after home")
        self.thanks_enabled.setChecked(bool(thanks.get("enabled", False)))
        thanks_form.addRow("Visibility", self.thanks_enabled)

        self.thanks_eyebrow = QLineEdit(str(thanks.get("eyebrow", "WITH GRATITUDE")))
        self.thanks_heading = QLineEdit(str(thanks.get("heading", "THANK YOU")))
        self.thanks_sub = QLineEdit(str(thanks.get("sub", "")))
        self.thanks_note = QLineEdit(str(thanks.get("note", "")))
        thanks_form.addRow("Eyebrow", self.thanks_eyebrow)
        thanks_form.addRow("Heading", self.thanks_heading)
        thanks_form.addRow("Sub", self.thanks_sub)
        thanks_form.addRow("Note", self.thanks_note)

        self.thanks_depts = QTextEdit()
        self.thanks_depts.setMinimumHeight(140)
        self.thanks_depts.setPlaceholderText(
            "One department per line: NAME | speech text\n"
            "e.g. MODELLING | Thank you to the Modelling team…"
        )
        dept_lines = []
        for d in thanks.get("departments") or []:
            if isinstance(d, dict):
                dept_lines.append(f"{d.get('name', '')} | {d.get('text', '')}")
            else:
                dept_lines.append(str(d))
        self.thanks_depts.setPlainText("\n".join(dept_lines))
        thanks_form.addRow("Departments", self.thanks_depts)

        thanks_layout.addWidget(thanks_box)
        thanks_layout.addStretch(1)
        thanks_scroll.setWidget(thanks_inner)
        thanks_split.addWidget(thanks_scroll)

        thanks_prev_panel = QWidget()
        tp_lay = QVBoxLayout(thanks_prev_panel)
        tp_lay.setContentsMargins(12, 18, 16, 16)
        tp_lay.setSpacing(10)
        tp_lbl = QLabel("LIVE PREVIEW · THANKS")
        tp_lbl.setObjectName("previewHeader")
        tp_lay.addWidget(tp_lbl)
        self.thanks_preview = ScreenPreviewWidget()
        self.thanks_preview.set_mode("thanks")
        tp_lay.addWidget(self.thanks_preview, 1)
        tp_hint = QLabel("Updates as you type · does not require Save")
        tp_hint.setStyleSheet("color:#888; font-size:11px;")
        tp_lay.addWidget(tp_hint)
        thanks_split.addWidget(thanks_prev_panel)
        thanks_split.setStretchFactor(0, 5)
        thanks_split.setStretchFactor(1, 6)
        thanks_split.setSizes([400, 480])

        thanks_outer = QVBoxLayout(thanks_page)
        thanks_outer.setContentsMargins(0, 0, 0, 0)
        thanks_outer.addWidget(thanks_split)
        self.main_tabs.addTab(thanks_page, "  Thanks  ")

        def _kick_thanks():
            if hasattr(self, "_thanks_preview_timer"):
                self._thanks_preview_timer.start()
            self._mark_dirty()

        self._thanks_preview_timer = QTimer(self)
        self._thanks_preview_timer.setSingleShot(True)
        self._thanks_preview_timer.setInterval(80)
        self._thanks_preview_timer.timeout.connect(self._refresh_thanks_preview)

        self.thanks_enabled.stateChanged.connect(_kick_thanks)
        for w in (self.thanks_eyebrow, self.thanks_heading, self.thanks_sub, self.thanks_note):
            w.textChanged.connect(_kick_thanks)
        self.thanks_depts.textChanged.connect(_kick_thanks)
        QTimer.singleShot(0, self._refresh_thanks_preview)

        # ===== TAB: Screens (Home + End + Font + Header) + live preview =====
        home = getattr(self, "home", None) or {}
        end = getattr(self, "end", None) or {}
        font = getattr(self, "font", None) or {}
        header = getattr(self, "header", None) or {}

        screens_page = QWidget()
        screens_split = QSplitter(Qt.Orientation.Horizontal)
        screens_split.setChildrenCollapsible(False)
        self._screens_split = screens_split

        # --- Left: form ---
        screens_scroll = QScrollArea()
        screens_scroll.setWidgetResizable(True)
        screens_scroll.setFrameShape(QFrame.Shape.NoFrame)
        screens_inner = QWidget()
        screens_layout = QVBoxLayout(screens_inner)
        screens_layout.setContentsMargins(20, 18, 16, 18)
        screens_layout.setSpacing(14)

        screens_layout.addWidget(self._make_header(
            "Screens & branding",
            "Edit header, home, end, and font. Live preview updates on the right."
        ))

        hdr_box = QGroupBox("HEADER")
        hdr_form = QFormLayout(hdr_box)
        hdr_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        hdr_form.setHorizontalSpacing(18)
        hdr_form.setVerticalSpacing(8)
        hdr_form.setContentsMargins(14, 16, 14, 12)
        self.header_brand = QLineEdit(str(header.get("brand", "ARTIST SHOWCASE · 2026")))
        self.header_brand.setPlaceholderText("ARTIST SHOWCASE · 2026")
        hdr_form.addRow("Brand text", self.header_brand)
        screens_layout.addWidget(hdr_box)

        home_box = QGroupBox("HOME SCREEN")
        home_form = QFormLayout(home_box)
        home_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        home_form.setHorizontalSpacing(18)
        home_form.setVerticalSpacing(8)
        home_form.setContentsMargins(14, 16, 14, 12)
        self.home_eyebrow = QLineEdit(str(home.get("eyebrow", "")))
        self.home_heading = QTextEdit()
        self.home_heading.setFixedHeight(64)
        self.home_heading.setPlainText(str(home.get("heading", "")).replace("\\n", "\n"))
        self.home_heading.setPlaceholderText("Multi-line title allowed")
        self.home_media_type = QComboBox()
        self.home_media_type.addItems(["(none)", "image", "video"])
        mt = (home.get("mediaType") or "").lower()
        self.home_media_type.setCurrentIndex(
            1 if mt == "image" else (2 if mt == "video" else 0)
        )
        self.home_media = QLineEdit(str(home.get("media", "")))
        self.home_media.setPlaceholderText("assets/images/... or assets/videos/...")
        home_media_row = QWidget()
        home_media_h = QHBoxLayout(home_media_row)
        home_media_h.setContentsMargins(0, 0, 0, 0)
        home_media_h.setSpacing(8)
        home_media_h.addWidget(self.home_media, 1)
        home_browse = QPushButton("Browse…")
        home_browse.setFixedWidth(96)
        home_browse.clicked.connect(lambda: self._browse_screen_media("home"))
        home_media_h.addWidget(home_browse)
        home_form.addRow("Eyebrow", self.home_eyebrow)
        home_form.addRow("Heading", self.home_heading)
        home_form.addRow("Media type", self.home_media_type)
        home_form.addRow("Media", home_media_row)
        screens_layout.addWidget(home_box)

        end_box = QGroupBox("END SCREEN")
        end_form = QFormLayout(end_box)
        end_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        end_form.setHorizontalSpacing(18)
        end_form.setVerticalSpacing(8)
        end_form.setContentsMargins(14, 16, 14, 12)
        self.end_eyebrow = QLineEdit(str(end.get("eyebrow", "")))
        self.end_heading = QLineEdit(str(end.get("heading", "")))
        self.end_note = QLineEdit(str(end.get("note", "")))
        self.end_media_type = QComboBox()
        self.end_media_type.addItems(["(none)", "image", "video"])
        emt = (end.get("mediaType") or "").lower()
        self.end_media_type.setCurrentIndex(
            1 if emt == "image" else (2 if emt == "video" else 0)
        )
        self.end_media = QLineEdit(str(end.get("media", "")))
        self.end_media.setPlaceholderText("assets/images/... or assets/videos/...")
        end_media_row = QWidget()
        end_media_h = QHBoxLayout(end_media_row)
        end_media_h.setContentsMargins(0, 0, 0, 0)
        end_media_h.setSpacing(8)
        end_media_h.addWidget(self.end_media, 1)
        end_browse = QPushButton("Browse…")
        end_browse.setFixedWidth(96)
        end_browse.clicked.connect(lambda: self._browse_screen_media("end"))
        end_media_h.addWidget(end_browse)
        end_form.addRow("Eyebrow", self.end_eyebrow)
        end_form.addRow("Heading", self.end_heading)
        end_form.addRow("Note", self.end_note)
        end_form.addRow("Media type", self.end_media_type)
        end_form.addRow("Media", end_media_row)
        screens_layout.addWidget(end_box)

        font_box = QGroupBox("FONT")
        font_form = QFormLayout(font_box)
        font_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        font_form.setHorizontalSpacing(18)
        font_form.setVerticalSpacing(8)
        font_form.setContentsMargins(14, 16, 14, 12)
        self.font_family = QLineEdit(str(font.get("family", "Segoe UI, Arial, Helvetica, sans-serif")))
        self.font_family.setPlaceholderText("Segoe UI, Arial, Helvetica, sans-serif")
        self.font_url = QLineEdit(str(font.get("url", "")))
        self.font_url.setPlaceholderText("https://fonts.googleapis.com/css2?family=...")
        font_form.addRow("Family", self.font_family)
        font_form.addRow("Stylesheet URL", self.font_url)
        screens_layout.addWidget(font_box)

        screens_layout.addStretch(1)
        screens_scroll.setWidget(screens_inner)
        screens_split.addWidget(screens_scroll)

        # --- Right: live preview ---
        preview_panel = QWidget()
        preview_panel.setObjectName("screenPreviewPanel")
        prev_lay = QVBoxLayout(preview_panel)
        prev_lay.setContentsMargins(12, 18, 16, 16)
        prev_lay.setSpacing(10)

        prev_top = QHBoxLayout()
        prev_lbl = QLabel("LIVE PREVIEW")
        prev_lbl.setObjectName("previewHeader")
        prev_top.addWidget(prev_lbl)
        prev_top.addStretch(1)
        self.preview_mode_combo = QComboBox()
        self.preview_mode_combo.addItems(["Home", "End"])
        self.preview_mode_combo.setFixedWidth(100)
        self.preview_mode_combo.currentIndexChanged.connect(self._on_preview_mode_changed)
        prev_top.addWidget(self.preview_mode_combo)
        prev_lay.addLayout(prev_top)

        self.screen_preview = ScreenPreviewWidget()
        self.screen_preview.setObjectName("screenPreview")
        prev_lay.addWidget(self.screen_preview, 1)

        prev_hint = QLabel("Updates as you type · does not require Save")
        prev_hint.setStyleSheet("color:#888; font-size:11px;")
        prev_lay.addWidget(prev_hint)

        screens_split.addWidget(preview_panel)
        screens_split.setStretchFactor(0, 5)
        screens_split.setStretchFactor(1, 6)
        screens_split.setSizes([420, 520])

        screens_outer = QVBoxLayout(screens_page)
        screens_outer.setContentsMargins(0, 0, 0, 0)
        screens_outer.addWidget(screens_split)
        self.main_tabs.addTab(screens_page, "  Screens  ")

        # Live preview wiring
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(80)
        self._preview_timer.timeout.connect(self._refresh_screen_preview)

        def _kick():
            self._preview_timer.start()
            self._mark_dirty()

        for w in (
            self.header_brand, self.home_eyebrow, self.home_media,
            self.end_eyebrow, self.end_heading, self.end_note, self.end_media,
            self.font_family, self.font_url,
        ):
            w.textChanged.connect(_kick)
        self.home_heading.textChanged.connect(_kick)
        self.home_media_type.currentIndexChanged.connect(_kick)
        self.end_media_type.currentIndexChanged.connect(_kick)
        if hasattr(self, "artist_name_edit"):
            self.artist_name_edit.textChanged.connect(_kick)
            self.artist_role_edit.textChanged.connect(_kick)

        QTimer.singleShot(0, self._refresh_screen_preview)

        # ===== TAB: Projects =====
        projects_page = QWidget()
        projects_layout = QVBoxLayout(projects_page)
        projects_layout.setContentsMargins(10, 10, 10, 10)
        projects_layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)

        # ----- Left: project browser -----
        left = QFrame()
        left.setObjectName("projectBrowser")
        left.setMinimumWidth(220)
        left.setMaximumWidth(360)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_lbl = QLabel("PROJECTS")
        title_lbl.setObjectName("panelTitle")
        self.project_count_label = QLabel("0")
        self.project_count_label.setObjectName("countBadge")
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        title_row.addWidget(self.project_count_label)
        left_layout.addLayout(title_row)

        self.project_search = QLineEdit()
        self.project_search.setPlaceholderText("Search…")
        self.project_search.setClearButtonEnabled(True)
        self.project_search.setObjectName("searchField")
        self.project_search.textChanged.connect(self._filter_project_list)
        left_layout.addWidget(self.project_search)

        self.project_list = QListWidget()
        self.project_list.setObjectName("projectList")
        self.project_list.setSpacing(3)
        self.project_list.setUniformItemSizes(False)
        self.project_list.currentRowChanged.connect(self.on_project_selected)
        left_layout.addWidget(self.project_list, 1)

        browser_buttons = QHBoxLayout()
        browser_buttons.setSpacing(6)
        self.new_project_btn = QPushButton("＋ New")
        self.new_project_btn.setObjectName("accentBtn")
        self.duplicate_project_btn = QPushButton("⧉ Duplicate")
        self.delete_project_btn = QPushButton("Delete")
        self.delete_project_btn.setObjectName("dangerBtn")
        self.delete_project_btn.setFixedHeight(30)
        self.delete_project_btn.setMinimumWidth(72)
        self.delete_project_btn.setToolTip("Delete selected project")
        self.new_project_btn.clicked.connect(self.add_project)
        self.duplicate_project_btn.clicked.connect(self.duplicate_project)
        self.delete_project_btn.clicked.connect(self.delete_project)
        browser_buttons.addWidget(self.new_project_btn, 1)
        browser_buttons.addWidget(self.duplicate_project_btn, 1)
        browser_buttons.addWidget(self.delete_project_btn)
        left_layout.addLayout(browser_buttons)

        splitter.addWidget(left)

        # ----- Right: editor -----
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Project header card
        self.project_header = QFrame()
        self.project_header.setObjectName("projectHeader")
        header_layout = QHBoxLayout(self.project_header)
        header_layout.setContentsMargins(18, 14, 18, 14)
        header_layout.setSpacing(12)

        header_left = QVBoxLayout()
        header_left.setSpacing(3)
        self.project_header_title = QLabel("Project")
        self.project_header_title.setObjectName("projectHeaderTitle")
        self.project_header_meta = QLabel("")
        self.project_header_meta.setObjectName("projectHeaderMeta")
        header_left.addWidget(self.project_header_title)
        header_left.addWidget(self.project_header_meta)
        header_layout.addLayout(header_left, 1)

        self.project_header_status = QLabel("SAVED")
        self.project_header_status.setObjectName("statusBadge")
        self.project_header_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.project_header_status.setMinimumSize(88, 30)
        self.project_header_status.setToolTip("Saved — no unsaved changes")
        header_layout.addWidget(self.project_header_status, 0, Qt.AlignmentFlag.AlignTop)

        right_layout.addWidget(self.project_header)

        # Quick action strip
        quick = QFrame()
        quick.setObjectName("quickStrip")
        quick_layout = QHBoxLayout(quick)
        quick_layout.setContentsMargins(10, 6, 10, 6)
        quick_layout.setSpacing(6)

        def quick_btn(text, slot, obj=None, tip=None):
            b = QPushButton(text)
            if obj:
                b.setObjectName(obj)
            if tip:
                b.setToolTip(tip)
            b.clicked.connect(slot)
            return b

        quick_layout.addWidget(quick_btn("‹  Previous", self._goto_prev_project,
                                         "ghostBtn", "Alt+↑"))
        quick_layout.addWidget(quick_btn("Next  ›", self._goto_next_project,
                                         "ghostBtn", "Alt+↓"))
        quick_layout.addSpacing(8)
        quick_layout.addWidget(quick_btn("✓  Validate", self.validate_assets,
                                         "ghostBtn"))
        quick_layout.addWidget(quick_btn("📄  Regen HTML", self.regenerate_html_menu,
                                         "ghostBtn"))
        quick_layout.addStretch(1)
        quick_layout.addWidget(quick_btn("💾  Save Project", self.save_current_project,
                                         "primaryBtn", "Ctrl+S"))
        right_layout.addWidget(quick)

        # Scrollable form area
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setObjectName("formScroll")
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.form_host = QWidget()
        self.form_host.setObjectName("formHost")
        self.form_layout = QVBoxLayout(self.form_host)
        self.form_layout.setContentsMargins(14, 14, 14, 22)
        self.form_layout.setSpacing(6)

        right_scroll.setWidget(self.form_host)
        # Live project preview (above form)
        prev_box = QFrame()
        prev_box.setObjectName("projectPreviewBox")
        prev_box_lay = QVBoxLayout(prev_box)
        prev_box_lay.setContentsMargins(8, 8, 8, 8)
        prev_box_lay.setSpacing(4)
        prev_hdr = QLabel("LIVE PREVIEW · PROJECT")
        prev_hdr.setObjectName("previewHeader")
        prev_box_lay.addWidget(prev_hdr)
        self.project_preview = ScreenPreviewWidget()
        self.project_preview.set_mode("project")
        self.project_preview.setMinimumHeight(160)
        self.project_preview.setMaximumHeight(220)
        prev_box_lay.addWidget(self.project_preview)
        right_layout.addWidget(prev_box)

        right_layout.addWidget(right_scroll, 1)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 980])

        projects_layout.addWidget(splitter, 1)

        self.main_tabs.addTab(projects_page, "  Projects  ")

        # ===== TAB: Pass Breakdown (merged studio) =====
        rpb_page = QWidget()
        rpb_layout = QVBoxLayout(rpb_page)
        rpb_layout.setContentsMargins(0, 0, 0, 0)
        rpb_layout.setSpacing(0)
        self._rpb_editor = None
        try:
            import importlib.util
            import sys as _sys
            import webbrowser
            from pathlib import Path as _Path

            studio_root = _Path(BASE_DIR).resolve().parent
            ed_path = studio_root / "editor" / "editor.py"
            if not ed_path.is_file():
                ed_path = _Path(BASE_DIR) / "editor" / "editor.py"
            if not ed_path.is_file():
                raise FileNotFoundError(
                    "Pass Breakdown editor not found.\n"
                    f"Looked for:\n  {studio_root / 'editor' / 'editor.py'}"
                )

            if str(studio_root) not in _sys.path:
                _sys.path.insert(0, str(studio_root))

            spec = importlib.util.spec_from_file_location("rpb_editor", str(ed_path))
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load {ed_path}")
            mod = importlib.util.module_from_spec(spec)
            _sys.modules["rpb_editor"] = mod
            spec.loader.exec_module(mod)
            Editor = mod.Editor

            # Embed the full QMainWindow as a child widget (keeps all UI visible)
            self._rpb_editor = Editor()
            self._rpb_editor.setParent(rpb_page)
            try:
                self._rpb_editor.setWindowFlags(Qt.WindowType.Widget)
            except Exception:
                try:
                    self._rpb_editor.setWindowFlags(Qt.Widget)  # type: ignore
                except Exception:
                    pass
            self._rpb_editor.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )

            # Top bar: project sync + viewer (matches this editor chrome)
            top = QWidget()
            top_l = QHBoxLayout(top)
            top_l.setContentsMargins(12, 6, 12, 6)
            tip = QLabel("Pass Breakdown  ·  sync with current Showcase project  ·  per-project viewer")
            tip.setObjectName("pageSubtitle")
            top_l.addWidget(tip, 1)

            b_from = QPushButton("Project → Breakdown")
            b_from.setToolTip("Load current Showcase project passes into Pass Breakdown")
            b_from.clicked.connect(self._sync_project_to_breakdown)
            b_to = QPushButton("Breakdown → Project")
            b_to.setToolTip("Write Pass Breakdown stack into current Showcase project passes")
            b_to.clicked.connect(self._sync_breakdown_to_project)
            b_save_proj = QPushButton("Save project viewer")
            b_save_proj.setToolTip("Write per-project viewer/projects/<id>/data.js and open it")
            b_save_proj.clicked.connect(self._save_project_viewer)
            b_view = QPushButton("Open Viewer")
            b_view.setToolTip("Open global or project-scoped animated viewer")
            b_view.clicked.connect(self._open_breakdown_viewer)

            for b in (b_from, b_to, b_save_proj, b_view):
                top_l.addWidget(b)
            rpb_layout.addWidget(top)
            rpb_layout.addWidget(self._rpb_editor, 1)
            self._rpb_editor.show()
            self._studio_root = studio_root
            # When user hits Save in Breakdown, push passes back to Showcase project
            self._rpb_editor._on_saved_callback = (
                lambda: self._auto_sync_breakdown_to_project(quiet=True)
            )
            try:
                self._sync_rpb_theme()
            except Exception:
                pass
        except Exception as e:
            import traceback
            err = QLabel(
                "Pass Breakdown editor could not load.\n\n"
                f"{e}\n\n{traceback.format_exc()}"
            )
            err.setWordWrap(True)
            err.setObjectName("pageSubtitle")
            err.setContentsMargins(24, 24, 24, 24)
            err.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            rpb_layout.addWidget(err)

        self.main_tabs.addTab(rpb_page, "  Pass Breakdown  ")

        self._sync_lock = False
        self._breakdown_for_index = -1
        self._last_tab_index = 3
        self.main_tabs.currentChanged.connect(self._on_main_tab_changed)
        self.main_tabs.setCurrentIndex(0)  # Home dashboard
        # Initial load of current project into breakdown (quiet)
        try:
            self._auto_sync_project_to_breakdown(quiet=True)
        except Exception:
            pass
        try:
            self._restore_session()
        except Exception:
            pass

    # ---------- Header helper ----------
    def _make_header(self, title, subtitle):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        t = QLabel(title)
        t.setObjectName("pageTitle")
        s = QLabel(subtitle)
        s.setObjectName("pageSubtitle")
        v.addWidget(t)
        v.addWidget(s)
        return w

    def _build_status_bar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")
        self.status.setSizeGripEnabled(True)

    # ---------- Keyboard shortcuts ----------
    def _install_shortcuts(self):
        from PySide6.QtGui import QShortcut

        QShortcut(QKeySequence("Alt+Up"), self, activated=self._goto_prev_project)
        QShortcut(QKeySequence("Alt+Down"), self, activated=self._goto_next_project)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: self.project_search.setFocus())
        QShortcut(QKeySequence("Ctrl+1"), self, activated=lambda: self.main_tabs.setCurrentIndex(1))
        QShortcut(QKeySequence("Ctrl+2"), self, activated=lambda: self.main_tabs.setCurrentIndex(2))
        QShortcut(QKeySequence("Ctrl+3"), self, activated=lambda: self.main_tabs.setCurrentIndex(3))
        QShortcut(QKeySequence("Ctrl+4"), self, activated=lambda: self.main_tabs.setCurrentIndex(4))
        QShortcut(QKeySequence("Ctrl+5"), self, activated=lambda: self.main_tabs.setCurrentIndex(5))
        QShortcut(QKeySequence("Ctrl+0"), self, activated=lambda: self.main_tabs.setCurrentIndex(0))

    # ---------- Style ----------

    def _apply_styles(self):
        pad = 8 if self._compact_mode else 12
        row_pad = 6 if self._compact_mode else 10
        theme = getattr(self, "_editor_theme", "dark")

        # Full palettes — every UI chrome uses these tokens (no leftover hard-coded dark-only colors)
        themes = {
            "dark": dict(
                bg="#0f1115", bg2="#14171d", bg3="#1c2129", bg4="#232932",
                text="#e7eaf0", text2="#c7ccd6", muted="#9aa3b2",
                accent="#c9a962", accent2="#d4af37",
                border="#2a3140", border2="#242932",
                danger="#c45c5c", danger_h="#d97070",
                inp="#181c24", inp_border="#2a3140",
                sel="#1c212a", sel_text="#ffffff",
                hover="#1e232b",
                badge_bg="#1d222a", badge_fg="#f4c95d",
                ok_bg="#1b2a1f", ok_fg="#b7e6a9", ok_bd="#426247",
                dirty_bg="#302615", dirty_fg="#f4c95d", dirty_bd="#8f7024",
                scroll="#2a3140",
            ),
            "light": dict(
                # Soft dashboard light (reference-style contrast)
                bg="#f0f2f5", bg2="#ffffff", bg3="#e8ebf0", bg4="#f5f6f8",
                text="#1a1d26", text2="#2c3142", muted="#5c6578",
                accent="#5b4fd6", accent2="#4a3fc4",
                border="#d8dce5", border2="#cfd4e0",
                danger="#d64545", danger_h="#e05555",
                inp="#ffffff", inp_border="#c8cede",
                sel="#e4e7f5", sel_text="#12141c",
                hover="#eceef6",
                badge_bg="#eef0f8", badge_fg="#5b4fd6",
                ok_bg="#e8f6ec", ok_fg="#1f7a3f", ok_bd="#b7e0c2",
                dirty_bg="#fff6e5", dirty_fg="#a67c00", dirty_bd="#f0d78c",
                scroll="#c5cad6",
            ),
            "slate": dict(
                bg="#1a2332", bg2="#243044", bg3="#2c3a52", bg4="#33415a",
                text="#e8eef7", text2="#c5d0e0", muted="#9aadc2",
                accent="#6eb5ff", accent2="#5aa8f5",
                border="#3a4a62", border2="#33415a",
                danger="#e07070", danger_h="#f08080",
                inp="#1e2a3c", inp_border="#3a4a62",
                sel="#2c3a52", sel_text="#ffffff",
                hover="#2a3850",
                badge_bg="#2c3a52", badge_fg="#6eb5ff",
                ok_bg="#1e3a2c", ok_fg="#8fd4a4", ok_bd="#3d6b4f",
                dirty_bg="#3a3420", dirty_fg="#f0d78c", dirty_bd="#6b5a28",
                scroll="#3a4a62",
            ),
        }
        T = themes.get(theme, themes["dark"])
        # Expand for f-string
        bg, bg2, bg3, bg4 = T["bg"], T["bg2"], T["bg3"], T["bg4"]
        text_c, text2, muted = T["text"], T["text2"], T["muted"]
        accent, accent2 = T["accent"], T["accent2"]
        border, border2 = T["border"], T["border2"]
        danger, danger_h = T["danger"], T["danger_h"]
        inp, inp_border = T["inp"], T["inp_border"]
        sel, sel_text, hover = T["sel"], T["sel_text"], T["hover"]
        badge_bg, badge_fg = T["badge_bg"], T["badge_fg"]
        ok_bg, ok_fg, ok_bd = T["ok_bg"], T["ok_fg"], T["ok_bd"]
        dirty_bg, dirty_fg, dirty_bd = T["dirty_bg"], T["dirty_fg"], T["dirty_bd"]
        scroll = T["scroll"]

        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background: {bg};
                color: {text_c};
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 13px;
            }}
            QToolTip {{
                background: {bg3};
                color: {text_c};
                border: 1px solid {border};
                padding: 5px 8px;
            }}

            /* ---------- Toolbar ---------- */
            QToolBar {{
                background: {bg2};
                border: none;
                border-bottom: 1px solid {border};
                padding: 5px 8px;
                spacing: 2px;
            }}
            QToolBar::separator {{
                background: {border};
                width: 1px;
                margin: 4px 6px;
            }}
            QToolBar QToolButton {{
                background: transparent;
                color: {text2};
                padding: 6px 9px;
                border-radius: 6px;
                font-weight: 650;
                border: 1px solid transparent;
            }}
            QToolBar QToolButton:hover {{
                background: {hover};
                color: {text_c};
            }}
            QToolBar QToolButton:pressed {{
                background: {bg3};
            }}


            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QTextEdit {{
                background: {bg3};
                color: {text_c};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 22px;
            }}
            QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QLineEdit:hover {{
                border-color: {accent};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 22px;
                background: {bg2};
                border-left: 1px solid {border};
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 0; height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {accent};
                margin-right: 6px;
            }}
            QComboBox QAbstractItemView {{
                background: {bg3};
                color: {text_c};
                border: 1px solid {border};
                selection-background-color: {accent};
                selection-color: #ffffff;
            }}
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                background: {bg2};
                border: none;
                width: 18px;
            }}

            QPushButton#ghostBtn {{
                background: {bg2};
                color: {text2};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: 600;
            }}
            QPushButton#ghostBtn:hover {{
                background: {hover};
                color: {text_c};
                border-color: {accent};
            }}
            QPushButton#dangerBtn {{
                background: transparent;
                color: {danger};
                border: 1px solid {danger};
                border-radius: 6px;
                padding: 4px 12px;
                font-weight: 600;
            }}
            QPushButton#dangerBtn:hover {{
                background: {danger};
                color: #ffffff;
                border-color: {danger_h};
            }}
            QPushButton#accentBtn, QPushButton#primaryBtn {{
                background: {accent};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 700;
            }}
            QPushButton#accentBtn:hover, QPushButton#primaryBtn:hover {{
                background: {accent2};
            }}
            QPushButton {{
                background: {bg3};
                color: {text_c};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background: {hover};
                border-color: {accent};
            }}

            QLabel#toolbarInfo {{
                color: {muted};
                padding: 0 8px;
                font-weight: 600;
            }}
            QLabel#dirtyDot {{
                color: {accent};
                font-size: 14px;
                padding: 0 6px;
            }}
            QLabel#previewHeader {{
                font-weight: 700;
                letter-spacing: 1px;
                color: {accent};
                font-size: 11px;
            }}
            QFrame#projectPreviewBox {{
                background: {bg2};
                border: 1px solid {border};
                border-radius: 8px;
            }}

            /* ---------- Tabs ---------- */
            QTabWidget::pane {{
                border: none;
                background: {bg};
            }}
            QTabBar::tab {{
                background: {bg2};
                color: {muted};
                padding: 10px 18px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border: 1px solid {border};
                border-bottom: none;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: {bg};
                color: {text_c};
                border-bottom: 2px solid {accent};
            }}
            QTabBar::tab:hover:!selected {{
                color: {text_c};
                background: {hover};
            }}

            /* ---------- Inputs ---------- */
            QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{
                background: {inp};
                color: {text_c};
                border: 1px solid {inp_border};
                border-radius: 8px;
                padding: 7px 10px;
                selection-background-color: {accent};
                selection-color: #ffffff;
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 1px solid {accent};
            }}
            QLineEdit:disabled, QTextEdit:disabled {{
                color: {muted};
                background: {bg3};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background: {bg2};
                color: {text_c};
                border: 1px solid {border};
                selection-background-color: {sel};
                selection-color: {sel_text};
            }}
            QCheckBox {{
                color: {text_c};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid {inp_border};
                background: {inp};
            }}
            QCheckBox::indicator:checked {{
                background: {accent};
                border-color: {accent};
            }}

            /* ---------- Group boxes ---------- */
            QGroupBox {{
                background: {bg2};
                border: 1px solid {border};
                border-radius: 10px;
                margin-top: 18px;
                padding: 12px 12px 14px 12px;
                font-weight: 700;
                color: {text_c};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 14px;
                padding: 2px 10px;
                color: {accent};
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 1.6px;
                background: {bg2};
            }}
            /* Form labels — plain text, no color boxes */
            QLabel#formLabel, QFormLayout > QLabel, QGroupBox QLabel {{
                background: transparent;
                border: none;
                padding: 0;
                color: {muted};
                font-weight: 600;
                font-size: 12px;
            }}
            QWidget#formRow {{
                background: transparent;
            }}

            /* ---------- Lists / project browser ---------- */
            QFrame#projectBrowser {{
                background: {bg2};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QListWidget#projectList {{
                background: transparent;
                border: none;
                padding: 4px;
                outline: none;
            }}
            QListWidget#projectList::item {{
                padding: {row_pad}px 12px;
                margin: 2px 4px;
                border-radius: 8px;
                color: {text_c};
                background: transparent;
                border: 1px solid transparent;
            }}
            QListWidget#projectList::item:hover {{
                background: {hover};
                color: {text_c};
            }}
            QListWidget#projectList::item:selected {{
                background: {sel};
                color: {sel_text};
                border: 1px solid {accent};
                font-weight: 700;
            }}
            QListWidget#projectList::item:selected:hover {{
                background: {sel};
                color: {sel_text};
            }}
            QLabel#panelTitle {{
                color: {muted};
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 1.5px;
            }}
            QLabel#countBadge {{
                background: {badge_bg};
                color: {badge_fg};
                border: 1px solid {border};
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 800;
            }}
            QLabel#statusBadge {{
                background: {ok_bg};
                color: {ok_fg};
                border: 1px solid {ok_bd};
                border-radius: 10px;
                padding: 5px 14px;
                min-width: 88px;
                min-height: 30px;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 1px;
            }}
            QLabel#statusBadge[dirty="true"] {{
                background: {dirty_bg};
                color: {dirty_fg};
                border-color: {dirty_bd};
            }}

            /* ---------- Project header ---------- */
            QFrame#projectHeader {{
                background: {bg2};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QLabel#projectHeaderTitle {{
                color: {text_c};
                font-size: 17px;
                font-weight: 800;
            }}
            QLabel#projectHeaderMeta {{
                color: {muted};
                font-size: 11px;
            }}
            QFrame#quickStrip {{
                background: {bg2};
                border: 1px solid {border};
                border-radius: 10px;
            }}

            /* ---------- Form / scroll ---------- */
            QScrollArea#formScroll, QWidget#formHost {{
                background: {bg};
                border: none;
            }}
            QScrollBar:vertical {{
                background: {bg};
                width: 10px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QLabel#pageTitle {{
                color: {text_c};
                font-size: 18px;
                font-weight: 800;
            }}
            QLabel#pageSubtitle {{
                color: {muted};
                font-size: 12px;
            }}
            QFrame#sectionDivider {{
                background: transparent;
            }}
            QLabel#sectionTitle, QLabel#dividerLabel {{
                color: {accent};
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 1.6px;
                background: transparent;
                border: none;
                padding: 0 4px;
            }}
            QFrame#dividerLine {{
                background: {border};
                border: none;
                max-height: 1px;
            }}
            QLabel#sectionHint {{
                color: {muted};
                font-size: 11px;
            }}
            QStatusBar {{
                background: {bg2};
                color: {muted};
                border-top: 1px solid {border};
            }}
            QSplitter::handle {{
                background: {border};
            }}
            QSplitter::handle:hover {{
                background: {accent};
            }}
            QPushButton#fmtBtn {{
                background: {bg3};
                color: {text_c};
                border: 1px solid {border};
                border-radius: 6px;
                font-weight: 700;
            }}
            QPushButton#fmtBtn:hover {{
                border-color: {accent};
                color: {accent};
            }}
            QComboBox {{
                min-height: 26px;
                padding: 2px 22px 2px 8px;
            }}
            QLineEdit#searchField {{
                background: {inp};
                color: {text_c};
                border: 1px solid {inp_border};
                border-radius: 8px;
                padding: 8px 12px;
            }}
        """)


    def _load_project_list(self):
        self.project_list.blockSignals(True)
        self.project_list.clear()
        for i, p in enumerate(self.projects):
            title = p.get("title", "(untitled)") or "(untitled)"
            category = (p.get("category", "") or "").strip()
            text = f"{i + 1:02d}   {title}"
            if category:
                text += f"\n      {category}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            item.setToolTip(f"{title}\n{category}\n{p.get('file', '')}")
            self.project_list.addItem(item)
        self.project_list.blockSignals(False)
        if hasattr(self, "project_count_label"):
            self.project_count_label.setText(str(len(self.projects)))
        self._filter_project_list(
            self.project_search.text() if hasattr(self, "project_search") else ""
        )
        self._update_action_bar()

    def _filter_project_list(self, query=""):
        query = (query or "").strip().lower()
        if not hasattr(self, "project_list"):
            return
        for row in range(self.project_list.count()):
            item = self.project_list.item(row)
            source_index = item.data(Qt.ItemDataRole.UserRole)
            p = self.projects[source_index] if isinstance(source_index, int) and source_index < len(self.projects) else {}
            haystack = " ".join([
                str(p.get("title", "")),
                str(p.get("category", "")),
                str(p.get("description", "")),
            ]).lower()
            item.setHidden(bool(query) and query not in haystack)

    def _refresh_project_list_item(self, index):
        if 0 <= index < self.project_list.count():
            p = self.projects[index]
            title = p.get("title", "(untitled)") or "(untitled)"
            category = (p.get("category", "") or "").strip()
            text = f"{index + 1:02d}   {title}"
            if category:
                text += f"\n      {category}"
            self.project_list.item(index).setText(text)
            self._filter_project_list(
                self.project_search.text() if hasattr(self, "project_search") else ""
            )

    # ---------- Status helpers ----------
    def _wire_dirty_signals(self):
        """Mark the editor as edited whenever a user changes an editable field."""
        if not HAS_QT:
            return

        def wire(widget, signal_name):
            # Avoid duplicate connections when the project form is rebuilt.
            if widget.property("_dirty_signal_wired"):
                return
            signal = getattr(widget, signal_name, None)
            if signal is None:
                return
            signal.connect(self._on_user_edit)
            widget.setProperty("_dirty_signal_wired", True)

        for widget in self.findChildren(QWidget):
            # Search/filter controls are navigation, not data edits.
            if widget is getattr(self, "project_search", None):
                continue
            if isinstance(widget, QLineEdit):
                wire(widget, "textChanged")
            elif isinstance(widget, QTextEdit):
                wire(widget, "textChanged")
            elif isinstance(widget, QCheckBox):
                wire(widget, "toggled")
            elif isinstance(widget, QComboBox):
                wire(widget, "currentTextChanged")
            # QListWidget is used for project navigation; selecting/reordering
            # a project should not turn the document into an edited state.

    def _on_user_edit(self, *args):
        if self._loading_form:
            return
        self._mark_dirty()

    def _mark_dirty(self):
        self._unsaved = True
        if hasattr(self, "tb_dirty"):
            self.tb_dirty.setVisible(True)
        try:
            self.status.showMessage("Unsaved changes ●", 2000)
        except Exception:
            pass
        if hasattr(self, "project_header_status"):
            self.project_header_status.setText("EDITED")
            self.project_header_status.setToolTip("Edited — changes have not been saved")
            self.project_header_status.setProperty("dirty", "true")
            self.project_header_status.style().unpolish(self.project_header_status)
            self.project_header_status.style().polish(self.project_header_status)

    def _mark_clean(self):
        self._unsaved = False
        if hasattr(self, "tb_dirty"):
            self.tb_dirty.setVisible(False)
        if hasattr(self, "project_header_status"):
            self.project_header_status.setText("SAVED")
            self.project_header_status.setToolTip("Saved — no unsaved changes")
            self.project_header_status.setProperty("dirty", "false")
            self.project_header_status.style().unpolish(self.project_header_status)
            self.project_header_status.style().polish(self.project_header_status)

    # ---------- Form helpers ----------
    def _clear_form(self):
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            else:
                sub = item.layout()
                if sub:
                    while sub.count():
                        sub_item = sub.takeAt(0)
                        sw = sub_item.widget()
                        if sw:
                            sw.deleteLater()
        self.entries = {}

    def _add_section(self, title, subtitle=None):
        """Insert a labeled section divider."""
        self.form_layout.addWidget(SectionDivider(title))
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("pageSubtitle")
            sub.setWordWrap(True)
            self.form_layout.addWidget(sub)

    def _add_field(self, label, widget):
        row = QWidget()
        row.setObjectName("formRow")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 2, 0, 2)
        rl.setSpacing(14)
        lbl = QLabel(label)
        lbl.setObjectName("formLabel")
        lbl.setFixedWidth(120)
        lbl.setWordWrap(True)
        rl.addWidget(lbl, 0, Qt.AlignmentFlag.AlignTop)
        rl.addWidget(widget, 1)
        self.form_layout.addWidget(row)
        return row

    def _add_widget(self, widget):
        self.form_layout.addWidget(widget)

    # ---------- Load project ----------
    def _load_project(self, index):
        if index < 0 or index >= len(self.projects):
            return

        self._loading_form = True
        self.current_index = index
        p = self.projects[index]

        # Header
        title_preview = p.get("title", "Untitled Project") or "Untitled Project"
        category_preview = (p.get("category", "") or "").strip()
        file_preview = p.get("file", "") or ""
        self.project_header_title.setText(title_preview)
        meta_parts = [f"PROJECT {index + 1:02d} / {len(self.projects):02d}"]
        if category_preview:
            meta_parts.append(category_preview)
        if file_preview:
            meta_parts.append(file_preview)
        self.project_header_meta.setText("   ·   ".join(meta_parts))

        self.project_list.blockSignals(True)
        self.project_list.setCurrentRow(index)
        self.project_list.blockSignals(False)

        self._clear_form()

        # ============ SECTION: Basics ============
        self._add_section("BASICS", "Title, category and long description.")

        self.entries["title"] = QLineEdit(p.get("title", ""))
        self.entries["category"] = QLineEdit(p.get("category", ""))
        self.entries["description"] = QTextEdit()
        self.entries["description"].setMinimumHeight(140)
        self.entries["description"].setAcceptRichText(True)
        self.entries["description"].setTabChangesFocus(True)
        desc_raw = p.get("description", "") or ""
        if "<" in desc_raw:
            self.entries["description"].setHtml(desc_raw)
        else:
            self.entries["description"].setPlainText(desc_raw)

        self._add_field("Title", self.entries["title"])
        self._add_field("Category", self.entries["category"])

        # Description + formatting toolbar (Bold / Italic / Highlight)
        desc_wrap = QWidget()
        desc_lay = QVBoxLayout(desc_wrap)
        desc_lay.setContentsMargins(0, 0, 0, 0)
        desc_lay.setSpacing(4)
        fmt_bar = QHBoxLayout()
        fmt_bar.setSpacing(6)
        btn_b = QPushButton("B")
        btn_b.setObjectName("fmtBtn")
        btn_b.setFixedSize(32, 28)
        btn_b.setToolTip("Bold (Ctrl+B)")
        btn_b.setStyleSheet("font-weight:800;")
        btn_i = QPushButton("I")
        btn_i.setObjectName("fmtBtn")
        btn_i.setFixedSize(32, 28)
        btn_i.setToolTip("Italic (Ctrl+I)")
        btn_i.setStyleSheet("font-style:italic;")
        btn_h = QPushButton("H")
        btn_h.setObjectName("fmtBtn")
        btn_h.setFixedSize(32, 28)
        btn_h.setToolTip("Highlight selected text")
        btn_clear = QPushButton("Clear fmt")
        btn_clear.setObjectName("ghostBtn")
        btn_clear.setFixedHeight(28)
        btn_clear.setToolTip("Remove formatting from selection")
        fmt_bar.addWidget(btn_b)
        fmt_bar.addWidget(btn_i)
        fmt_bar.addWidget(btn_h)
        fmt_bar.addWidget(btn_clear)
        fmt_bar.addStretch(1)
        hint = QLabel("Select text, then B / I / H")
        hint.setObjectName("pageSubtitle")
        fmt_bar.addWidget(hint)
        desc_lay.addLayout(fmt_bar)
        desc_lay.addWidget(self.entries["description"])
        self._add_field("Description", desc_wrap)

        btn_b.clicked.connect(lambda: self._fmt_description("bold"))
        btn_i.clicked.connect(lambda: self._fmt_description("italic"))
        btn_h.clicked.connect(lambda: self._fmt_description("highlight"))
        btn_clear.clicked.connect(lambda: self._fmt_description("clear"))

        # Optional per-project artist — can show/hide on the project page
        self._add_section(
            "ARTIST NAME",
            "Optional. Leave name empty to use the global Artist name from the Artist tab. "
            "Uncheck “Show on project page” to hide the name for this project only."
        )
        self.entries["showArtist"] = QCheckBox("Show artist name on this project page")
        self.entries["showArtist"].setChecked(p.get("showArtist", True) is not False)
        self.form_layout.addWidget(self.entries["showArtist"])
        self.entries["artistName"] = QLineEdit(str(p.get("artistName", "") or ""))
        self.entries["artistName"].setPlaceholderText("Empty = use global artist name")
        self._add_field("Name", self.entries["artistName"])

        def _sync_artist_enabled(state=None):
            on = self.entries["showArtist"].isChecked()
            self.entries["artistName"].setEnabled(on)
        self.entries["showArtist"].stateChanged.connect(_sync_artist_enabled)
        _sync_artist_enabled()

        # Wire live project preview
        for key in ("title", "category", "artistName"):
            if key in self.entries:
                self.entries[key].textChanged.connect(self._kick_project_preview)
        self.entries["showArtist"].stateChanged.connect(self._kick_project_preview)
        self.entries["description"].textChanged.connect(self._kick_project_preview)
        QTimer.singleShot(0, self._refresh_project_preview)
        QTimer.singleShot(0, self._refresh_project_preview)

        # Status / tags / client visibility
        self._add_section(
            "STATUS & TAGS",
            "Status badge (Final / WIP / Hero). Tags for search. Client-hide removes this project in ?client=1 mode."
        )
        self.entries["status"] = QComboBox()
        self.entries["status"].addItems(["", "Final", "WIP", "Hero", "Review"])
        cur_st = str(p.get("status", "") or "")
        idx = self.entries["status"].findText(cur_st)
        self.entries["status"].setCurrentIndex(max(0, idx))
        self._add_field("Status", self.entries["status"])
        tags_val = p.get("tags") or []
        if isinstance(tags_val, str):
            tags_val = [x.strip() for x in tags_val.split(",") if x.strip()]
        self.entries["tags"] = QLineEdit(", ".join(tags_val))
        self.entries["tags"].setPlaceholderText("comma separated, e.g. lighting, outdoor")
        self._add_field("Tags", self.entries["tags"])
        self.entries["clientHidden"] = QCheckBox("Hide in client mode (?client=1)")
        self.entries["clientHidden"].setChecked(bool(p.get("clientHidden")))
        self.form_layout.addWidget(self.entries["clientHidden"])


        # ============ SECTION: Media ============
        self._add_section("MEDIA", "Main video and before/after images.")

        project_folder = os.path.join(ASSETS_IMAGES, f"project-{index + 1:02d}")

        self.entries["video"] = FilePickerRow(
            "Video", p.get("video", ""),
            filetypes=[("Video files", "*.mp4 *.webm *.mov"), ("All files", "*.*")],
            dest_folder=ASSETS_VIDEOS
        )
        self.entries["poster"] = FilePickerRow(
            "Video thumbnail", p.get("poster", ""),
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp"), ("All files", "*.*")],
            dest_folder=project_folder
        )
        self.entries["before"] = FilePickerRow(
            "Before image", p.get("before", ""),
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp"), ("All files", "*.*")],
            dest_folder=project_folder
        )
        self.entries["after"] = FilePickerRow(
            "After image", p.get("after", ""),
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp"), ("All files", "*.*")],
            dest_folder=project_folder
        )

        self._add_field("Video", self.entries["video"])
        self._add_field("Thumbnail", self.entries["poster"])
        self._add_field("Before", self.entries["before"])
        self._add_field("After", self.entries["after"])

        # ============ SECTION: Extra videos ============
        self._add_section("EXTRA VIDEOS", "Optional multi-clip player.")

        self.entries["videos"] = VideosPicker(
            values=p.get("videos", []),
            dest_folder=ASSETS_VIDEOS,
        )
        self._add_widget(self.entries["videos"])

        # ============ SECTION: Gallery ============
        self._add_section("GALLERY", "Stills with optional captions.")

        self.entries["gallery"] = GalleryPicker(
            values=p.get("gallery", []),
            dest_folder=project_folder
        )
        self._add_widget(self.entries["gallery"])

        # ============ SECTION: Passes ============
        self._add_section("RENDER PASSES", "Carousel + labeled grid. Name shows under each image.")

        self.entries["passes"] = NamedImagePicker(
            values=p.get("passes", []),
            dest_folder=project_folder,
            placeholder=(
                "One pass image per line. Name shows under the image.\n"
                "path | ReadableName   (name defaults to filename when browsing)"
            ),
        )
        self._add_widget(self.entries["passes"])

        # ============ SECTION: Voice-over script ============
        self._add_section(
            "VOICE-OVER SCRIPT",
            "Optional presenter script for this project. Leave empty to auto-build from title/description/passes."
        )
        self.entries["vo_script"] = QTextEdit()
        self.entries["vo_script"].setPlaceholderText(
            "e.g. Welcome to the kitchen lighting breakdown. We start with key fill…"
        )
        self.entries["vo_script"].setMinimumHeight(100)
        self.entries["vo_script"].setPlainText(p.get("vo_script") or "")
        self._add_widget(self.entries["vo_script"])
        vo_row = QHBoxLayout()
        b_test_vo = QPushButton("Test speak")
        b_test_vo.setToolTip("Speak this script with a female system voice (Windows/macOS)")
        b_gen_vo = QPushButton("Fill from project data")
        b_gen_vo.setToolTip("Generate a starter script from title, description, details, passes")
        b_test_vo.clicked.connect(self._test_project_vo)
        b_gen_vo.clicked.connect(self._fill_vo_from_project)
        vo_row.addWidget(b_test_vo)
        vo_row.addWidget(b_gen_vo)
        vo_row.addStretch(1)
        vo_w = QWidget()
        vo_w.setLayout(vo_row)
        self._add_widget(vo_w)

        # ============ SECTION: Details ============
        self._add_section("DETAILS", "Toggle ROLE / TASK / DURATION / OUTPUT and add extras.")

        existing = p.get("details") or {}
        existing_norm = {str(k).strip().upper(): v for k, v in existing.items()}

        self.entries["detail_rows"] = {}
        for key in STANDARD_DETAIL_KEYS:
            row_w = QWidget()
            row = QHBoxLayout(row_w)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)

            chk = QCheckBox("Show")
            chk.setChecked(key in existing_norm)
            val = QLineEdit(str(existing_norm.get(key, "") if key in existing_norm else ""))
            val.setPlaceholderText(key.title())
            chk.setFixedWidth(64)

            lbl = QLabel(key)
            lbl.setFixedWidth(90)
            lbl.setStyleSheet("color:#9aa2ae; font-weight:700;")

            row.addWidget(chk)
            row.addWidget(lbl)
            row.addWidget(val, 1)
            self.form_layout.addWidget(row_w)
            self.entries["detail_rows"][key] = (chk, val)

            def _bind(c=chk, v=val):
                def _toggle(state):
                    v.setEnabled(c.isChecked())
                c.stateChanged.connect(_toggle)
                v.setEnabled(c.isChecked())
            _bind()

        extras = []
        for k, v in existing.items():
            ku = str(k).strip().upper()
            if ku not in STANDARD_DETAIL_KEYS:
                extras.append(f"{k}: {v}")
        self.entries["details_extra"] = QTextEdit()
        self.entries["details_extra"].setFixedHeight(64)
        self.entries["details_extra"].setPlaceholderText(
            "Extra details (optional) — one per line: Key: value"
        )
        self.entries["details_extra"].setPlainText("\n".join(extras))
        self._add_field("Extra", self.entries["details_extra"])

        # ============ SECTION: Software ============
        self._add_section("SOFTWARE", "Comma-separated list of tools.")
        self.entries["tools"] = QLineEdit(", ".join(p.get("tools", [])))
        self.entries["tools"].setPlaceholderText("e.g. Blender, 3ds Max, V-Ray")
        self._add_field("Tools", self.entries["tools"])

        # ============ SECTION: Contributions ============
        self._add_section("CONTRIBUTIONS", "Number, name per line.")
        self.entries["contributions"] = QTextEdit()
        self.entries["contributions"].setFixedHeight(84)
        self.entries["contributions"].setPlaceholderText("e.g. 01, LIGHTING")
        self.entries["contributions"].setPlainText(
            "\n".join(f"{n}, {t}" for n, t in p.get("contributions", []))
        )
        self._add_widget(self.entries["contributions"])

        # ============ SECTION: Chapters ============
        self._add_section("CHAPTERS", "Name, seconds per line.")
        self.entries["chapters"] = QTextEdit()
        self.entries["chapters"].setFixedHeight(84)
        self.entries["chapters"].setPlaceholderText("e.g. FINAL, 0")
        self.entries["chapters"].setPlainText(
            "\n".join(f"{c['name']}, {c['time']}" for c in p.get("chapters", []))
        )
        self._add_widget(self.entries["chapters"])

        # ============ SECTION: File ============
        self._add_section("FILE", "HTML page associated with this project.")
        file_row = QLineEdit(p.get("file", ""))
        file_row.setReadOnly(True)
        self._add_field("HTML", file_row)

        self._wire_dirty_signals()
        self._loading_form = False
        self.status.showMessage(f"Editing project {index + 1}/{len(self.projects)}")
        self._update_action_bar()
        self._sync_toolbar_info()

        # Keep Pass Breakdown + title in sync with this project
        try:
            if "passes" in self.entries and hasattr(self.entries["passes"], "text"):
                self.entries["passes"].text.textChanged.connect(self._on_project_passes_edited)
            if "title" in self.entries:
                self.entries["title"].textChanged.connect(self._on_project_title_edited)
        except Exception:
            pass
        try:
            self._auto_sync_project_to_breakdown(quiet=True)
        except Exception:
            pass
        try:
            self._refresh_dashboard()
        except Exception:
            pass

    def _description_to_storage(self, edit):
        """Store description as compact HTML: <b>/<i>/<mark> + <br> for lines.

        Qt emits <span style="font-weight:700"> not <b>, so we convert spans.
        Blank lines in the editor become <br><br> in the stored HTML.
        """
        if edit is None:
            return ""
        plain = edit.toPlainText()
        if not plain.strip():
            return ""

        html = edit.toHtml()
        body_m = re.search(r"<body[^>]*>(.*)</body>", html, re.I | re.S)
        body = body_m.group(1) if body_m else html

        def convert_spans(src):
            # Repeat to unwrap nested spans
            for _ in range(12):
                prev = src
                # Bold
                src = re.sub(
                    r'<span\s+([^>]*?)style="([^"]*)"([^>]*)>(.*?)</span>',
                    lambda m: _span_to_semantic(m),
                    src,
                    flags=re.I | re.S,
                )
                if src == prev:
                    break
            return src

        def _span_to_semantic(m):
            pre, style, post, inner = m.group(1), m.group(2), m.group(3), m.group(4)
            style_l = style.lower()
            open_tags = []
            close_tags = []
            if re.search(r"font-weight:\s*(bold|[6-9]00)", style_l):
                open_tags.append("<b>")
                close_tags.append("</b>")
            if "font-style:italic" in style_l or "font-style: italic" in style_l:
                open_tags.append("<i>")
                close_tags.append("</i>")
            if "background-color:" in style_l or "background:" in style_l:
                # skip transparent / none
                if not re.search(r"background(?:-color)?:\s*(transparent|none)", style_l):
                    open_tags.append("<mark>")
                    close_tags.append("</mark>")
            if not open_tags:
                return inner  # drop decorative span
            return "".join(open_tags) + inner + "".join(reversed(close_tags))

        # Use iterative manual span conversion (callable in replace needs nested def in loop)
        for _ in range(12):
            prev = body
            def repl(m):
                style = m.group(2) or ""
                inner = m.group(4)
                style_l = style.lower()
                opens, closes = [], []
                if re.search(r"font-weight:\s*(bold|[6-9]00)", style_l):
                    opens.append("<b>"); closes.append("</b>")
                if "font-style:italic" in style_l.replace(" ", ""):
                    opens.append("<i>"); closes.append("</i>")
                if "background-color:" in style_l or re.search(r"(?<!-)background:\s*#", style_l):
                    if "transparent" not in style_l and "none" not in style_l:
                        opens.append("<mark>"); closes.append("</mark>")
                if not opens:
                    return inner
                return "".join(opens) + inner + "".join(reversed(closes))
            body = re.sub(
                r'<span\s+([^>]*?)style="([^"]*)"([^>]*)>(.*?)</span>',
                repl,
                body,
                flags=re.I | re.S,
            )
            if body == prev:
                break

        body = re.sub(r"</?strong\b[^>]*>", lambda m: "<b>" if m.group(0).lower().find("</") < 0 else "</b>", body, flags=re.I)
        body = re.sub(r"</?em\b[^>]*>", lambda m: "<i>" if m.group(0).lower().find("</") < 0 else "</i>", body, flags=re.I)
        # leftover spans
        body = re.sub(r"<span[^>]*>", "", body, flags=re.I)
        body = re.sub(r"</span>", "", body, flags=re.I)

        # Paragraphs → content + line breaks (empty p → blank line)
        def p_repl(m):
            inner = m.group(1)
            core = re.sub(r"<br\s*/?>", "", inner, flags=re.I).strip()
            if not core:
                return "<br><br>"
            return inner.rstrip() + "<br>"

        body = re.sub(r"<p[^>]*>(.*?)</p>", p_repl, body, flags=re.I | re.S)
        body = re.sub(r"</?(?:html|head|body|meta|style)[^>]*>", "", body, flags=re.I)
        body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
        body = re.sub(r"(?:<br\s*/?>\s*){5,}", "<br><br>", body, flags=re.I)
        body = re.sub(r"^(?:\s*<br\s*/?>)+", "", body, flags=re.I)
        body = re.sub(r"(?:<br\s*/?>\s*)+$", "", body, flags=re.I)
        body = body.strip()

        if not re.search(r"<(b|i|mark|br)\b", body, re.I):
            # Plain: preserve blank lines
            parts = plain.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            esc = []
            for i, line in enumerate(parts):
                if i > 0:
                    esc.append("<br>")
                esc.append(
                    line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                )
            return "".join(esc)

        return body

    def _fmt_description(self, kind: str):
        edit = self.entries.get("description") if self.entries else None
        if edit is None:
            return
        cursor = edit.textCursor()
        if not cursor.hasSelection() and kind != "clear":
            self.status.showMessage("Select text first to format", 2500)
            return
        fmt = QTextCharFormat()
        if kind == "bold":
            weight = cursor.charFormat().fontWeight()
            fmt.setFontWeight(
                QFont.Weight.Normal if weight > QFont.Weight.Normal else QFont.Weight.Bold
            )
            cursor.mergeCharFormat(fmt)
        elif kind == "italic":
            italic = cursor.charFormat().fontItalic()
            fmt.setFontItalic(not italic)
            cursor.mergeCharFormat(fmt)
        elif kind == "highlight":
            # Toggle gold/amber highlight
            cur = cursor.charFormat()
            bg = cur.background()
            if bg.style() != Qt.BrushStyle.NoBrush and bg.color().isValid():
                fmt.setBackground(QBrush())
            else:
                fmt.setBackground(QBrush(QColor("#e8c96a")))
            cursor.mergeCharFormat(fmt)
        elif kind == "clear":
            fmt.setFontWeight(QFont.Weight.Normal)
            fmt.setFontItalic(False)
            fmt.setBackground(QBrush())
            cursor.mergeCharFormat(fmt)
        edit.mergeCurrentCharFormat(fmt)
        edit.setTextCursor(cursor)
        edit.setFocus()
        self._mark_dirty()

    # ---------- Commit ----------
    def _commit_current(self):

        if self.current_index < 0 or self.current_index >= len(self.projects):
            return
        if not self.entries:
            return

        p = self.projects[self.current_index]

        p["title"] = self.entries["title"].text().strip()
        p["category"] = self.entries["category"].text().strip()
        p["description"] = self._description_to_storage(self.entries["description"])
        if "artistName" in self.entries:
            p["artistName"] = self.entries["artistName"].text().strip()
        if "showArtist" in self.entries:
            p["showArtist"] = self.entries["showArtist"].isChecked()
        if "status" in self.entries:
            p["status"] = self.entries["status"].currentText().strip()
        if "tags" in self.entries:
            p["tags"] = [t.strip() for t in self.entries["tags"].text().split(",") if t.strip()]
        if "clientHidden" in self.entries:
            p["clientHidden"] = self.entries["clientHidden"].isChecked()

        p["video"] = self.entries["video"].text()
        p["poster"] = self.entries["poster"].text()
        p["before"] = self.entries["before"].text()
        p["after"] = self.entries["after"].text()

        p["gallery"] = self.entries["gallery"].values()
        if "vo_script" in self.entries:
            try:
                p["vo_script"] = self.entries["vo_script"].toPlainText().strip()
            except Exception:
                p["vo_script"] = p.get("vo_script") or ""
        raw_passes = self.entries["passes"].values() if "passes" in self.entries else []
        # Ensure web-safe relative paths (copy absolute/viewer paths into showcase assets)
        try:
            from shared import project_bridge as bridge
            # Convert through RPB shape then back so images land under assets/images/project-XX/
            as_rpb = bridge.showcase_passes_to_rpb(raw_passes)
            p["passes"] = bridge.rpb_to_showcase_passes(as_rpb, self.current_index)
            if "passes" in self.entries:
                try:
                    self.entries["passes"].text.blockSignals(True)
                    self.entries["passes"].setValues(p["passes"])
                    self.entries["passes"].text.blockSignals(False)
                except Exception:
                    pass
        except Exception:
            p["passes"] = raw_passes
        p["videos"] = self.entries["videos"].values() if "videos" in self.entries else []

        p["tools"] = [t.strip() for t in self.entries["tools"].text().split(",") if t.strip()]

        details = {}
        for key in STANDARD_DETAIL_KEYS:
            chk, val = self.entries["detail_rows"][key]
            if chk.isChecked():
                details[key] = val.text().strip()
        for line in self.entries["details_extra"].toPlainText().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip()
                if k:
                    details[k] = v.strip()
        p["details"] = details

        contribs = []
        for line in self.entries["contributions"].toPlainText().splitlines():
            if "," in line:
                n, t = line.split(",", 1)
                contribs.append([n.strip(), t.strip()])
        p["contributions"] = contribs

        chapters = []
        for line in self.entries["chapters"].toPlainText().splitlines():
            if "," in line:
                n, t = line.rsplit(",", 1)
                try:
                    chapters.append({"name": n.strip(), "time": float(t.strip())})
                except ValueError:
                    pass
        p["chapters"] = chapters

    # ---------- Events ----------
    def on_project_selected(self, index):
        if index < 0 or index == self.current_index:
            return
        # Save current breakdown stack into the project we are leaving
        try:
            self._auto_sync_breakdown_to_project(quiet=True)
        except Exception:
            pass
        self._commit_current()
        self._refresh_project_list_item(self.current_index)
        self._load_project(index)

    def _goto_prev_project(self):
        if self.current_index > 0:
            self.on_project_selected(self.current_index - 1)

    def _goto_next_project(self):
        if self.current_index < len(self.projects) - 1:
            self.on_project_selected(self.current_index + 1)

    def _update_action_bar(self):
        n = len(self.projects)
        i = self.current_index + 1
        if hasattr(self, "tb_info"):
            pass  # handled by _sync_toolbar_info

    def _sync_toolbar_info(self):
        if not hasattr(self, "tb_info"):
            return
        n = len(self.projects)
        if n == 0:
            self.tb_info.setText("●  No projects")
            return
        i = self.current_index + 1
        self.tb_info.setText(f"●  {i:02d} / {n:02d}")

    # ---------- Actions ----------
    def _refresh_thanks_form(self):
        t = getattr(self, "thanks", None) or {}
        if not hasattr(self, "thanks_enabled"):
            return
        self.thanks_enabled.setChecked(bool(t.get("enabled", False)))
        self.thanks_eyebrow.setText(str(t.get("eyebrow", "")))
        self.thanks_heading.setText(str(t.get("heading", "")))
        self.thanks_sub.setText(str(t.get("sub", "")))
        self.thanks_note.setText(str(t.get("note", "")))
        lines = []
        for d in t.get("departments") or []:
            if isinstance(d, dict):
                lines.append(f"{d.get('name', '')} | {d.get('text', '')}")
            else:
                lines.append(str(d))
        self.thanks_depts.setPlainText("\n".join(lines))

    def _commit_thanks(self):
        if not hasattr(self, "thanks_enabled"):
            return
        depts = []
        for line in self.thanks_depts.toPlainText().splitlines():
            line = line.strip()
            if not line:
                continue
            if " | " in line:
                name, speech = line.split(" | ", 1)
                depts.append({"name": name.strip(), "text": speech.strip()})
            else:
                depts.append({"name": line, "text": ""})
        self.thanks = {
            "enabled": self.thanks_enabled.isChecked(),
            "eyebrow": self.thanks_eyebrow.text().strip(),
            "heading": self.thanks_heading.text().strip(),
            "sub": self.thanks_sub.text().strip(),
            "note": self.thanks_note.text().strip(),
            "departments": depts,
        }


    def _browse_screen_media(self, which: str):
        """Browse image/video for Home or End media; copy into assets/."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose media",
            BASE_DIR,
            "Media (*.png *.jpg *.jpeg *.webp *.gif *.mp4 *.webm *.mov);;All (*)"
        )
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        is_video = ext in (".mp4", ".webm", ".mov", ".mkv", ".avi")
        dest_dir = ASSETS_VIDEOS if is_video else ASSETS_IMAGES
        os.makedirs(dest_dir, exist_ok=True)
        name = os.path.basename(path)
        dest = os.path.join(dest_dir, name)
        try:
            if os.path.abspath(path) != os.path.abspath(dest):
                shutil.copy2(path, dest)
        except OSError as e:
            QMessageBox.warning(self, "Copy failed", str(e))
            return
        rel = ("assets/videos/" if is_video else "assets/images/") + name
        if which == "home":
            self.home_media.setText(rel)
            self.home_media_type.setCurrentIndex(2 if is_video else 1)
        else:
            self.end_media.setText(rel)
            self.end_media_type.setCurrentIndex(2 if is_video else 1)
        self._mark_dirty()
        self.status.showMessage(f"Media set: {rel}", 3000)
        if hasattr(self, "_refresh_screen_preview"):
            self._refresh_screen_preview()



    def _refresh_thanks_preview(self):
        if not hasattr(self, "thanks_preview"):
            return
        depts = []
        if hasattr(self, "thanks_depts"):
            for line in self.thanks_depts.toPlainText().splitlines():
                line = line.strip()
                if not line:
                    continue
                if " | " in line:
                    n, t = line.split(" | ", 1)
                    depts.append((n.strip(), t.strip()))
                else:
                    depts.append((line, ""))
        brand = self.header_brand.text().strip() if hasattr(self, "header_brand") else "ARTIST SHOWCASE · 2026"
        self.thanks_preview.set_mode("thanks")
        self.thanks_preview.set_data(
            brand=brand,
            enabled=self.thanks_enabled.isChecked() if hasattr(self, "thanks_enabled") else True,
            eyebrow=self.thanks_eyebrow.text() if hasattr(self, "thanks_eyebrow") else "",
            heading=self.thanks_heading.text() if hasattr(self, "thanks_heading") else "",
            sub=self.thanks_sub.text() if hasattr(self, "thanks_sub") else "",
            note=self.thanks_note.text() if hasattr(self, "thanks_note") else "",
            depts=depts,
        )

    def _kick_project_preview(self, *_args):
        if not hasattr(self, "_project_preview_timer"):
            self._project_preview_timer = QTimer(self)
            self._project_preview_timer.setSingleShot(True)
            self._project_preview_timer.setInterval(80)
            self._project_preview_timer.timeout.connect(self._refresh_project_preview)
        self._project_preview_timer.start()

    def _refresh_project_preview(self):
        if not hasattr(self, "project_preview"):
            return
        title = ""
        category = ""
        desc = ""
        proj_artist = ""
        show_artist = True
        if self.entries:
            if "title" in self.entries:
                title = self.entries["title"].text().strip()
            if "category" in self.entries:
                category = self.entries["category"].text().strip()
            if "description" in self.entries:
                desc = self.entries["description"].toPlainText().strip()  # preview: plain
            if "artistName" in self.entries:
                proj_artist = self.entries["artistName"].text().strip()
            if "showArtist" in self.entries:
                show_artist = self.entries["showArtist"].isChecked()
        brand = self.header_brand.text().strip() if hasattr(self, "header_brand") else "ARTIST SHOWCASE · 2026"
        artist_name = self.artist_name_edit.text().strip() if hasattr(self, "artist_name_edit") else ""
        if not show_artist:
            proj_artist = ""
            artist_name = ""
        self.project_preview.set_mode("project")
        self.project_preview.set_data(
            brand=brand,
            heading=title,
            category=category,
            description=desc,
            project_artist=proj_artist,
            artist_name=artist_name,
        )


    def _on_preview_mode_changed(self, _idx=None):
        if hasattr(self, "screen_preview"):
            mode = "end" if self.preview_mode_combo.currentIndex() == 1 else "home"
            self.screen_preview.set_mode(mode)
            self._refresh_screen_preview()

    def _refresh_screen_preview(self):
        if not hasattr(self, "screen_preview"):
            return
        mode = "end" if getattr(self, "preview_mode_combo", None) and self.preview_mode_combo.currentIndex() == 1 else "home"
        self.screen_preview.set_mode(mode)
        brand = self.header_brand.text().strip() if hasattr(self, "header_brand") else ""
        artist_name = self.artist_name_edit.text().strip() if hasattr(self, "artist_name_edit") else ""
        artist_role = self.artist_role_edit.text().strip() if hasattr(self, "artist_role_edit") else ""
        n_proj = len(getattr(self, "projects", []) or [])
        if mode == "home":
            mt = self.home_media_type.currentText()
            self.screen_preview.set_data(
                brand=brand,
                eyebrow=self.home_eyebrow.text(),
                heading=self.home_heading.toPlainText(),
                note="",
                media_type="" if mt == "(none)" else mt,
                media_path=self.home_media.text().strip(),
                artist_name=artist_name,
                artist_role=artist_role,
                project_count=n_proj,
            )
        else:
            mt = self.end_media_type.currentText()
            self.screen_preview.set_data(
                brand=brand,
                eyebrow=self.end_eyebrow.text(),
                heading=self.end_heading.text(),
                note=self.end_note.text(),
                media_type="" if mt == "(none)" else mt,
                media_path=self.end_media.text().strip(),
                artist_name=artist_name,
                artist_role=artist_role,
                project_count=n_proj,
            )

    def _commit_home_end_font(self):
        if hasattr(self, "header_brand"):
            self.header = {
                "brand": self.header_brand.text().strip() or "ARTIST SHOWCASE · 2026",
            }
        if hasattr(self, "home_eyebrow"):
            mt = self.home_media_type.currentText()
            self.home = {
                "eyebrow": self.home_eyebrow.text().strip(),
                "heading": self.home_heading.toPlainText().strip(),
                "mediaType": "" if mt == "(none)" else mt,
                "media": self.home_media.text().strip(),
            }
        if hasattr(self, "end_eyebrow"):
            emt = self.end_media_type.currentText()
            self.end = {
                "eyebrow": self.end_eyebrow.text().strip(),
                "heading": self.end_heading.text().strip(),
                "note": self.end_note.text().strip(),
                "mediaType": "" if emt == "(none)" else emt,
                "media": self.end_media.text().strip(),
            }
        if hasattr(self, "font_family"):
            self.font = {
                "family": self.font_family.text().strip(),
                "url": self.font_url.text().strip(),
            }

    def save_current_project(self):
        if getattr(self, "_project_locked", False):
            QMessageBox.information(self, "Locked", "Unlock from View menu to edit.")
            return
        self._commit_current()
        try:
            self._auto_sync_breakdown_to_project(quiet=True)
        except Exception:
            pass
        self._commit_thanks()
        self._commit_home_end_font()
        self.artist["name"] = self.artist_name_edit.text().strip()
        self.artist["role"] = self.artist_role_edit.text().strip()
        for i, p in enumerate(self.projects):
            p["id"] = i
        try:
            backup_data_js()
            save_data_js(self.artist, self.projects, getattr(self, 'thanks', None), getattr(self, 'home', None), getattr(self, 'end', None), getattr(self, 'font', None), getattr(self, 'header', None))
            ensure_asset_folders(self.projects)
            sync_html_data_project_attrs(self.projects)
            title = self.projects[self.current_index].get("title", "project")
            self.status.showMessage(f"Saved project: {title} ✔", 3500)
            self._refresh_project_list_item(self.current_index)
            self._mark_clean()
        except Exception as e:
            QMessageBox.critical(self, "Save error", str(e))

    def save_all(self):
        if getattr(self, "_project_locked", False):
            QMessageBox.information(self, "Locked", "Unlock from View menu to edit.")
            return
        self._commit_current()
        try:
            self._auto_sync_breakdown_to_project(quiet=True)
        except Exception:
            pass
        self._commit_thanks()
        self._commit_home_end_font()
        self.artist["name"] = self.artist_name_edit.text().strip()
        self.artist["role"] = self.artist_role_edit.text().strip()

        for i, p in enumerate(self.projects):
            p["id"] = i

        try:
            bak = backup_data_js()
            save_data_js(self.artist, self.projects, getattr(self, 'thanks', None), getattr(self, 'home', None), getattr(self, 'end', None), getattr(self, 'font', None), getattr(self, 'header', None))
            ensure_asset_folders(self.projects)
            sync_html_data_project_attrs(self.projects)
            bak_msg = f"\nBackup: {os.path.basename(bak)}" if bak else ""
            self.status.showMessage("Saved js/data.js ✔", 3000)
            QMessageBox.information(self, "Saved", f"js/data.js has been updated.{bak_msg}")
            self._mark_clean()
        except Exception as e:
            QMessageBox.critical(self, "Save error", str(e))

    def reload_from_disk(self):
        if QMessageBox.question(
            self, "Reload",
            "Discard unsaved changes and reload data.js from disk?"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.artist, self.projects, self.thanks, self.home, self.end, self.font, self.header = load_data_js()
        except Exception as e:
            QMessageBox.critical(self, "Reload error", str(e))
            return
        self.artist_name_edit.setText(self.artist.get("name", ""))
        self.artist_role_edit.setText(self.artist.get("role", ""))
        self._refresh_thanks_form()
        self._load_project_list()
        self._load_project(0)
        self._mark_clean()
        self.status.showMessage("Reloaded from disk", 3000)

    def force_repair(self):
        try:
            self.artist, self.projects, self.thanks, self.home, self.end, self.font, self.header = load_data_js()
            save_data_js(self.artist, self.projects, getattr(self, 'thanks', None), getattr(self, 'home', None), getattr(self, 'end', None), getattr(self, 'font', None), getattr(self, 'header', None))
            self.artist_name_edit.setText(self.artist.get("name", ""))
            self.artist_role_edit.setText(self.artist.get("role", ""))
            self._refresh_thanks_form()
            self._load_project_list()
            self._load_project(min(self.current_index, len(self.projects) - 1))
            self._mark_clean()
            self.status.showMessage("data.js repaired & saved ✔", 4000)
            QMessageBox.information(
                self, "Repair complete",
                "data.js was re-parsed (with auto-repair if needed) and rewritten as clean JSON."
            )
        except Exception as e:
            QMessageBox.critical(self, "Repair error", str(e))


    def backup_version(self):
        """Snapshot js/data.js into js/backups/ with timestamp."""
        self._commit_current()
        src = DATA_JS
        if not os.path.isfile(src):
            QMessageBox.warning(self, "Backup", "data.js not found")
            return
        bak_dir = os.path.join(BASE_DIR, "js", "backups")
        os.makedirs(bak_dir, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(bak_dir, f"data_{stamp}.js")
        shutil.copy2(src, dest)
        # keep last 20
        files = sorted(Path(bak_dir).glob("data_*.js"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in files[20:]:
            try:
                old.unlink()
            except OSError:
                pass
        self.status.showMessage(f"Backup saved: js/backups/{os.path.basename(dest)}", 5000)
        QMessageBox.information(self, "Backup", f"Saved:\n{dest}")

    def export_delivery_zip(self):
        """Zip showcase for client delivery (HTML/CSS/JS/assets only, no editor)."""
        self._commit_current()
        dest, _ = QFileDialog.getSaveFileName(
            self, "Delivery zip", os.path.join(BASE_DIR, "showcase-delivery.zip"), "Zip (*.zip)"
        )
        if not dest:
            return
        if not dest.endswith(".zip"):
            dest += ".zip"
        import zipfile
        skip = {"editor.py", "__pycache__", ".git"}
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(BASE_DIR):
                dirs[:] = [d for d in dirs if d not in skip and d != "backups" and not d.startswith(".")]
                for fn in files:
                    if fn in skip or fn.endswith(".pyc") or fn == "editor.py":
                        continue
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, BASE_DIR)
                    if rel.startswith("js" + os.sep + "backups"):
                        continue
                    zf.write(full, rel)
        self.status.showMessage(f"Delivery zip: {dest}", 6000)
        QMessageBox.information(self, "Zip Delivery", f"Created:\n{dest}")

    def bulk_import_gallery(self):
        """Import a folder of images into the current project's gallery."""
        if self.current_index < 0:
            return
        folder = QFileDialog.getExistingDirectory(self, "Folder of stills", ASSETS_IMAGES)
        if not folder:
            return
        p = self.projects[self.current_index]
        dest_dir = os.path.join(ASSETS_IMAGES, f"project-{self.current_index + 1:02d}")
        os.makedirs(dest_dir, exist_ok=True)
        exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff"}
        added = []
        for fn in sorted(os.listdir(folder)):
            ext = os.path.splitext(fn)[1].lower()
            if ext not in exts:
                continue
            src = os.path.join(folder, fn)
            safe = sanitize_filename(fn)
            dst = os.path.join(dest_dir, safe)
            if os.path.abspath(src) != os.path.abspath(dst):
                shutil.copy2(src, dst)
            rel = os.path.relpath(dst, BASE_DIR).replace("\\\\", "/")
            added.append({"src": rel, "caption": os.path.splitext(fn)[0]})
        if not added:
            QMessageBox.information(self, "Bulk import", "No images found in folder.")
            return
        gallery = list(p.get("gallery") or [])
        gallery.extend(added)
        p["gallery"] = gallery
        self._mark_dirty()
        self._load_project(self.current_index)
        QMessageBox.information(self, "Bulk import", f"Added {len(added)} image(s) to gallery.")

    def add_project(self):
        if getattr(self, "_project_locked", False):
            QMessageBox.information(self, "Locked", "Unlock from View menu to edit.")
            return
        self._commit_current()
        new_id = len(self.projects)

        default_file = f"project-{new_id + 1:02d}.html"
        file_name, ok = QInputDialog.getText(
            self, "New Project", "HTML file name:", text=default_file
        )
        if not ok or not file_name.strip():
            return
        file_name = file_name.strip()

        if not file_name.lower().endswith(".html"):
            file_name += ".html"

        dest = os.path.join(PROJECTS_DIR, file_name)
        if os.path.isfile(dest):
            reply = QMessageBox.question(
                self, "File exists",
                f"{file_name} already exists.\nOverwrite the HTML page?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        title = "NEW PROJECT"
        self.projects.append({
            "id": new_id,
            "file": file_name,
            "title": title,
            "category": "CATEGORY / SUB",
            "description": "",
            "video": "",
            "poster": "",
            "details": {},
            "tools": [],
            "contributions": [],
            "chapters": [],
            "gallery": [],
            "before": "",
            "after": ""
        })

        try:
            html_path = generate_project_html(new_id, file_name, title)
            msg = f"Added project + generated {file_name}"
        except Exception as e:
            html_path = None
            msg = f"Added project (HTML write failed: {e})"
            QMessageBox.warning(self, "HTML generation", str(e))

        self._load_project_list()
        self._load_project(new_id)
        self._mark_dirty()
        self.status.showMessage(msg, 4000)
        if html_path:
            QMessageBox.information(
                self, "Project created",
                f"Data entry + HTML page created:\n\n"
                f"  projects/{file_name}\n"
                f"  assets/images/project-{new_id + 1:02d}/\n\n"
                f"Fill in the form, then Save Project (Ctrl+S)."
            )

    def duplicate_project(self):
        self._commit_current()
        if self.current_index < 0:
            return

        src_proj = self.projects[self.current_index]
        new_id = len(self.projects)
        clone = json.loads(json.dumps(src_proj))
        clone["id"] = new_id
        clone["title"] = src_proj.get("title", "") + " (copy)"
        clone["file"] = f"project-{new_id + 1:02d}.html"

        self.projects.append(clone)

        try:
            generate_project_html(new_id, clone["file"], clone["title"])
            msg = f"Duplicated + generated {clone['file']}"
        except Exception as e:
            msg = f"Duplicated (HTML write failed: {e})"
            QMessageBox.warning(self, "HTML generation", str(e))

        self._load_project_list()
        self._load_project(new_id)
        self._mark_dirty()
        self.status.showMessage(msg, 4000)

    def delete_project(self):
        if getattr(self, "_project_locked", False):
            QMessageBox.information(self, "Locked", "Unlock from View menu to edit.")
            return
        if len(self.projects) <= 1:
            QMessageBox.warning(self, "Cannot delete", "At least one project is required.")
            return
        doomed = self.projects[self.current_index]
        title = doomed.get("title", "")
        file_name = doomed.get("file", "")
        if QMessageBox.question(
            self, "Delete",
            f"Delete '{title}' from data.js?"
        ) != QMessageBox.StandardButton.Yes:
            return

        html_path = os.path.join(PROJECTS_DIR, file_name) if file_name else ""
        if html_path and os.path.isfile(html_path):
            if QMessageBox.question(
                self, "Delete HTML?",
                f"Also delete projects/{file_name} from disk?"
            ) == QMessageBox.StandardButton.Yes:
                try:
                    os.remove(html_path)
                except OSError as e:
                    QMessageBox.warning(self, "Delete HTML", str(e))

        del self.projects[self.current_index]
        for i, p in enumerate(self.projects):
            p["id"] = i
        sync_html_data_project_attrs(self.projects)
        self._load_project_list()
        self._load_project(0)
        self._mark_dirty()
        self.status.showMessage("Project deleted", 3000)

    def validate_assets(self):
        self._commit_current()
        ensure_asset_folders(self.projects)
        issues = validate_project_assets(self.projects)
        if not issues:
            QMessageBox.information(self, "Validate", "All assets look good. ✔")
            self.status.showMessage("Validation passed", 3000)
            return
        text = "\n".join(f"• {x}" for x in issues[:40])
        extra = f"\n… and {len(issues) - 40} more" if len(issues) > 40 else ""
        QMessageBox.warning(
            self, f"Validate — {len(issues)} issue(s)",
            text + extra
        )
        self.status.showMessage(f"{len(issues)} validation issue(s)", 5000)

    def regenerate_html_menu(self):
        self._commit_current()
        choice = QMessageBox.question(
            self, "Regenerate HTML",
            "Regenerate HTML pages from the built-in template?\n\n"
            "Yes = ALL projects\n"
            "No  = current project only\n"
            "Cancel = abort",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel
        )
        if choice == QMessageBox.StandardButton.Cancel:
            return
        try:
            if choice == QMessageBox.StandardButton.Yes:
                paths = regenerate_all_html(self.projects)
                msg = f"Regenerated {len(paths)} HTML page(s)."
            else:
                p = self.projects[self.current_index]
                path = generate_project_html(
                    self.current_index,
                    p.get("file") or f"project-{self.current_index + 1:02d}.html",
                    p.get("title", "Project"),
                )
                msg = f"Regenerated {os.path.basename(path)}"
            self.status.showMessage(msg, 4000)
            QMessageBox.information(self, "Regenerate HTML", msg)
        except Exception as e:
            QMessageBox.critical(self, "Regenerate error", str(e))

    def export_json_action(self):
        self._commit_current()
        path, _ = QFileDialog.getSaveFileName(
            self, "Export JSON",
            os.path.join(BASE_DIR, "showcase-export.json"),
            "JSON (*.json)"
        )
        if not path:
            return
        try:
            export_json(self.artist, self.projects, path, getattr(self, 'thanks', None))
            self.status.showMessage(f"Exported {os.path.basename(path)}", 3000)
            QMessageBox.information(self, "Export", f"Wrote:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export error", str(e))

    def import_json_action(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import JSON", BASE_DIR, "JSON (*.json)"
        )
        if not path:
            return
        if QMessageBox.question(
            self, "Import",
            "Replace current artist + projects with this JSON?\n"
            "(data.js is not written until you Save All)"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.artist, self.projects, _thanks = import_json(path)
            if _thanks is not None:
                self.thanks = _thanks
            self.artist_name_edit.setText(self.artist.get("name", ""))
            self.artist_role_edit.setText(self.artist.get("role", ""))
            self._load_project_list()
            self._load_project(0)
            self._mark_dirty()
            self.status.showMessage("Imported JSON (remember to Save)", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Import error", str(e))

    # ---------- Close ----------

    # ----- Showcase ↔ Pass Breakdown bridge -----
    def _current_project_key(self):
        try:
            from shared import project_bridge as bridge
        except Exception:
            import sys
            from pathlib import Path
            root = Path(BASE_DIR).resolve().parent
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            from shared import project_bridge as bridge
        idx = max(0, getattr(self, "current_index", 0))
        if not self.projects:
            return "project", "Project", bridge
        p = self.projects[idx]
        key = bridge.project_key(p, idx)
        title = p.get("title") or key
        return key, title, bridge


    def _on_main_tab_changed(self, index: int):
        """Entering Pass Breakdown pulls project data; leaving pushes edits back."""
        prev = getattr(self, "_last_tab_index", 0)
        self._last_tab_index = index
        try:
            rpb_i = self._tab_index("Pass Breakdown")
            if prev == rpb_i and index != rpb_i:
                self._auto_sync_breakdown_to_project(quiet=True)
            if index == rpb_i:
                self._commit_current()
                self._auto_sync_project_to_breakdown(quiet=True)
            if index == 0:
                self._refresh_dashboard()
        except Exception:
            pass

    def _on_project_passes_edited(self):
        if getattr(self, "_loading_form", False) or getattr(self, "_sync_lock", False):
            return
        # Debounce: mark that project passes changed; live-push into breakdown
        try:
            self._auto_sync_project_to_breakdown(quiet=True)
        except Exception:
            pass

    def _on_project_title_edited(self, _text=""):
        if getattr(self, "_loading_form", False) or getattr(self, "_sync_lock", False):
            return
        if not getattr(self, "_rpb_editor", None):
            return
        title = ""
        if "title" in getattr(self, "entries", {}):
            try:
                title = self.entries["title"].text().strip()
            except Exception:
                title = ""
        if not title and self.projects:
            title = self.projects[self.current_index].get("title") or "Project"
        try:
            if hasattr(self._rpb_editor, "title"):
                self._rpb_editor.title.setText(title)
            key, _, _ = self._current_project_key()
            self._rpb_editor.set_project_context(key, title)
        except Exception:
            pass

    def _auto_sync_project_to_breakdown(self, quiet: bool = True):
        """Load current Showcase project passes + title into Pass Breakdown."""
        if not getattr(self, "_rpb_editor", None):
            return
        if getattr(self, "_sync_lock", False):
            return
        self._sync_lock = True
        try:
            # Prefer live form values when available
            if "passes" in getattr(self, "entries", {}) and not getattr(self, "_loading_form", False):
                try:
                    live = self.entries["passes"].values()
                except Exception:
                    live = None
            else:
                live = None
            p = self.projects[self.current_index] if self.projects else {}
            raw_passes = live if live is not None else (p.get("passes") or [])
            title = ""
            if "title" in getattr(self, "entries", {}) and not getattr(self, "_loading_form", False):
                try:
                    title = self.entries["title"].text().strip()
                except Exception:
                    title = ""
            if not title:
                title = (p.get("title") or "").strip() or f"Project {self.current_index + 1}"

            from shared import project_bridge as bridge
            key = bridge.project_key(p, self.current_index) if p else f"project-{self.current_index+1:02d}"
            passes = bridge.showcase_passes_to_rpb(raw_passes)

            # Always set title/context even if no passes yet
            self._rpb_editor.load_passes_list(passes, title=title)
            self._rpb_editor.set_project_context(key, title)
            self._breakdown_for_index = self.current_index

            if not quiet:
                if passes:
                    self.status.showMessage(
                        f"Pass Breakdown ← {len(passes)} pass(es) from “{title}”", 3500
                    )
                else:
                    self.status.showMessage(
                        f"Pass Breakdown ready for “{title}” (no passes yet)", 3500
                    )
            else:
                self.status.showMessage(
                    f"Breakdown linked to “{title}” · {len(passes)} pass(es)", 2500
                )
        except Exception as e:
            if not quiet:
                QMessageBox.warning(self, "Sync", str(e))
        finally:
            self._sync_lock = False

    def _auto_sync_breakdown_to_project(self, quiet: bool = True):
        """Write Pass Breakdown stack + title back into current Showcase project."""
        if not getattr(self, "_rpb_editor", None) or not self.projects:
            return
        if getattr(self, "_sync_lock", False):
            return
        self._sync_lock = True
        try:
            passes = self._rpb_editor.get_passes_list()
            try:
                from shared import project_bridge as bridge
                show_passes = bridge.rpb_to_showcase_passes(passes, self.current_index)
            except Exception:
                show_passes = [
                    {"src": p.get("image") or "", "name": p.get("name") or "Pass"}
                    for p in passes
                ]

            self.projects[self.current_index]["passes"] = show_passes

            # Title: prefer breakdown title if user edited it there
            bd_title = ""
            try:
                if hasattr(self._rpb_editor, "title"):
                    bd_title = self._rpb_editor.title.text().strip()
            except Exception:
                bd_title = ""
            if bd_title:
                self.projects[self.current_index]["title"] = bd_title
                if "title" in getattr(self, "entries", {}):
                    try:
                        self.entries["title"].blockSignals(True)
                        self.entries["title"].setText(bd_title)
                        self.entries["title"].blockSignals(False)
                    except Exception:
                        pass
                try:
                    self.project_header_title.setText(bd_title)
                except Exception:
                    pass

            if "passes" in getattr(self, "entries", {}):
                try:
                    self.entries["passes"].text.blockSignals(True)
                    self.entries["passes"].setValues(show_passes)
                    self.entries["passes"].text.blockSignals(False)
                except Exception:
                    try:
                        self.entries["passes"].setValues(show_passes)
                    except Exception:
                        pass

            self._mark_dirty()
            if not quiet:
                self.status.showMessage(
                    f"Project ← {len(show_passes)} pass(es) from Pass Breakdown", 3500
                )
                QMessageBox.information(
                    self, "Synced",
                    f"Updated Showcase project with {len(show_passes)} pass(es).\n"
                    "Save (Ctrl+S) to write js/data.js.",
                )
            else:
                self.status.showMessage(
                    f"Project updated from Breakdown · {len(show_passes)} pass(es)", 2500
                )
        finally:
            self._sync_lock = False

    def _sync_project_to_breakdown(self):
        """Toolbar button — explicit sync with feedback."""
        self._commit_current()
        self._auto_sync_project_to_breakdown(quiet=False)
        self.main_tabs.setCurrentIndex(self._tab_index("Pass Breakdown"))

    def _sync_breakdown_to_project(self):
        """Toolbar button — explicit sync with feedback."""
        self._auto_sync_breakdown_to_project(quiet=False)



    def _save_project_viewer(self):
        """Write per-project viewer data and optionally open it."""
        if not getattr(self, "_rpb_editor", None):
            QMessageBox.warning(self, "Viewer", "Pass Breakdown editor is not loaded.")
            return
        try:
            self._auto_sync_breakdown_to_project(quiet=True)
        except Exception:
            pass
        key, title, bridge = self._current_project_key()
        passes = self._rpb_editor.get_passes_list()
        if not passes:
            QMessageBox.information(self, "Viewer", "No passes in Breakdown to save.")
            return
        path = bridge.write_viewer_data(key, title, passes)
        try:
            if hasattr(self._rpb_editor, "save"):
                self._rpb_editor.save()
        except Exception:
            pass
        url = bridge.viewer_url_for(key)
        self.status.showMessage(f"Project viewer saved: {path}", 5000)
        reply = QMessageBox.question(
            self, "Project viewer",
            f"Saved per-project breakdown:\n{path}\n\nOpen viewer now?",
        )
        if reply == QMessageBox.StandardButton.Yes and url:
            import webbrowser
            webbrowser.open(url)

    def _open_breakdown_viewer(self):
        """Open project-scoped viewer if available, else global viewer."""
        import webbrowser
        from pathlib import Path as _Path
        key, title, bridge = self._current_project_key()
        url = bridge.viewer_url_for(key)
        proj_data = _Path(BASE_DIR).resolve().parent / "viewer" / "projects" / key / "data.js"
        if proj_data.is_file() and url:
            webbrowser.open(url)
            return
        v = _Path(BASE_DIR).resolve().parent / "viewer" / "index.html"
        if v.is_file():
            webbrowser.open(v.resolve().as_uri())
        else:
            QMessageBox.warning(self, "Viewer", f"Not found:\n{v}")





    def _fill_vo_from_project(self):
        self._commit_current()
        if not self.projects:
            return
        p = self.projects[self.current_index]
        parts = []
        if p.get("title"):
            parts.append(str(p["title"]))
        if p.get("category"):
            parts.append(str(p["category"]))
        desc = p.get("description") or ""
        if isinstance(desc, str):
            import re
            desc = re.sub(r"<[^>]+>", " ", desc)
            desc = re.sub(r"\s+", " ", desc).strip()
            if len(desc) > 280:
                desc = desc[:277] + "…"
            if desc:
                parts.append(desc)
        details = p.get("details") or {}
        for k, v in details.items():
            if v:
                parts.append(f"{k}: {v}")
        passes = []
        for item in p.get("passes") or []:
            if isinstance(item, dict):
                passes.append(item.get("name") or "")
            else:
                passes.append(str(item).split("/")[-1])
        passes = [x for x in passes if x]
        if passes:
            parts.append("Render passes: " + ", ".join(passes))
        script = ". ".join(parts)
        if script and not script.endswith("."):
            script += "."
        if "vo_script" in self.entries:
            self.entries["vo_script"].setPlainText(script)
            self._mark_dirty()

    def _test_project_vo(self):
        """Speak current VO script using a female system voice when available."""
        text = ""
        if "vo_script" in getattr(self, "entries", {}):
            text = self.entries["vo_script"].toPlainText().strip()
        if not text:
            self._fill_vo_from_project()
            if "vo_script" in self.entries:
                text = self.entries["vo_script"].toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Voice-over", "No script to speak.")
            return
        # Optional OpenAI TTS if OPENAI_API_KEY is set
        try:
            from shared.tts_optional import synthesize_openai
            mp3 = synthesize_openai(text)
            if mp3 and mp3.is_file():
                import subprocess, sys
                if sys.platform.startswith("win"):
                    os.startfile(str(mp3))  # type: ignore
                else:
                    subprocess.Popen(["xdg-open", str(mp3)])
                self.status.showMessage("Played OpenAI TTS (cached)", 3000)
                return
        except Exception:
            pass
        try:
            import pyttsx3
            eng = pyttsx3.init()
            voices = eng.getProperty("voices") or []
            chosen = None
            for v in voices:
                name = (getattr(v, "name", "") or "") + " " + (getattr(v, "id", "") or "")
                if any(x in name.lower() for x in ("zira", "hazel", "susan", "female", "woman", "samantha")):
                    chosen = v.id
                    break
            if chosen:
                eng.setProperty("voice", chosen)
            eng.setProperty("rate", 165)
            eng.say(text)
            eng.runAndWait()
            self.status.showMessage("Spoke VO script (pyttsx3)", 3000)
            return
        except Exception:
            pass
        # Fallback: write temp HTML that speaks (opens browser)
        import tempfile, webbrowser
        from pathlib import Path as _P
        safe = text.replace("\\", "\\\\").replace("`", "'").replace("</", "<\\/")
        html = f"""<!DOCTYPE html><html><body>
<script>
const u = new SpeechSynthesisUtterance({json.dumps(text)});
u.rate = 0.95; u.pitch = 1.05;
function pick() {{
  const voices = speechSynthesis.getVoices();
  const prefer = [/zira/i,/hazel/i,/susan/i,/samantha/i,/female/i,/woman/i];
  for (const re of prefer) {{
    const v = voices.find(x => re.test(x.name));
    if (v) return v;
  }}
  return voices.find(x => (x.lang||'').startsWith('en')) || voices[0];
}}
function go() {{
  const v = pick(); if (v) u.voice = v;
  speechSynthesis.speak(u);
}}
speechSynthesis.onvoiceschanged = go;
setTimeout(go, 300);
</script>
<p>Speaking… you can close this tab.</p>
</body></html>"""
        tmp = _P(tempfile.gettempdir()) / "studio_vo_test.html"
        tmp.write_text(html, encoding="utf-8")
        webbrowser.open(tmp.resolve().as_uri())
        self.status.showMessage("Opened browser VO test", 3000)

    def publish_all_projects(self):
        if getattr(self, "_project_locked", False):
            QMessageBox.information(self, "Locked", "Unlock from View menu first.")
            return
        try:
            self._commit_current()
            self._auto_sync_breakdown_to_project(quiet=True)
            self.save_all()
        except Exception as e:
            QMessageBox.warning(self, "Publish All", f"Save failed:\n{e}")
            return
        n = 0
        try:
            from shared import project_bridge as bridge
            for i, proj in enumerate(self.projects):
                key = bridge.project_key(proj, i)
                title = proj.get("title") or key
                passes = bridge.showcase_passes_to_rpb(proj.get("passes") or [])
                if passes:
                    bridge.write_viewer_data(key, title, passes)
                    n += 1
        except Exception as e:
            QMessageBox.warning(self, "Publish All", f"Viewer write issue:\n{e}")
            return
        self.status.showMessage(f"Published viewers for {n} project(s)", 5000)
        QMessageBox.information(
            self, "Publish All",
            f"Saved data.js and wrote per-project viewers for {n} project(s) with passes.",
        )

    def export_client_package(self):
        """Zip showcase site + viewer for client (no Python editor)."""
        self._commit_current()
        dest, _ = QFileDialog.getSaveFileName(
            self, "Client package",
            os.path.join(BASE_DIR, "client-package.zip"),
            "Zip (*.zip)",
        )
        if not dest:
            return
        if not dest.endswith(".zip"):
            dest += ".zip"
        import zipfile
        from pathlib import Path as _P
        root = _P(BASE_DIR).resolve().parent
        showcase = _P(BASE_DIR)
        viewer = root / "viewer"
        skip_names = {"editor.py", "__pycache__", ".git"}
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for base, prefix in ((showcase, "showcase"), (viewer, "viewer")):
                if not base.is_dir():
                    continue
                for dirpath, dirs, files in os.walk(base):
                    dirs[:] = [d for d in dirs if d not in skip_names and not d.startswith(".")]
                    for fn in files:
                        if fn in skip_names or fn.endswith((".pyc", ".py")):
                            continue
                        full = os.path.join(dirpath, fn)
                        rel = os.path.relpath(full, base)
                        if "backups" in rel.replace("\\", "/").split("/"):
                            continue
                        zf.write(full, f"{prefix}/{rel}")
            # small readme
            zf.writestr(
                "README.txt",
                "Client package\n\n"
                "1. Open showcase/index.html in a browser\n"
                "2. Pass breakdown: viewer/index.html?project=project-01\n"
                "3. No Python required\n",
            )
        self.status.showMessage(f"Client package: {dest}", 6000)
        QMessageBox.information(self, "Client package", f"Created:\n{dest}")



    def _tab_index(self, name_substr: str) -> int:
        name_substr = (name_substr or "").strip().lower()
        for i in range(self.main_tabs.count()):
            if name_substr in self.main_tabs.tabText(i).strip().lower():
                return i
        return 0

    def _toast(self, msg: str, ms: int = 3500):
        try:
            self.status.showMessage(str(msg), ms)
        except Exception:
            pass
        try:
            if hasattr(self, "dash_status") and self.dash_status is not None:
                self.dash_status.setText(str(msg))
        except Exception:
            pass

    def _refresh_dashboard(self):
        try:
            n = len(self.projects or [])
            idx = getattr(self, "current_index", 0) + 1
            title = ""
            if self.projects and 0 <= self.current_index < len(self.projects):
                title = self.projects[self.current_index].get("title") or ""
            dirty = "● Unsaved changes" if getattr(self, "_dirty", False) else "All saved"
            locked = " · LOCKED" if getattr(self, "_project_locked", False) else ""
            if hasattr(self, "dash_status"):
                self.dash_status.setText(f"{dirty}{locked}  ·  Project {idx}/{n}  ·  {title}")
            lines = ["Recent projects:"]
            for i, p in enumerate(self.projects[:8]):
                mark = "→ " if i == self.current_index else "  "
                lines.append(f"{mark}{i+1:02d}  {p.get('title') or 'Untitled'}")
            if hasattr(self, "dash_recent"):
                self.dash_recent.setText("\n".join(lines))
        except Exception:
            pass

    def _collect_asset_issues(self):
        from pathlib import Path as _Path
        issues = []
        root = _Path(BASE_DIR)

        def check_path(label, rel):
            if not rel:
                return
            p = _Path(str(rel))
            candidates = [p, root / str(rel), root / str(rel).replace("\\\\", "/")]
            if not any(c.is_file() for c in candidates):
                issues.append(f"{label}: {rel}")

        for i, proj in enumerate(self.projects):
            title = proj.get("title") or f"Project {i+1}"
            prefix = f"[{i+1}] {title}"
            check_path(f"{prefix} / before", proj.get("before"))
            check_path(f"{prefix} / after", proj.get("after"))
            for j, item in enumerate(proj.get("passes") or []):
                if isinstance(item, dict):
                    src, name = item.get("src") or "", item.get("name") or f"pass {j+1}"
                else:
                    src, name = str(item), f"pass {j+1}"
                check_path(f"{prefix} / pass “{name}”", src)
        return issues


    # ----- Floating windows (second monitor) -----
    def undock_preview_window(self):
        """Open a floating preview window — drag to second monitor."""
        if getattr(self, "_float_preview", None) is not None:
            try:
                self._float_preview.show()
                self._float_preview.raise_()
                self._float_preview.activateWindow()
                return
            except Exception:
                self._float_preview = None

        win = QMainWindow(None)
        win.setWindowTitle("Studio Preview — drag to second monitor")
        win.resize(960, 540)
        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(8, 8, 8, 8)
        tip = QLabel("Live project preview · move this window to another screen · closes independently")
        tip.setObjectName("pageSubtitle")
        lay.addWidget(tip)
        try:
            prev = ScreenPreviewWidget()
            prev.set_mode("project")
            lay.addWidget(prev, 1)
            self._float_preview_widget = prev
            self._refresh_floating_preview()
        except Exception as e:
            lay.addWidget(QLabel(f"Preview unavailable: {e}"))
        bar = QHBoxLayout()
        b_ref = QPushButton("Refresh")
        b_ref.clicked.connect(self._refresh_floating_preview)
        b_proj = QPushButton("Open project page")
        b_proj.clicked.connect(self.run_current_project_html)
        b_show = QPushButton("Run Showcase")
        b_show.clicked.connect(self.run_showcase_html)
        bar.addWidget(b_ref)
        bar.addWidget(b_proj)
        bar.addWidget(b_show)
        bar.addStretch(1)
        lay.addLayout(bar)
        win.setCentralWidget(central)
        # Place on second screen if available
        try:
            app = QApplication.instance()
            screens = app.screens() if app else []
            if screens and len(screens) > 1:
                geo = screens[1].availableGeometry()
                win.move(geo.x() + 40, geo.y() + 40)
                win.resize(min(1200, geo.width() - 80), min(700, geo.height() - 80))
        except Exception:
            pass
        win.show()
        self._float_preview = win
        self._toast("Preview undocked — drag to second monitor")

    def _refresh_floating_preview(self):
        w = getattr(self, "_float_preview_widget", None)
        if w is None:
            return
        try:
            self._commit_current()
            p = self.projects[self.current_index] if self.projects else {}
            # ScreenPreviewWidget APIs vary — try common ones
            if hasattr(w, "set_project_data"):
                w.set_project_data(p)
            elif hasattr(w, "set_data"):
                w.set_data(project=p)
            elif hasattr(w, "update_preview"):
                w.update_preview(p)
            elif hasattr(w, "set_mode"):
                w.set_mode("project")
            w.update()
        except Exception:
            pass

    def undock_pass_breakdown(self):
        """Float the Pass Breakdown editor in its own window."""
        rpb = getattr(self, "_rpb_editor", None)
        if rpb is None:
            QMessageBox.information(self, "Undock", "Pass Breakdown is not loaded.")
            return
        if getattr(self, "_rpb_docked_parent", None) is None:
            # Remember original parent layout
            self._rpb_docked_parent = rpb.parent()
        try:
            rpb.setParent(None)
            rpb.setWindowFlags(Qt.WindowType.Window)
            rpb.setWindowTitle("Pass Breakdown — floating")
            rpb.resize(1280, 800)
            try:
                app = QApplication.instance()
                screens = app.screens() if app else []
                if screens and len(screens) > 1:
                    geo = screens[1].availableGeometry()
                    rpb.move(geo.x() + 20, geo.y() + 20)
            except Exception:
                pass
            rpb.show()
            rpb.raise_()
            self._rpb_floating = True
            self._toast("Pass Breakdown undocked")
        except Exception as e:
            QMessageBox.warning(self, "Undock", str(e))

    def redock_floating_windows(self):
        """Bring floating preview / breakdown back into the main window."""
        # Close float preview
        fp = getattr(self, "_float_preview", None)
        if fp is not None:
            try:
                fp.close()
            except Exception:
                pass
            self._float_preview = None
            self._float_preview_widget = None
        # Redock RPB
        rpb = getattr(self, "_rpb_editor", None)
        if rpb is not None and getattr(self, "_rpb_floating", False):
            try:
                parent = getattr(self, "_rpb_host_layout", None)
                rpb.setWindowFlags(Qt.WindowType.Widget)
                # Find Pass Breakdown tab page and re-add
                idx = self._tab_index("Pass Breakdown")
                page = self.main_tabs.widget(idx)
                if page is not None:
                    lay = page.layout()
                    if lay is not None:
                        rpb.setParent(page)
                        lay.addWidget(rpb, 1)
                rpb.show()
                self._rpb_floating = False
                try:
                    self._sync_rpb_theme()
                except Exception:
                    pass
            except Exception as e:
                QMessageBox.warning(self, "Redock", str(e))
        self._toast("Floating windows redocked")

    # ----- Asset relink / search -----
    def _asset_search_roots(self):
        from pathlib import Path as _P
        roots = [
            _P(BASE_DIR) / "assets",
            _P(BASE_DIR) / "assets" / "images",
            _P(BASE_DIR) / "assets" / "videos",
        ]
        # Per-project folders
        img = _P(BASE_DIR) / "assets" / "images"
        if img.is_dir():
            for sub in sorted(img.iterdir()):
                if sub.is_dir():
                    roots.append(sub)
        # Studio viewer / shared
        studio = _P(BASE_DIR).resolve().parent
        roots.extend([
            studio / "viewer" / "assets" / "passes",
            studio / "shared" / "passes",
        ])
        return [r for r in roots if r.is_dir()]

    def _build_asset_index(self):
        """Map lowercase filename and checksum -> absolute path."""
        from pathlib import Path as _P
        index = {}  # name -> path
        by_sum = {}  # checksum -> path
        exts = {".png", ".jpg", ".jpeg", ".webp", ".exr", ".tif", ".tiff", ".hdr", ".bmp", ".mp4", ".mov", ".webm"}
        for root in self._asset_search_roots():
            try:
                for dirpath, _dirs, files in os.walk(root):
                    for fn in files:
                        ext = os.path.splitext(fn)[1].lower()
                        if ext not in exts:
                            continue
                        full = str(_P(dirpath) / fn)
                        key = fn.lower()
                        if key not in index:
                            index[key] = full
                        cs = self._file_checksum(full)
                        if cs and cs not in by_sum:
                            by_sum[cs] = full
            except Exception:
                continue
        self._asset_checksum_index = by_sum
        return index

    def relink_missing_assets(self):
        """Search asset folders by filename + checksum; optional manual pick for leftovers."""
        self._commit_current()
        index = self._build_asset_index()
        by_sum = getattr(self, "_asset_checksum_index", {}) or {}
        if not index:
            QMessageBox.information(
                self, "Relink",
                "No images found under assets/ folders.\n"
                "Put files in assets/images/project-XX/ then try again.",
            )
            return

        fixed = []
        still_missing = []  # list of (label, old_path, setter_callback)

        def path_ok(path_str):
            from pathlib import Path as _P
            if not path_str:
                return True
            p = _P(str(path_str))
            return any(c.is_file() for c in (p, _P(BASE_DIR) / str(path_str)))

        def try_relink(label, path_str):
            if not path_str or path_ok(path_str):
                return path_str, False
            from pathlib import Path as _P
            p = _P(str(path_str))
            found = index.get(p.name.lower())
            if not found:
                # checksum match against original if still on disk somewhere was lost — try size-only via index values already hashed
                # If broken path file exists elsewhere under different name, user needs manual; checksum only works if we had stored checksums
                found = None
            if found:
                rel = self._to_showcase_rel(found)
                fixed.append(f"{label}: {p.name} → {rel}")
                return rel, True
            still_missing.append((label, path_str))
            return path_str, False

        for i, proj in enumerate(self.projects):
            title = proj.get("title") or f"Project {i+1}"
            pref = f"[{i+1}] {title}"
            b, ch = try_relink(f"{pref} before", proj.get("before") or "")
            if ch:
                proj["before"] = b
            a, ch = try_relink(f"{pref} after", proj.get("after") or "")
            if ch:
                proj["after"] = a
            new_passes = []
            for j, item in enumerate(proj.get("passes") or []):
                if isinstance(item, dict):
                    src = item.get("src") or ""
                    name = item.get("name") or f"pass {j+1}"
                    ns, ch = try_relink(f"{pref} pass {name}", src)
                    d = dict(item)
                    d["src"] = ns
                    new_passes.append(d)
                else:
                    ns, ch = try_relink(f"{pref} pass", str(item))
                    new_passes.append(ns)
            proj["passes"] = new_passes
            new_gal = []
            for j, item in enumerate(proj.get("gallery") or []):
                if isinstance(item, dict):
                    src = item.get("src") or ""
                    ns, ch = try_relink(f"{pref} gallery {j+1}", src)
                    d = dict(item)
                    d["src"] = ns
                    new_gal.append(d)
                else:
                    ns, ch = try_relink(f"{pref} gallery {j+1}", str(item))
                    new_gal.append(ns)
            proj["gallery"] = new_gal

        # Manual pick for leftovers
        if still_missing:
            reply = QMessageBox.question(
                self, "Manual relink",
                f"Auto-relinked {len(fixed)} path(s).\n"
                f"{len(still_missing)} still missing.\n\n"
                "Pick files manually one by one?",
            )
            if reply == QMessageBox.StandardButton.Yes:
                # Build mutable refs into project data
                remaining = []
                for label, old in still_missing:
                    path, ok = QFileDialog.getOpenFileName(
                        self, f"Locate: {label}",
                        os.path.join(BASE_DIR, "assets"),
                        "Images (*.png *.jpg *.jpeg *.webp *.exr *.tif *.tiff);;All (*.*)",
                    )
                    if not path:
                        remaining.append(f"{label}: {old}")
                        continue
                    rel = self._to_showcase_rel(path)
                    # Write back into matching project field
                    applied = False
                    for i, proj in enumerate(self.projects):
                        title = proj.get("title") or f"Project {i+1}"
                        pref = f"[{i+1}] {title}"
                        if label == f"{pref} before":
                            proj["before"] = rel
                            applied = True
                        elif label == f"{pref} after":
                            proj["after"] = rel
                            applied = True
                        else:
                            for j, item in enumerate(proj.get("passes") or []):
                                nm = item.get("name") if isinstance(item, dict) else ""
                                if label == f"{pref} pass {nm}" or label == f"{pref} pass":
                                    if isinstance(item, dict):
                                        item["src"] = rel
                                    else:
                                        proj["passes"][j] = rel
                                    applied = True
                            for j, item in enumerate(proj.get("gallery") or []):
                                if label == f"{pref} gallery {j+1}":
                                    if isinstance(item, dict):
                                        item["src"] = rel
                                    else:
                                        proj["gallery"][j] = rel
                                    applied = True
                    if applied:
                        fixed.append(f"{label}: manual → {rel}")
                    else:
                        remaining.append(f"{label}: {old}")
                still_missing = remaining

        try:
            self._load_project(self.current_index)
        except Exception:
            pass
        self._mark_dirty()

        msg = [f"Relinked {len(fixed)} path(s).", f"Still missing: {len(still_missing)}", ""]
        if fixed:
            msg.extend(fixed[:20])
            if len(fixed) > 20:
                msg.append(f"… +{len(fixed)-20} more")
        if still_missing:
            msg.append("")
            msg.append("Still missing:")
            for x in still_missing[:15]:
                msg.append(x if isinstance(x, str) else f"{x[0]}: {x[1]}")
        msg.append("")
        msg.append("Save (Ctrl+S) to keep changes.")
        QMessageBox.information(self, "Relink Missing Assets", "\n".join(msg))
        self._toast(f"Relinked {len(fixed)} · missing {len(still_missing)}")



    def toggle_watch_folder(self):
        """Poll current project asset folder for new images and offer import."""
        if getattr(self, "_watch_timer", None) is None:
            self._watch_timer = QTimer(self)
            self._watch_timer.setInterval(2500)
            self._watch_timer.timeout.connect(self._watch_folder_tick)
            self._watch_seen = set()
        on = not self._watch_timer.isActive()
        if on:
            folder = self._current_project_asset_dir()
            folder.mkdir(parents=True, exist_ok=True)
            self._watch_seen = self._list_media_names(folder)
            self._watch_timer.start()
            if hasattr(self, "act_watch"):
                self.act_watch.setChecked(True)
            self._toast(f"Watching {folder}")
            QMessageBox.information(
                self, "Folder watch",
                f"Watching for new images:\n{folder}\n\n"
                "Drop renders here; new files are offered for import into RENDER PASSES.",
            )
        else:
            self._watch_timer.stop()
            if hasattr(self, "act_watch"):
                self.act_watch.setChecked(False)
            self._toast("Folder watch off")

    def _current_project_asset_dir(self):
        from pathlib import Path as _P
        folder = f"project-{self.current_index + 1:02d}"
        return _P(BASE_DIR) / "assets" / "images" / folder

    def _list_media_names(self, folder):
        from pathlib import Path as _P
        names = set()
        if not folder.is_dir():
            return names
        for p in folder.iterdir():
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".exr", ".tif", ".tiff", ".hdr"}:
                names.add(p.name.lower())
        return names

    def _watch_folder_tick(self):
        folder = self._current_project_asset_dir()
        if not folder.is_dir():
            return
        now = self._list_media_names(folder)
        seen = getattr(self, "_watch_seen", set())
        new = sorted(now - seen)
        self._watch_seen = now
        if not new:
            return
        # Auto-add new files as passes
        try:
            self._commit_current()
            p = self.projects[self.current_index]
            passes = list(p.get("passes") or [])
            existing_src = set()
            for it in passes:
                if isinstance(it, dict):
                    existing_src.add((it.get("src") or "").replace("\\\\", "/").lower())
                else:
                    existing_src.add(str(it).replace("\\\\", "/").lower())
            added = []
            for name in new:
                rel = f"assets/images/project-{self.current_index + 1:02d}/{name}".replace("\\\\", "/")
                if rel.lower() in existing_src:
                    continue
                stem = Path(name).stem
                passes.append({"src": rel, "name": stem})
                added.append(name)
            if added:
                p["passes"] = passes
                try:
                    self._load_project(self.current_index)
                except Exception:
                    pass
                self._mark_dirty()
                self._toast(f"Watch: imported {len(added)} new file(s)")
        except Exception:
            pass

    def toggle_preview_dock(self):
        """Native QDockWidget preview panel."""
        dock = getattr(self, "_preview_dock", None)
        if dock is not None:
            dock.setVisible(not dock.isVisible())
            if dock.isVisible():
                dock.raise_()
            return
        dock = QDockWidget("Preview", self)
        dock.setObjectName("PreviewDock")
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
            | Qt.DockWidgetArea.TopDockWidgetArea
        )
        try:
            prev = ScreenPreviewWidget()
            prev.set_mode("project")
            dock.setWidget(prev)
            self._preview_dock_widget = prev
        except Exception as e:
            dock.setWidget(QLabel(f"Preview: {e}"))
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self._preview_dock = dock
        self._refresh_dock_preview()
        self._toast("Preview dock open — drag title bar to undock to another monitor")

    def _refresh_dock_preview(self):
        w = getattr(self, "_preview_dock_widget", None)
        if w is None:
            return
        try:
            self._commit_current()
            p = self.projects[self.current_index] if self.projects else {}
            if hasattr(w, "set_project_data"):
                w.set_project_data(p)
            elif hasattr(w, "set_mode"):
                w.set_mode("project")
            w.update()
        except Exception:
            pass

    def _window_layout_path(self):
        from pathlib import Path as _P
        return _P(BASE_DIR) / ".window_layout.json"

    def _save_window_layout(self):
        import json
        from pathlib import Path as _P
        data = {
            "geometry": bytes(self.saveGeometry().toHex()).decode("ascii"),
            "state": bytes(self.saveState().toHex()).decode("ascii"),
        }
        # floating windows
        fp = getattr(self, "_float_preview", None)
        if fp is not None:
            try:
                data["float_preview"] = {
                    "x": fp.x(), "y": fp.y(), "w": fp.width(), "h": fp.height(),
                }
            except Exception:
                pass
        rpb = getattr(self, "_rpb_editor", None)
        if rpb is not None and getattr(self, "_rpb_floating", False):
            try:
                data["float_rpb"] = {
                    "x": rpb.x(), "y": rpb.y(), "w": rpb.width(), "h": rpb.height(),
                }
            except Exception:
                pass
        try:
            self._window_layout_path().write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass

    def _restore_window_layout(self):
        import json
        from pathlib import Path as _P
        path = self._window_layout_path()
        if not path.is_file():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            from PySide6.QtCore import QByteArray
            if data.get("geometry"):
                self.restoreGeometry(QByteArray.fromHex(data["geometry"].encode("ascii")))
            if data.get("state"):
                self.restoreState(QByteArray.fromHex(data["state"].encode("ascii")))
        except Exception:
            pass


    def presenter_checklist(self):
        self._commit_current()
        issues = self._collect_asset_issues()
        checks = []
        checks.append(("Projects exist", bool(self.projects)))
        checks.append(("Current project has title", bool(self.projects and (self.projects[self.current_index].get("title") or "").strip())))
        p = self.projects[self.current_index] if self.projects else {}
        checks.append(("Has render passes", bool(p.get("passes"))))
        checks.append(("No missing assets", len(issues) == 0))
        checks.append(("Project locked for presenting", bool(getattr(self, "_project_locked", False))))
        vo = (p.get("vo_script") or "").strip()
        checks.append(("VO script filled (optional)", bool(vo)))

        lines = ["Presenter checklist", ""]
        for label, ok in checks:
            lines.append(("✔ " if ok else "✖ ") + label)
        if issues:
            lines.append("")
            lines.append(f"Missing assets: {len(issues)} (see Asset Health)")
        lines.append("")
        lines.append("Tips: F5 Run Showcase · F8 Publish · V voice-over · View→Lock Project")
        QMessageBox.information(self, "Presenter checklist", "\n".join(lines))
        self._toast("Checklist reviewed")

    def snapshot_version(self):
        """Timestamped backup of data.js before client send."""
        self._commit_current()
        try:
            self.save_all()
        except Exception:
            pass
        src = os.path.join(BASE_DIR, "js", "data.js")
        if not os.path.isfile(src):
            QMessageBox.warning(self, "Snapshot", "data.js not found")
            return
        bak_dir = os.path.join(BASE_DIR, "js", "snapshots")
        os.makedirs(bak_dir, exist_ok=True)
        import time
        stamp = time.strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(bak_dir, f"data_{stamp}.js")
        shutil.copy2(src, dest)
        self._toast(f"Snapshot saved: js/snapshots/{os.path.basename(dest)}")
        QMessageBox.information(self, "Snapshot", f"Saved version:\n{dest}")

    def apply_project_template(self):
        templates = {
            "Interior lighting": {
                "category": "INTERIOR / LIGHTING",
                "vo_script": "Interior lighting breakdown. We build from ambient occlusion and diffuse, then add specular and reflections, finishing on the beauty pass.",
                "shot": "Interior lighting",
            },
            "Car paint": {
                "category": "AUTOMOTIVE / LOOKDEV",
                "vo_script": "Car paint lookdev. We review base color, clearcoat and specular response, reflections, and the final beauty composite.",
                "shot": "Car paint",
            },
            "Character": {
                "category": "CHARACTER / LOOKDEV",
                "vo_script": "Character shading breakdown. Skin and subsurface, specular response, and final beauty.",
                "shot": "Character",
            },
        }
        name, ok = QInputDialog.getItem(
            self, "Project template", "Apply template to current project:",
            list(templates.keys()), 0, False,
        )
        if not ok or not name:
            return
        tpl = templates[name]
        self._commit_current()
        if not self.projects:
            return
        p = self.projects[self.current_index]
        p["category"] = tpl["category"]
        p["vo_script"] = tpl["vo_script"]
        if "category" in self.entries:
            self.entries["category"].setText(tpl["category"])
        if "vo_script" in self.entries:
            self.entries["vo_script"].setPlainText(tpl["vo_script"])
        # Apply shot preset to breakdown if loaded
        try:
            if getattr(self, "_rpb_editor", None):
                from shared.pass_naming import apply_shot_preset
                passes = self._rpb_editor.get_passes_list()
                if passes:
                    self._rpb_editor.load_passes_list(apply_shot_preset(passes, tpl["shot"]), title=p.get("title") or "")
        except Exception:
            pass
        self._mark_dirty()
        self._toast(f"Template applied: {name}")
        QMessageBox.information(self, "Template", f"Applied “{name}” to the current project.\nReview VO script and passes, then Save.")

    def startup_self_check_quiet(self):
        """Log package status to status bar without a dialog."""
        missing = []
        for mod in ("PySide6", "numpy", "PIL"):
            try:
                __import__(mod)
            except Exception:
                missing.append(mod)
        if missing:
            self._toast("Missing packages: " + ", ".join(missing) + " — run install_deps.bat")
        else:
            self._toast("Studio ready ✔")
        self._refresh_dashboard()

    def startup_self_check(self):
        lines = []
        import sys
        lines.append(f"Python: {sys.version.split()[0]}")
        lines.append(f"Executable: {sys.executable}")
        for mod in ("PySide6", "numpy", "PIL", "imageio"):
            try:
                m = __import__(mod)
                ver = getattr(m, "__version__", "ok")
                lines.append(f"✔ {mod} {ver}")
            except Exception as e:
                lines.append(f"✖ {mod} — {e}")
        # Writable?
        test = os.path.join(BASE_DIR, ".write_test")
        try:
            with open(test, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(test)
            lines.append("✔ Showcase folder writable")
        except Exception as e:
            lines.append(f"✖ Folder not writable — {e}")
        QMessageBox.information(self, "Self-check", "\n".join(lines))
        self._toast("Self-check complete")

    def maybe_show_tour(self):
        marker = os.path.join(BASE_DIR, ".studio_tour_done")
        if os.path.isfile(marker):
            return
        reply = QMessageBox.question(
            self, "Quick tour",
            "Take a 60-second tour of the Studio?\n\n"
            "Home → Projects → Passes → Pass Breakdown → Publish",
        )
        try:
            open(marker, "w", encoding="utf-8").write("1")
        except Exception:
            pass
        if reply != QMessageBox.StandardButton.Yes:
            return
        QMessageBox.information(
            self, "Tour",
            "1) Home — dashboard actions\n"
            "2) Projects — title, before/after, RENDER PASSES\n"
            "3) Pass Breakdown — blends, timing, VO soundtrack\n"
            "4) Publish (F8) — save + open project page\n"
            "5) Run Showcase (F5) — full site\n\n"
            "Tip: View → Lock Project while presenting.",
        )
        self.main_tabs.setCurrentIndex(0)


    def publish_project(self):
        """One-click: Save All + write project viewer + open project page."""
        if getattr(self, "_project_locked", False):
            QMessageBox.information(self, "Locked", "Project is locked for presenting. Unlock from View menu.")
            return
        try:
            self._commit_current()
            self._auto_sync_breakdown_to_project(quiet=True)
        except Exception:
            pass
        issues = []
        try:
            issues = self._collect_asset_issues()
        except Exception:
            issues = []
        critical = [x for x in issues if "/ pass" in x]
        if critical:
            detail = "\n".join(critical[:12])
            more = f"\n… +{len(critical)-12} more" if len(critical) > 12 else ""
            reply = QMessageBox.question(
                self, "Publish — missing images",
                f"{len(critical)} pass image path(s) look missing:\n\n{detail}{more}\n\nPublish anyway?",
            )
            if reply != QMessageBox.StandardButton.Yes:
                try:
                    self.asset_health_panel()
                except Exception:
                    pass
                return
        try:
            self.save_all()
            self._toast("Saved ✔")
        except Exception as e:
            QMessageBox.warning(self, "Publish", f"Save All failed:\n{e}")
            return
        try:
            if getattr(self, "_rpb_editor", None):
                key, title, bridge = self._current_project_key()
                passes = self._rpb_editor.get_passes_list()
                if passes:
                    bridge.write_viewer_data(key, title, passes)
        except Exception as e:
            self.status.showMessage(f"Viewer write skipped: {e}", 4000)
        self.run_current_project_html()
        self._toast("Published project — page opened")
        self.status.showMessage("Published project — page opened in browser", 5000)

    def asset_health_panel(self):
        """List missing/broken images for current (or all) projects."""
        self._commit_current()
        from pathlib import Path as _Path
        issues = []
        root = _Path(BASE_DIR)

        def check_path(label, rel):
            if not rel:
                return
            p = _Path(str(rel))
            candidates = [p, root / str(rel), root / str(rel).replace("\\", "/")]
            ok = any(c.is_file() for c in candidates)
            if not ok:
                issues.append(f"{label}: {rel}")

        for i, proj in enumerate(self.projects):
            title = proj.get("title") or f"Project {i+1}"
            prefix = f"[{i+1}] {title}"
            check_path(f"{prefix} / before", proj.get("before"))
            check_path(f"{prefix} / after", proj.get("after"))
            for j, item in enumerate(proj.get("passes") or []):
                if isinstance(item, dict):
                    src, name = item.get("src") or "", item.get("name") or f"pass {j+1}"
                else:
                    src, name = str(item), f"pass {j+1}"
                check_path(f"{prefix} / pass “{name}”", src)
            for j, item in enumerate(proj.get("gallery") or []):
                if isinstance(item, dict):
                    src = item.get("src") or ""
                else:
                    src = str(item)
                check_path(f"{prefix} / gallery[{j+1}]", src)

        if not issues:
            QMessageBox.information(self, "Asset Health", "All checked images look present. ✔")
            self.status.showMessage("Asset health OK", 3000)
            return
        text = "\n".join(f"• {x}" for x in issues[:60])
        extra = f"\n… and {len(issues)-60} more" if len(issues) > 60 else ""
        reply = QMessageBox.question(
            self, f"Asset Health — {len(issues)} issue(s)",
            text + extra + "\n\nSearch project asset folders and try to relink by filename?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        self.status.showMessage(f"{len(issues)} missing asset(s)", 5000)
        if reply == QMessageBox.StandardButton.Yes:
            self.relink_missing_assets()

    def toggle_project_lock(self):
        self._project_locked = not getattr(self, "_project_locked", False)
        if hasattr(self, "act_lock"):
            self.act_lock.setChecked(self._project_locked)
        self._apply_project_lock()
        state = "LOCKED (presenting)" if self._project_locked else "Unlocked"
        self.status.showMessage(state, 4000)

    def _apply_project_lock(self):
        locked = getattr(self, "_project_locked", False)
        # Disable destructive / edit actions when locked
        for name in (
            "save_action", "save_all_action", "delete_action",
        ):
            act = getattr(self, name, None)
            if act is not None:
                try:
                    act.setEnabled(not locked)
                except Exception:
                    pass
        try:
            if hasattr(self, "project_list"):
                self.project_list.setEnabled(not locked)
        except Exception:
            pass
        # Form fields
        try:
            for w in getattr(self, "entries", {}).values():
                if hasattr(w, "setReadOnly"):
                    w.setReadOnly(locked)
                elif hasattr(w, "setEnabled"):
                    w.setEnabled(not locked)
        except Exception:
            pass

    def run_showcase_html(self):
        """Open the final showcase website (index.html) in the default browser."""
        import webbrowser
        from pathlib import Path as _Path
        # Commit + optional save prompt is intentional: user sees latest data only if they saved.
        try:
            self._commit_current()
        except Exception:
            pass
        index = _Path(BASE_DIR) / "index.html"
        if not index.is_file():
            QMessageBox.warning(
                self, "Run Showcase",
                f"Showcase index not found:\n{index}\n\n"
                "Use Regen HTML or New Showcase if the site structure is missing.",
            )
            return
        uri = index.resolve().as_uri()
        webbrowser.open(uri)
        self.status.showMessage(f"Opened showcase: {index.name}", 4000)

    def run_current_project_html(self):
        """Open the current project's HTML page in the browser."""
        import webbrowser
        from pathlib import Path as _Path
        try:
            self._commit_current()
        except Exception:
            pass
        if not self.projects:
            QMessageBox.information(self, "Open Project", "No projects loaded.")
            return
        p = self.projects[self.current_index]
        fname = (p.get("file") or "").strip()
        if not fname:
            fname = f"project-{self.current_index + 1:02d}.html"
        path = _Path(BASE_DIR) / "projects" / fname
        if not path.is_file():
            QMessageBox.warning(
                self, "Open Project",
                f"Project page not found:\n{path}\n\n"
                "Try Regen HTML for this project first.",
            )
            return
        webbrowser.open(path.resolve().as_uri())
        self.status.showMessage(f"Opened project page: {fname}", 4000)



    def show_help_guide(self):
        self._show_help_dialog(
            "Studio Guide",
            """
<h2>Artist Showcase Studio</h2>
<p>One app for the <b>Showcase website</b> and <b>Pass Breakdown</b> viewer.</p>
<ol>
<li><b>Projects tab</b> — set title, before/after, render passes, gallery.</li>
<li><b>Pass Breakdown tab</b> — blends, timing, transitions. Data syncs with the project.</li>
<li><b>Publish (F8)</b> — Save All + write project viewer + open the project page.</li>
<li><b>Run Showcase (F5)</b> — open the full site in your browser.</li>
</ol>
<p><b>Pass images:</b> add under RENDER PASSES or in Pass Breakdown (drag-drop).
Paths are copied into <code>showcase/assets/images/project-XX/</code> on save.</p>
<p><b>Rename table:</b> optional cleanup only — you review every name (no forced Key Light).</p>
<p><b>Shot presets:</b> Interior / Car paint / Character blend packs.</p>
"""
        )

    def show_help_shortcuts(self):
        self._show_help_dialog(
            "Keyboard Shortcuts",
            """
<table cellpadding="6">
<tr><td><b>Ctrl+S</b></td><td>Save current project</td></tr>
<tr><td><b>Ctrl+Shift+S</b></td><td>Save All</td></tr>
<tr><td><b>F5</b></td><td>Run Showcase (index.html)</td></tr>
<tr><td><b>F6</b></td><td>Open current project page</td></tr>
<tr><td><b>F7</b></td><td>Open Pass Breakdown viewer</td></tr>
<tr><td><b>F8</b></td><td>Publish project</td></tr>
<tr><td><b>F9</b></td><td>Asset Health panel</td></tr>
<tr><td><b>F1</b></td><td>This guide</td></tr>
<tr><td><b>Ctrl+1…5</b></td><td>Jump tabs (Artist…Pass Breakdown)</td></tr>
</table>
<p><b>In the Viewer (browser)</b></p>
<table cellpadding="6">
<tr><td><b>Space</b></td><td>Play / pause</td></tr>
<tr><td><b>← →</b></td><td>Previous / next pass</td></tr>
<tr><td><b>V</b></td><td>Toggle voice-over (pass names)</td></tr>
<tr><td><b>M</b></td><td>Play / pause soundtrack</td></tr>
<tr><td><b>T</b></td><td>Light / dark theme</td></tr>
<tr><td><b>P</b></td><td>Presentation mode</td></tr>
<tr><td><b>F</b></td><td>Fullscreen</td></tr>
</table>
<p><b>On Showcase project pages</b> — <b>V</b> speaks project script · <b>Esc</b> stops.</p>
"""
        )

    def show_help_audio(self):
        self._show_help_dialog(
            "Voice-over & Soundtrack",
            """
<h3>Voice-over (spoken pass / page text)</h3>
<p>Uses the free <b>browser speech engine</b> (no API key). Prefers a <b>female voice</b> when available (e.g. Microsoft Zira / Hazel on Windows).</p>
<ol>
<li>Open the <b>Pass Breakdown viewer</b> (F7) or a project page (F6).</li>
<li>Click the <b>VO</b> button <i>or</i> press <b>V</b>.</li>
<li>Change passes — each pass name is spoken when VO is on.</li>
</ol>
<p>On Showcase pages, <b>V</b> reads title, description, details, and pass list.</p>
<p><i>Tip:</i> Some browsers only start speech after a click. Click VO once if V seems silent.</p><p><b>Optional HQ TTS:</b> set environment variable <code>OPENAI_API_KEY</code> — Test speak will prefer OpenAI audio with local cache under <code>shared/tts_cache/</code>.</p>

<h3>Soundtrack (background music)</h3>
<ol>
<li>Open the <b>Pass Breakdown</b> tab.</li>
<li>In presentation / extra settings find <b>Audio…</b> (soundtrack field).</li>
<li>Browse an <b>mp3 / wav</b> file.</li>
<li>Press <b>Save</b> in Pass Breakdown (writes viewer data).</li>
<li>Open Viewer → press <b>M</b> to play/pause the bed.</li>
</ol>
<p>Soundtrack is copied into <code>viewer/assets/</code> and stored in <code>SETTINGS.soundtrack</code>.</p>
"""
        )

    def show_help_about(self):
        self._show_help_dialog(
            "About Studio",
            """
<p><b>Artist Showcase Studio</b> — merged Showcase editor + Pass Breakdown.</p>
<p>Components: Showcase site · Pass Breakdown editor · Shared library · Viewer</p>
<p>Python · PySide6 · optional imageio / OpenEXR for EXR passes</p>
"""
        )

    def _show_help_dialog(self, title, html):
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(560, 480)
        lay = QVBoxLayout(dlg)
        view = QTextEdit()
        view.setReadOnly(True)
        view.setHtml(html)
        lay.addWidget(view, 1)
        close = QPushButton("Close")
        close.clicked.connect(dlg.accept)
        lay.addWidget(close)
        dlg.exec()


    def _session_path(self):
        from pathlib import Path as _P
        return _P(BASE_DIR) / ".studio_session.json"

    def _save_session(self):
        try:
            import json
            data = {
                "project_index": getattr(self, "current_index", 0),
                "tab_index": self.main_tabs.currentIndex() if hasattr(self, "main_tabs") else 3,
            }
            self._session_path().write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass

    def _restore_session(self):
        try:
            import json
            p = self._session_path()
            if not p.is_file():
                return
            data = json.loads(p.read_text(encoding="utf-8"))
            idx = int(data.get("project_index", 0))
            if 0 <= idx < len(self.projects):
                self._load_project(idx)
            tab = int(data.get("tab_index", 3))
            if hasattr(self, "main_tabs") and 0 <= tab < self.main_tabs.count():
                self.main_tabs.setCurrentIndex(tab)
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            self._save_session()
        except Exception:
            pass
        try:
            self._save_window_layout()
        except Exception:
            pass
        self._commit_current()
        try:
            if getattr(self, "_rpb_editor", None) is not None:
                self._rpb_editor.close()
        except Exception:
            pass
        reply = QMessageBox.question(
            self, "Quit",
            "Save changes to js/data.js before closing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Save:
            self.save_all()
            event.accept()
        elif reply == QMessageBox.StandardButton.Discard:
            event.accept()
        else:
            event.ignore()




def show_first_run_wizard(parent=None):
    """Simple first-run setup: artist name/role + optional first project title."""
    try:
        from shared.studio_bootstrap import needs_first_run_wizard, mark_initialized, detect_studio_root
    except Exception:
        return False
    showcase = Path(BASE_DIR)
    if not needs_first_run_wizard(showcase):
        return False

    dlg = QDialog(parent)
    dlg.setWindowTitle("Welcome — Studio Setup")
    dlg.setMinimumWidth(420)
    lay = QVBoxLayout(dlg)
    title = QLabel("Set up your Artist Showcase")
    title.setObjectName("pageTitle")
    lay.addWidget(title)
    lay.addWidget(QLabel(
        "This studio folder was prepared for first use.\n"
        "Enter your details to continue — you can change them later."
    ))
    form = QFormLayout()
    name_e = QLineEdit("Artist")
    role_e = QLineEdit("Look Development")
    proj_e = QLineEdit("Project 01")
    form.addRow("Artist name", name_e)
    form.addRow("Role", role_e)
    form.addRow("First project title", proj_e)
    lay.addLayout(form)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        mark_initialized(showcase)
        return False

    name = name_e.text().strip() or "Artist"
    role = role_e.text().strip() or "Look Development"
    ptitle = proj_e.text().strip() or "Project 01"

    # Apply into open editor if available
    if parent is not None and hasattr(parent, "artist"):
        parent.artist["name"] = name
        parent.artist["role"] = role
        if hasattr(parent, "artist_name_edit"):
            parent.artist_name_edit.setText(name)
        if hasattr(parent, "artist_role_edit"):
            parent.artist_role_edit.setText(role)
        if parent.projects:
            parent.projects[0]["title"] = ptitle
            try:
                parent._load_project(0)
            except Exception:
                pass
        try:
            parent.save_all()
        except Exception:
            pass
        try:
            parent.status.showMessage("Studio initialized — welcome, " + name, 5000)
        except Exception:
            pass
    mark_initialized(showcase)
    return True


# =========================================================
# Entry
# =========================================================

def run_cli(argv):
    """
    Headless utilities (no GUI):

      python editor.py --init [dir]     Create full project structure
      python editor.py --scaffold-force Overwrite HTML/CSS/JS shells (keep data.js)
      python editor.py --repair
      python editor.py --validate
      python editor.py --regenerate-html
      python editor.py --backup
      python editor.py --export out.json
      python editor.py --import in.json
    """
    if not argv:
        return False

    cmd = argv[0]
    try:
        if cmd == "--init":
            target = argv[1] if len(argv) >= 2 else "."
            target = os.path.abspath(target)
            os.makedirs(target, exist_ok=True)
            # Copy this editor into the new project if not already there
            dest_editor = os.path.join(target, "editor.py")
            src_editor = os.path.abspath(__file__)
            if os.path.abspath(target) != os.path.abspath(BASE_DIR) or not os.path.isfile(dest_editor):
                try:
                    if os.path.abspath(dest_editor) != src_editor:
                        shutil.copy2(src_editor, dest_editor)
                except OSError as e:
                    print("Note: could not copy editor.py:", e)
            created = scaffold_project(base=target, force=True, with_sample=True)
            print("Scaffolded project at:", target)
            for p in created:
                print(" ", p)
            print("Done. Run:  cd", target, "&& python editor.py")
            return True
        if cmd == "--scaffold-force":
            created = scaffold_project(base=BASE_DIR, force=True, with_sample=True)
            print("Force-scaffolded shells (data.js preserved if present):")
            for p in created:
                print(" ", p)
            return True
        if cmd == "--repair":
            artist, projects, thanks, home, end, font, header = load_data_js()
            save_data_js(artist, projects, thanks, home, end, font, header)
            print("Repaired & saved js/data.js")
            return True
        if cmd == "--validate":
            artist, projects, thanks, home, end, font, header = load_data_js()
            ensure_asset_folders(projects)
            issues = validate_project_assets(projects)
            if not issues:
                print("OK — no issues")
            else:
                print(f"{len(issues)} issue(s):")
                for x in issues:
                    print(" ", x)
                sys.exit(1)
            return True
        if cmd == "--regenerate-html":
            artist, projects, thanks, home, end, font, header = load_data_js()
            paths = regenerate_all_html(projects)
            print(f"Regenerated {len(paths)} page(s)")
            for p in paths:
                print(" ", p)
            return True
        if cmd == "--backup":
            bak = backup_data_js()
            print("Backup:", bak or "(no data.js)")
            return True
        if cmd == "--export" and len(argv) >= 2:
            artist, projects, thanks, home, end, font, header = load_data_js()
            export_json(artist, projects, argv[1])
            print("Exported", argv[1])
            return True
        if cmd == "--import" and len(argv) >= 2:
            artist, projects, thanks = import_json(argv[1])
            if thanks is None:
                thanks = {}
            backup_data_js()
            save_data_js(artist, projects, thanks, home, end, font, header)
            print("Imported & saved from", argv[1])
            return True
        if cmd in ("-h", "--help"):
            print(run_cli.__doc__)
            return True
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(2)
    return False


def main():
    if len(sys.argv) > 1 and run_cli(sys.argv[1:]):
        return

    if not HAS_QT:
        print(
            "PySide6 is not installed. CLI still works.\n"
            "  pip install PySide6\n"
            "  python editor.py --help",
            file=sys.stderr,
        )
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName("Artist Showcase Editor")
    # Use the native Windows UI font for cleaner, sharper text rendering.
    app.setFont(QFont("Segoe UI", 10))
    try:
        app.setStyle("Fusion")
    except Exception:
        pass

    # Studio-level bootstrap (viewer/editor/shared) then showcase shells
    try:
        studio_root = Path(BASE_DIR).resolve().parent
        try:
            from shared.studio_bootstrap import ensure_studio_tree
            made = ensure_studio_tree(root=studio_root, source_root=studio_root)
            if made:
                print("Studio bootstrap:", ", ".join(made[:12]), ("…" if len(made) > 12 else ""))
        except Exception as be:
            print("Studio bootstrap note:", be, file=sys.stderr)
        created = ensure_project_structure(BASE_DIR)
        if created:
            print("Created missing project files:", ", ".join(created))
    except Exception as e:
        print("Scaffold warning:", e, file=sys.stderr)

    win = EditorWindow()
    win.show()
    try:
        from PySide6.QtCore import QTimer
        def _after_show():
            try:
                show_first_run_wizard(win)
            except Exception:
                pass
            try:
                win.startup_self_check_quiet()
            except Exception:
                pass
            try:
                win._refresh_dashboard()
            except Exception:
                pass
            try:
                win.maybe_show_tour()
            except Exception:
                pass
            try:
                win._restore_window_layout()
            except Exception:
                pass
        QTimer.singleShot(250, _after_show)
    except Exception:
        try:
            show_first_run_wizard(win)
        except Exception:
            pass
    sys.exit(app.exec())


if __name__ == "__main__":
    main()