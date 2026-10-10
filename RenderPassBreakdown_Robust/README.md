# Render Pass Studio

## Run

```bat
install_deps.bat
run.bat
```

Or:

```bat
python studio.py
```

## First run / empty folder

```bat
python studio.py --init .
```

Creates missing `showcase/`, `viewer/`, `editor/`, `shared/` files without overwriting your `data.js`.

```bat
python studio.py --repair-tree
```

Only fills missing files.

## First-run wizard

On first launch, enter artist name, role, and first project title.

# Artist Showcase Studio (merged)

One Python editor with the **Showcase theme**, plus a **Pass Breakdown** tab.

## Install (once)

```bat
install_deps.bat
```

```
pip install -r requirements.txt
```

```
PySide6>=6.6
numpy>=1.26
Pillow>=10.0
imageio>=2.34
imageio-ffmpeg>=0.5.1
OpenEXR>=3.2
```

## Run

```bat
run.bat
```

or:

```bat
python showcase\editor.py
```

## Tabs (same theme)

| Tab | Content |
|-----|---------|
| **Artist** | Name / role |
| **Thanks** | Thanks slide |
| **Screens** | Home / end / font |
| **Projects** | Project list, before/after, passes, gallery |
| **Pass Breakdown** | Timeline, blends, transitions, viewer data |

## Viewer & site

- Pass Breakdown → **Open Viewer** (or top actions) → `viewer/index.html`
- Showcase site → open `showcase/index.html` in a browser after **Save All**

## Layout

```
RenderPassBreakdown_Robust/
  run.bat / install_deps.bat / requirements.txt
  showcase/
    editor.py          ← main merged editor (this theme)
    index.html, js/, css/, projects/
  editor/
    editor.py          ← pass breakdown UI (loaded as tab)
  viewer/              ← animated breakdown player
  shared/              ← shared pass library
```


## Power features (organized)

### Pass Breakdown tab
- **Drag & drop** images onto the pass list
- **Batch timing…** — set transition / pause / hold for all passes
- **Smart blends** — name-based multiply/add/screen
- **Pipeline sort** — typical lighting order (beauty last)
- **Project → Breakdown** — load current Showcase project passes
- **Breakdown → Project** — push stack back into Showcase
- **Save project viewer** — writes `viewer/projects/<id>/data.js`

### Showcase project pages
- BEFORE / AFTER · RENDER PASSES · PASS BREAKDOWN (embedded viewer iframe)
- Viewer supports `?project=project-01` for per-project data

### Shared library
- `shared/pass_library.json` + `shared/passes/`

## Studio power features (latest)

### Run / Publish
| Shortcut | Action |
|----------|--------|
| **F5** | Run Showcase site |
| **F6** | Open current project page |
| **F7** | Open Pass Breakdown viewer |
| **F8** | **Publish project** (Save All + project viewer + open page) |
| **F9** | Asset Health panel |

### Pass Breakdown
- **Rename table…** — optional suggestions only; you review each name (no forced “Key Light”)
- **Shot preset…** — Interior lighting / Car paint / Character / Environment packs
- **Batch timing**, Smart blends, Pipeline sort
- **Export MP4…** (existing)

### Voice / presenter
- Viewer: **V** toggle VO (reads pass name), **M** soundtrack if set in SETTINGS
- Showcase project page: **V** speaks title + description + details + pass list, **Esc** stops
- Viewer **P** presentation mode, **T** light/dark theme (light theme parity improved)

### Safety
- **View → Lock Project (presenting)** — blocks edits during a live show


## Windows executable (.exe)

On a Windows PC with Python installed **once** to build:

```bat
install_deps.bat
build_exe.bat
```

Output:

```
dist\RenderPassStudio\RenderPassStudio.exe
```

Ship the **whole** `dist\RenderPassStudio\` folder (not only the .exe).

- First run creates/fills project files next to the EXE  
- No Python needed on client machines after build  
- Folder size is large (~100–300 MB) because Qt is bundled  

Optional single-file build (slower startup):

```bat
build_exe_onefile.bat
```
