"""Bootstrap a complete Render Pass Studio tree in an empty or partial folder.

Never overwrites existing data.js or user project content.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

# Minimal viewer shells (used only when viewer/ files are missing)
MIN_VIEWER_HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Render Pass Breakdown</title>
<link rel="stylesheet" href="style.css">
</head><body>
<div class="app" id="app">
  <header class="topbar">
    <h1 id="projectTitle">Render Pass Breakdown</h1>
    <div class="controls">
      <button id="prev" type="button">‹</button>
      <button id="play" type="button">PLAY</button>
      <button id="next" type="button">›</button>
      <button id="voBtn" type="button">VO</button>
      <button id="theme" type="button">◐</button>
    </div>
  </header>
  <main class="stage-wrap"><div class="stage" id="stage">
    <img id="imgBase" alt=""><img id="imgOver" alt="">
    <div class="wipeEdge" id="wipeEdge" style="display:none"></div>
  </div></main>
  <div class="passBar"><span id="passName">—</span> <span id="counter">00 / 00</span></div>
  <div class="timeline" id="timeline"></div>
  <div class="hint">Space play · ← → · V voice · T theme</div>
</div>
<script>
(function(){
  var params=new URLSearchParams(location.search||"");
  var project=params.get("project");
  var dataSrc=project?("projects/"+encodeURIComponent(project)+"/data.js"):"data.js";
  var s=document.createElement("script");
  s.src=dataSrc;
  s.onerror=function(){var f=document.createElement("script");f.src="data.js";f.onload=function(){var a=document.createElement("script");a.src="app.js";document.body.appendChild(a);};document.body.appendChild(f);};
  s.onload=function(){var a=document.createElement("script");a.src="app.js";document.body.appendChild(a);};
  document.body.appendChild(s);
})();
</script>
</body></html>
"""

MIN_VIEWER_CSS = """*{box-sizing:border-box}body{margin:0;background:#0a0d12;color:#e8ecf1;font-family:Segoe UI,system-ui,sans-serif}
.app{min-height:100vh;display:flex;flex-direction:column}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:10px 16px;border-bottom:1px solid #2e3746}
.controls button{margin-left:6px;background:#161e2c;border:1px solid #4a5568;color:#e8ecf1;border-radius:6px;padding:6px 10px;cursor:pointer}
.stage-wrap{flex:1;display:flex;align-items:center;justify-content:center;padding:12px}
.stage{position:relative;width:min(1100px,96vw);aspect-ratio:16/9;background:#05070b;border:1px solid #3a4558;border-radius:8px;overflow:hidden}
.stage img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain}
.passBar,.hint{padding:8px 16px;color:#9aa3b2;font-size:13px}
.timeline{display:flex;gap:6px;padding:8px 16px;overflow:auto}
"""

MIN_VIEWER_APP = """const passes=(window.PASSES||[]).filter(p=>!p.hidden);
let index=0,playing=false,timer=null;
const $=id=>document.getElementById(id);
function imgSrc(p){return(p&&(p.image||p.after||p.before))||""}
function setInfo(i){
  const p=passes[i]; if(!p)return;
  if($("passName"))$("passName").textContent=p.name||("Pass "+(i+1));
  if($("counter"))$("counter").textContent=String(i+1).padStart(2,"0")+" / "+String(passes.length).padStart(2,"0");
  if($("projectTitle"))$("projectTitle").textContent=window.PROJECT_TITLE||"Render Pass Breakdown";
}
function show(i){
  if(!passes.length)return;
  index=(i+passes.length)%passes.length;
  const p=passes[index];
  const img=$("imgBase"); if(img)img.src=imgSrc(p);
  setInfo(index);
}
function play(){
  playing=!playing;
  if($("play"))$("play").textContent=playing?"PAUSE":"PLAY";
  clearTimeout(timer);
  if(!playing)return;
  const step=()=>{show(index+1);const p=passes[index];const ms=(p&&p.slide_ms)||1200;timer=setTimeout(step,ms);};
  timer=setTimeout(step,(passes[index]&&passes[index].slide_ms)||1200);
}
if($("prev"))$("prev").onclick=()=>show(index-1);
if($("next"))$("next").onclick=()=>show(index+1);
if($("play"))$("play").onclick=play;
if($("theme"))$("theme").onclick=()=>document.body.classList.toggle("light");
document.addEventListener("keydown",e=>{
  if(e.key==="ArrowRight")show(index+1);
  if(e.key==="ArrowLeft")show(index-1);
  if(e.key===" "){e.preventDefault();play();}
});
if($("projectTitle"))$("projectTitle").textContent=window.PROJECT_TITLE||"Render Pass Breakdown";
show(0);
"""

