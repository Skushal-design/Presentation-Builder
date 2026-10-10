Artist Showcase 2026
====================

Open index.html in a browser (local server recommended).

Edit content (PyQt6 GUI):
  pip install PyQt6
  python editor.py

────────────────────────────────────────
Create a NEW project in ANY folder
────────────────────────────────────────

GUI:
  Toolbar → "New Showcase…" (Ctrl+Shift+N)
  1. Pick a parent folder
  2. Enter project name
  3. Full showcase + editor.py are created there
  4. Optionally open the new project in the editor

  Toolbar → "Open Showcase…" (Ctrl+Shift+O)
  Open an existing showcase folder anywhere on disk.

Command line:
  python editor.py --init ./my-new-showcase
  python editor.py --init "D:/Clients/Acme/show-2026"
  python editor.py --init "/Users/you/Projects/reel"

Creates:
  my-new-showcase/
    editor.py          ← edit content from here
    index.html
    thanks.html
    README.txt
    css/style.css
    js/data.js         ← your content (never overwritten if present)
    js/main.js
    js/project.js
    js/features.js
    projects/
    assets/images/
    assets/videos/

Then:
  cd my-new-showcase
  python editor.py

Repair shells (keep data.js):
  python editor.py --scaffold-force

Other CLI: --repair  --validate  --regenerate-html  --backup  --export  --import
