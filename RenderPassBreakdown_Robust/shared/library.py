"""Shared render-pass library used by Pass Breakdown editor and Showcase builder.

Load once → available everywhere → edit anywhere.
"""
from __future__ import annotations

import json
import shutil
import hashlib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LIB_JSON = Path(__file__).resolve().parent / "pass_library.json"
LIB_ASSETS = Path(__file__).resolve().parent / "passes"
VIEWER_ASSETS = ROOT / "viewer" / "assets" / "passes"
SHOWCASE_ROOT = ROOT / "showcase"


def _ensure():
    LIB_ASSETS.mkdir(parents=True, exist_ok=True)
    if not LIB_JSON.exists():
        LIB_JSON.write_text(json.dumps({"version": 1, "passes": []}, indent=2), encoding="utf-8")


def load() -> dict:
    _ensure()
    try:
        data = json.loads(LIB_JSON.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {"version": 1, "passes": []}
        data.setdefault("passes", [])
        return data
    except Exception:
        return {"version": 1, "passes": []}


def save(data: dict) -> None:
    _ensure()
    LIB_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def list_passes() -> list[dict]:
    return list(load().get("passes") or [])


def _copy_into_library(src: Path) -> str:
    """Copy image into shared/passes and return relative path shared/passes/name."""
    _ensure()
    src = Path(src)
    if not src.is_file():
        return ""
    # stable name: original stem + short hash to avoid collisions
    h = hashlib.md5(str(src.resolve()).encode("utf-8")).hexdigest()[:8]
    dest_name = f"{src.stem}_{h}{src.suffix.lower()}"
    dest = LIB_ASSETS / dest_name
    if not dest.exists():
        shutil.copy2(src, dest)
    return f"shared/passes/{dest_name}"


def upsert_pass(entry: dict, copy_asset: bool = True) -> dict:
    """Add or update a pass by name. Returns stored entry."""
    data = load()
    name = (entry.get("name") or "Pass").strip() or "Pass"
    image = entry.get("image") or entry.get("src") or ""
    stored_image = image
    if copy_asset and image:
        p = Path(image)
        if not p.is_file():
            # try relative to ROOT
            p2 = ROOT / image
            if p2.is_file():
                p = p2
        if p.is_file():
            stored_image = _copy_into_library(p)

    new_item = {
        "id": entry.get("id") or hashlib.md5(name.encode()).hexdigest()[:10],
        "name": name,
        "image": stored_image,
        "blend": entry.get("blend") or "normal",
        "transition": entry.get("transition") or "wipe_rl",
        "wipe_angle": float(entry.get("wipe_angle") or 180),
        "opacity": float(entry.get("opacity") if entry.get("opacity") is not None else 100),
        "slide_ms": int(entry.get("slide_ms") or 1200),
        "pause_ms": int(entry.get("pause_ms") or 800),
        "hold": float(entry.get("hold") or 10),
        "final": bool(entry.get("final", False)),
        "hidden": bool(entry.get("hidden", False)),
        "description": entry.get("description") or "",
    }

    passes = data["passes"]
    found = False
    for i, p in enumerate(passes):
        if p.get("name") == name or p.get("id") == new_item["id"]:
            # preserve id
            new_item["id"] = p.get("id") or new_item["id"]
            if not stored_image:
                new_item["image"] = p.get("image") or ""
            passes[i] = new_item
            found = True
            break
    if not found:
        passes.append(new_item)
    data["passes"] = passes
    save(data)
    return new_item


def import_from_rpb_passes(rpb_passes: list[dict]) -> int:
    """Register a list of RPB pass dicts into the library. Returns count."""
    n = 0
    for p in rpb_passes or []:
        upsert_pass(p, copy_asset=True)
        n += 1
    return n


def resolve_image(rel_or_abs: str) -> Path | None:
    if not rel_or_abs:
        return None
    p = Path(rel_or_abs)
    if p.is_file():
        return p
    for base in (ROOT, LIB_ASSETS, VIEWER_ASSETS, SHOWCASE_ROOT):
        cand = base / rel_or_abs
        if cand.is_file():
            return cand
        cand2 = base / Path(rel_or_abs).name
        if cand2.is_file():
            return cand2
    # shared/passes/foo
    if rel_or_abs.startswith("shared/"):
        cand = ROOT / rel_or_abs
        if cand.is_file():
            return cand
    return None


def export_to_rpb_format() -> list[dict]:
    """Return library passes in RPB viewer/editor format (paths relative for editor use)."""
    out = []
    for p in list_passes():
        img = p.get("image") or ""
        resolved = resolve_image(img)
        image_path = str(resolved) if resolved else img
        out.append({
            "name": p.get("name") or "Pass",
            "image": image_path,
            "description": p.get("description") or "",
            "slide_ms": int(p.get("slide_ms") or 1200),
            "pause_ms": int(p.get("pause_ms") or 800),
            "hold": float(p.get("hold") or 10),
            "final": bool(p.get("final", False)),
            "blend": p.get("blend") or "normal",
            "transition": p.get("transition") or "wipe_rl",
            "wipe_angle": float(p.get("wipe_angle") or 180),
            "hidden": bool(p.get("hidden", False)),
            "opacity": float(p.get("opacity") if p.get("opacity") is not None else 100),
        })
    return out


def export_to_showcase_format() -> list[dict]:
    """Showcase expects {src, name} list."""
    out = []
    for p in list_passes():
        img = p.get("image") or ""
        resolved = resolve_image(img)
        src = str(resolved) if resolved else img
        out.append({"src": src, "name": p.get("name") or "Pass"})
    return out


def remove_pass(name_or_id: str) -> bool:
    data = load()
    before = len(data["passes"])
    data["passes"] = [p for p in data["passes"] if p.get("name") != name_or_id and p.get("id") != name_or_id]
    save(data)
    return len(data["passes"]) < before