MIN_VIEWER_DATA = """window.PROJECT_TITLE = "New Pass Breakdown";
window.SETTINGS = {"edge_show": true, "edge_color": "#ffffff", "edge_width": 2};
window.PASSES = [];
"""

SHARED_LIBRARY_PY = '''"""Shared render-pass library."""
from __future__ import annotations
import json, hashlib, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
LIB_JSON = Path(__file__).resolve().parent / "pass_library.json"
LIB_ASSETS = Path(__file__).resolve().parent / "passes"

def _ensure():
    LIB_ASSETS.mkdir(parents=True, exist_ok=True)
    if not LIB_JSON.exists():
        LIB_JSON.write_text(json.dumps({"version": 1, "passes": []}, indent=2), encoding="utf-8")

def load():
    _ensure()
    try:
        data = json.loads(LIB_JSON.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {"version": 1, "passes": []}
        data.setdefault("passes", [])
        return data
    except Exception:
        return {"version": 1, "passes": []}

def save(data):
    _ensure()
    LIB_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def list_passes():
    return list(load().get("passes") or [])

def import_from_rpb_passes(passes):
    data = load()
    by_name = {str(p.get("name") or ""): p for p in data.get("passes") or []}
    for p in passes or []:
        name = str(p.get("name") or "Pass")
        by_name[name] = {"id": hashlib.md5(name.encode()).hexdigest()[:10], "name": name, "image": p.get("image") or "", "blend": p.get("blend") or "normal"}
    data["passes"] = list(by_name.values())
    save(data)
    return data["passes"]
'''


