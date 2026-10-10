"""Optional pass rename suggestions — never forced; user reviews a table."""
from __future__ import annotations

import re
from pathlib import Path

# Strip render-engine noise only — do NOT invent creative names like "Key Light"
_PREFIX_RE = re.compile(
    r"^(?:vray|arnold|redshift|corona|octane|cycles|renderman|prman|mentalray)[_\.\- ]*",
    re.I,
)
_NOISE = re.compile(r"[_\.\-]+")
_MULTI_SPACE = re.compile(r"\s+")


def suggest_name(raw: str) -> str:
    """Conservative cleanup: strip engine prefix, separators → spaces, title-case.

    Does NOT map lights to Key/Fill/Rim — that needs human judgment.
    """
    if not raw:
        return "Pass"
    s = Path(str(raw)).stem if ("/" in str(raw) or "\\" in str(raw)) else str(raw)
    s = s.strip()
    # Drop leading single-letter channel markers like K. or R.
    s = re.sub(r"^[A-Za-z]\.", "", s)
    s = _PREFIX_RE.sub("", s)
    s = _NOISE.sub(" ", s)
    s = _MULTI_SPACE.sub(" ", s).strip()
    if not s:
        return Path(str(raw)).stem or "Pass"
    # Title case but keep short all-caps tokens (AO, GI, ID)
    parts = []
    for w in s.split(" "):
        if w.upper() in {"AO", "GI", "ID", "UV", "SSS", "RGB", "RGBA", "HDR", "EXR"}:
            parts.append(w.upper())
        elif re.fullmatch(r"\d+", w):
            parts.append(w)
        else:
            parts.append(w[:1].upper() + w[1:] if w else w)
    return " ".join(parts)


def build_rename_table(passes: list[dict]) -> list[dict]:
    """Return [{index, original, suggested, image}] for UI review."""
    rows = []
    for i, p in enumerate(passes or []):
        original = str(p.get("name") or Path(str(p.get("image") or "")).stem or f"Pass {i+1}")
        rows.append({
            "index": i,
            "original": original,
            "suggested": suggest_name(original),
            "image": p.get("image") or p.get("src") or "",
        })
    return rows


# Shot-type blend/transition packs (applied to matching names; others unchanged)
SHOT_PRESETS = {
    "Interior lighting": {
        "description": "Multiply AO/shadow · add lights · screen specular · fade beauty",
        "rules": [
            (("ao", "ambient", "shadow", "dirt", "cavity"), {"blend": "multiply", "transition": "wipe_rl"}),
            (("light", "gi", "illum", "diffuse", "lighting"), {"blend": "add", "transition": "wipe_angle"}),
            (("specular", "reflect", "gloss", "highlight"), {"blend": "screen", "transition": "soft_wipe_angle"}),
            (("beauty", "final", "rgb"), {"blend": "normal", "transition": "fade", "final": True}),
        ],
    },
    "Car paint": {
        "description": "Coat/specular screen · reflection add · AO multiply · beauty hold",
        "rules": [
            (("ao", "shadow", "dirt"), {"blend": "multiply", "transition": "wipe_rl"}),
            (("coat", "clearcoat", "specular", "gloss"), {"blend": "screen", "transition": "soft_wipe_angle"}),
            (("reflect", "env", "chrome"), {"blend": "add", "transition": "wipe_angle"}),
            (("beauty", "final"), {"blend": "normal", "transition": "fade", "final": True}),
        ],
    },
    "Character": {
        "description": "SSS soft · specular screen · AO multiply · beauty last",
        "rules": [
            (("ao", "cavity", "dirt"), {"blend": "multiply", "transition": "wipe_rl"}),
            (("sss", "subsurface", "skin"), {"blend": "screen", "transition": "fade"}),
            (("specular", "reflect", "gloss"), {"blend": "screen", "transition": "soft_wipe_angle"}),
            (("beauty", "final", "diffuse"), {"blend": "normal", "transition": "fade", "final": True}),
        ],
    },
    "Environment / Matte": {
        "description": "BG normal · fog screen · light add · beauty fade",
        "rules": [
            (("bg", "background", "matte", "plate"), {"blend": "normal", "transition": "fade"}),
            (("fog", "mist", "atmosphere", "volume"), {"blend": "screen", "transition": "fade"}),
            (("light", "sun", "sky", "gi"), {"blend": "add", "transition": "wipe_angle"}),
            (("beauty", "final"), {"blend": "normal", "transition": "fade", "final": True}),
        ],
    },
}


def apply_shot_preset(passes: list[dict], preset_name: str) -> list[dict]:
    preset = SHOT_PRESETS.get(preset_name)
    if not preset:
        return passes
    out = []
    for p in passes:
        q = dict(p)
        n = str(q.get("name") or "").lower()
        for keys, updates in preset["rules"]:
            if any(k in n for k in keys):
                q.update(updates)
                break
        out.append(q)
    return out
