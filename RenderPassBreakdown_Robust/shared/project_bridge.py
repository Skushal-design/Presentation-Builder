"""Per-project pass breakdown bridge between Showcase and Pass Breakdown viewer.

Paths written for the web always stay relative to the showcase or viewer root
so images load in the browser (never absolute disk paths).
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOWCASE = ROOT / "showcase"
VIEWER_PROJECTS = ROOT / "viewer" / "projects"
SHARED_PROJECTS = Path(__file__).resolve().parent / "projects"


def slugify(title: str, fallback: str = "project") -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (title or "").strip().lower()).strip("-")
    return s[:48] or fallback


def project_key(project: dict, index: int = 0) -> str:
    file_stem = Path(str(project.get("file") or f"project-{index + 1:02d}")).stem
    return slugify(file_stem, f"project-{index + 1:02d}")


def _ensure_dirs(key: str) -> tuple[Path, Path]:
    vdir = VIEWER_PROJECTS / key
    vdir.mkdir(parents=True, exist_ok=True)
    SHARED_PROJECTS.mkdir(parents=True, exist_ok=True)
    return vdir, SHARED_PROJECTS / f"{key}.json"


def _resolve_existing(path_str: str) -> Path | None:
    """Find a readable image file from absolute or relative path."""
    if not path_str:
        return None
    p = Path(path_str)
    candidates = [
        p,
        ROOT / path_str,
        SHOWCASE / path_str,
        ROOT / "viewer" / path_str,
        ROOT / "viewer" / "assets" / "passes" / p.name,
        ROOT / "shared" / "passes" / p.name,
    ]
    # strip leading ../
    cleaned = path_str.replace("\\", "/").lstrip("./")
    while cleaned.startswith("../"):
        cleaned = cleaned[3:]
    candidates.extend([
        ROOT / cleaned,
        SHOWCASE / cleaned,
        ROOT / "viewer" / cleaned,
    ])
    seen = set()
    for c in candidates:
        try:
            c = c.resolve()
        except Exception:
            continue
        if c in seen:
            continue
        seen.add(c)
        if c.is_file():
            return c
    return None


def _copy_into_showcase(src: Path, project_index: int) -> str:
    """Copy image into showcase/assets/images/project-XX/ and return web-relative path."""
    folder_name = f"project-{project_index + 1:02d}"
    dest_dir = SHOWCASE / "assets" / "images" / folder_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    try:
        if not dest.exists() or dest.stat().st_mtime < src.stat().st_mtime:
            shutil.copy2(src, dest)
    except Exception:
        # if copy fails, still return intended relative path
        pass
    return f"assets/images/{folder_name}/{src.name}".replace("\\", "/")


def showcase_passes_to_rpb(passes: list) -> list[dict]:
    """Convert Showcase {src,name} list → RPB pass dicts (resolved absolute for editor)."""
    out = []
    for i, item in enumerate(passes or []):
        if isinstance(item, str):
            src, name = item, Path(item).stem
        elif isinstance(item, dict):
            src = item.get("src") or item.get("image") or item.get("path") or ""
            name = item.get("name") or item.get("label") or Path(str(src)).stem or f"Pass {i + 1}"
        else:
            continue
        if not src:
            continue
        resolved = _resolve_existing(str(src))
        image = str(resolved) if resolved else str(src)
        out.append({
            "name": str(name),
            "image": image,
            "description": "",
            "slide_ms": 1000,
            "pause_ms": 600,
            "hold": 8.0,
            "final": i == len(passes) - 1,
            "blend": _guess_blend(str(name)),
            "transition": _guess_transition(str(name), i),
            "wipe_angle": 45.0,
            "hidden": False,
            "opacity": 100.0,
        })
    return out


def rpb_to_showcase_passes(passes: list[dict], project_index: int = 0) -> list[dict]:
    """Convert RPB passes → Showcase {src,name} with web-safe relative paths.

    Images are copied into showcase/assets/images/project-XX/.
    """
    out = []
    for p in passes or []:
        raw = p.get("image") or p.get("src") or ""
        name = p.get("name") or Path(str(raw)).stem or "Pass"
        resolved = _resolve_existing(str(raw))
        if resolved is not None:
            rel = _copy_into_showcase(resolved, project_index)
        else:
            # already a relative showcase path?
            s = str(raw).replace("\\", "/")
            if s.startswith("assets/"):
                rel = s
            elif "assets/images/" in s:
                rel = s[s.find("assets/images/") :]
            else:
                rel = s  # last resort — may still fail in browser
        out.append({"src": rel, "name": str(name)})
    return out


def _guess_blend(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ("ao", "ambient", "shadow", "dirt", "cavity")):
        return "multiply"
    if any(k in n for k in ("reflect", "specular", "gloss", "emission", "glow", "light", "gi", "illum")):
        return "add"
    if any(k in n for k in ("refraction", "sss", "coat", "sheen")):
        return "screen"
    return "normal"


def _guess_transition(name: str, index: int) -> str:
    n = name.lower()
    if "beauty" in n or "final" in n:
        return "fade"
    if any(k in n for k in ("ao", "shadow")):
        return "wipe_rl"
    if any(k in n for k in ("reflect", "refract")):
        return "soft_wipe_angle"
    return "wipe_angle" if index % 2 else "wipe_rl"


def write_viewer_data(key: str, title: str, passes: list[dict], settings: dict | None = None) -> Path:
    """Write viewer/projects/<key>/data.js and copy images into local assets."""
    vdir, cache = _ensure_dirs(key)
    assets = vdir / "assets"
    assets.mkdir(exist_ok=True)

    written_passes = []
    for i, p in enumerate(passes or []):
        item = dict(p)
        resolved = _resolve_existing(str(item.get("image") or ""))
        if resolved is not None:
            dest_name = f"{i + 1:02d}_{resolved.name}"
            dest = assets / dest_name
            try:
                if not dest.exists() or dest.stat().st_mtime < resolved.stat().st_mtime:
                    shutil.copy2(resolved, dest)
                item["image"] = f"projects/{key}/assets/{dest_name}"
            except Exception:
                item["image"] = str(resolved)
        written_passes.append(item)

    settings = settings or {
        "logo": "",
        "edge_show": True,
        "edge_color": "#ffffff",
        "edge_width": 2.0,
        "edge_glow": True,
        "show_topbar": True,
        "show_brand": True,
        "show_counter": True,
        "show_pass_name": True,
        "show_tags": True,
        "show_timeline": True,
        "show_hint": True,
        "show_caption": True,
    }

    js = (
        f"window.PROJECT_TITLE = {json.dumps(title or key)};\n"
        f"window.SETTINGS = {json.dumps(settings)};\n"
        f"window.PASSES = {json.dumps(written_passes, indent=2)};\n"
    )
    data_js = vdir / "data.js"
    data_js.write_text(js, encoding="utf-8")
    cache.write_text(json.dumps({"title": title, "passes": passes}, indent=2), encoding="utf-8")
    return data_js


def load_project_cache(key: str) -> list[dict]:
    _, cache = _ensure_dirs(key)
    if not cache.is_file():
        return []
    try:
        data = json.loads(cache.read_text(encoding="utf-8"))
        return list(data.get("passes") or [])
    except Exception:
        return []


def viewer_url_for(key: str) -> str:
    index = ROOT / "viewer" / "index.html"
    if not index.is_file():
        return ""
    return index.resolve().as_uri() + f"?project={key}"