def _write_if_missing(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def _copy_if_missing(src: Path, dest: Path) -> bool:
    if dest.is_file():
        return False
    if not src.is_file():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


def detect_studio_root(start: Path | None = None) -> Path:
    """Resolve studio root (folder containing showcase/ or studio.py)."""
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        if (p / "showcase").is_dir() or (p / "studio.py").is_file():
            return p
        if (p / "editor" / "editor.py").is_file() and (p / "viewer").is_dir():
            return p
    return cur


def ensure_studio_tree(root: Path | None = None, source_root: Path | None = None) -> list[str]:
    """Create any missing studio folders/files. Returns list of created relative paths."""
    root = (root or detect_studio_root()).resolve()
    source_root = (source_root or root).resolve()
    created: list[str] = []

    # Folders
    for rel in (
        "showcase", "showcase/js", "showcase/css", "showcase/projects",
        "showcase/assets/images", "showcase/assets/videos",
        "viewer", "viewer/assets/passes", "viewer/projects",
        "editor", "shared", "shared/passes", "shared/projects",
    ):
        d = root / rel
        if not d.is_dir():
            d.mkdir(parents=True, exist_ok=True)
            created.append(rel + "/")

    # Shared package
    if _write_if_missing(root / "shared" / "__init__.py", "from . import library\n"):
        created.append("shared/__init__.py")
    if _write_if_missing(root / "shared" / "library.py", SHARED_LIBRARY_PY):
        created.append("shared/library.py")
    if _write_if_missing(root / "shared" / "pass_library.json", json.dumps({"version": 1, "passes": []}, indent=2)):
        created.append("shared/pass_library.json")

    # Copy project_bridge / pass_naming / tts if present in source
    for name in ("project_bridge.py", "pass_naming.py", "tts_optional.py", "studio_bootstrap.py"):
        src = source_root / "shared" / name
        dest = root / "shared" / name
        if _copy_if_missing(src, dest):
            created.append(f"shared/{name}")

    # Pass Breakdown editor — copy from source if missing
    ed_src = source_root / "editor" / "editor.py"
    ed_dest = root / "editor" / "editor.py"
    if _copy_if_missing(ed_src, ed_dest):
        created.append("editor/editor.py")
    if _write_if_missing(root / "editor" / "__init__.py", "# package\n"):
        created.append("editor/__init__.py")

    # Viewer — prefer copy full app from source; else minimal shells
    for name in ("index.html", "style.css", "app.js", "data.js"):
        src = source_root / "viewer" / name
        dest = root / "viewer" / name
        if src.is_file() and src.resolve() != dest.resolve():
            if _copy_if_missing(src, dest):
                created.append(f"viewer/{name}")
        elif not dest.is_file():
            content = {
                "index.html": MIN_VIEWER_HTML,
                "style.css": MIN_VIEWER_CSS,
                "app.js": MIN_VIEWER_APP,
                "data.js": MIN_VIEWER_DATA,
            }[name]
            dest.write_text(content, encoding="utf-8")
            created.append(f"viewer/{name}")

    # Showcase shell via showcase.editor scaffold when available
    showcase = root / "showcase"
    try:
        import importlib.util
        editor_path = showcase / "editor.py"
        # Prefer existing showcase editor from source
        src_editor = source_root / "showcase" / "editor.py"
        if src_editor.is_file() and not editor_path.is_file():
            shutil.copy2(src_editor, editor_path)
            created.append("showcase/editor.py")
        if editor_path.is_file():
            # Import scaffold from that file
            spec = importlib.util.spec_from_file_location("showcase_editor_boot", str(editor_path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                # Don't execute full GUI path — load module carefully
                # execute module (defines scaffold_project)
                spec.loader.exec_module(mod)
                if hasattr(mod, "ensure_project_structure"):
                    made = mod.ensure_project_structure(base=str(showcase))
                    for m in made or []:
                        created.append(f"showcase/{m}")
                elif hasattr(mod, "scaffold_project"):
                    made = mod.scaffold_project(base=str(showcase), force=False, with_sample=True)
                    for m in made or []:
                        created.append(f"showcase/{m}")
        else:
            # Minimal showcase index
            if _write_if_missing(showcase / "index.html", "<!DOCTYPE html><html><body><h1>Showcase</h1><p>Run studio to generate full site.</p></body></html>"):
                created.append("showcase/index.html")
            if _write_if_missing(showcase / "js" / "data.js", 'const ARTIST={name:"Artist",role:"Lookdev"};const PROJECTS=[];const PATHS={assetBase:""};\n'):
                created.append("showcase/js/data.js")
    except Exception as e:
        created.append(f"# showcase scaffold warning: {e}")

    # Copy showcase js/css assets from source if still missing
    for rel in (
        "showcase/css/style.css",
        "showcase/js/main.js",
        "showcase/js/project.js",
        "showcase/js/features.js",
        "showcase/index.html",
        "showcase/thanks.html",
    ):
        src = source_root / rel
        dest = root / rel
        if src.is_file() and src.resolve() != dest.resolve():
            if _copy_if_missing(src, dest):
                created.append(rel)

    # Launcher files
    run_bat = (
        "@echo off\ncd /d \"%~dp0\"\n"
        "python studio.py\n"
        "if errorlevel 1 (\n  echo.\n  echo Run install_deps.bat if modules are missing.\n  pause\n)\n"
    )
    if _write_if_missing(root / "run.bat", run_bat):
        created.append("run.bat")
    req = "PySide6>=6.6\nnumpy>=1.26\nPillow>=10.0\nimageio>=2.34\nimageio-ffmpeg>=0.5.1\nOpenEXR>=3.2\n"
    if _write_if_missing(root / "requirements.txt", req):
        created.append("requirements.txt")
    install = (
        "@echo off\ncd /d \"%~dp0\"\n"
        "python -m pip install --upgrade pip\n"
        "python -m pip install -r requirements.txt\n"
        "echo Done.\npause\n"
    )
    if _write_if_missing(root / "install_deps.bat", install):
        created.append("install_deps.bat")

    # First-run marker only if brand new (no data.js existed before)
    return created


def needs_first_run_wizard(showcase_dir: Path) -> bool:
    marker = showcase_dir / ".studio_initialized"
    if marker.is_file():
        return False
    data = showcase_dir / "js" / "data.js"
    if not data.is_file():
        return True
    try:
        text = data.read_text(encoding="utf-8")
        # Empty artist name → wizard
        if 'name": ""' in text or "name: \"\"" in text or '"name": "Artist"' in text:
            return True
        if "NEW PROJECT" in text and "Lookdev Artist" not in text:
            return True
    except Exception:
        return True
    return not marker.is_file()


def mark_initialized(showcase_dir: Path) -> None:
    try:
        (showcase_dir / ".studio_initialized").write_text("1\n", encoding="utf-8")
    except Exception:
        pass
