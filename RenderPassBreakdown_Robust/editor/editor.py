import os, sys, json, shutil, webbrowser, subprocess, hashlib, re
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPixmap, QPainter, QPen, QBrush, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QScrollArea,
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QLineEdit, QTextEdit,
    QDoubleSpinBox, QFileDialog, QMessageBox, QFormLayout,
    QGroupBox, QSplitter, QCheckBox, QComboBox, QDialog, QInputDialog, QSizePolicy, QMenuBar, QWidgetAction,
    QDialogButtonBox, QSpinBox, QColorDialog, QGridLayout, QTableWidget, QTableWidgetItem, QMenu
)

BASE = Path(__file__).resolve().parent.parent
VIEWER = BASE / "viewer"
ASSETS = VIEWER / "assets" / "passes"
DATA = VIEWER / "data.js"

BLEND_MODES = [
    ("normal", "Normal"),
    ("add", "Add (Plus)"),
    ("screen", "Screen"),
    ("multiply", "Multiply"),
    ("overlay", "Overlay"),
    ("soft-light", "Soft Light"),
    ("hard-light", "Hard Light"),
    ("lighten", "Lighten"),
    ("darken", "Darken"),
    ("color-dodge", "Color Dodge"),
    ("color-burn", "Color Burn"),
    ("difference", "Difference"),
]

TRANSITIONS = [
    ("wipe_rl", "Linear Wipe → (R to L)"),
    ("wipe_lr", "Linear Wipe ← (L to R)"),
    ("wipe_angle", "Linear Wipe (angled)"),
    ("soft_wipe_rl", "Soft Wipe → (R to L)"),
    ("soft_wipe_lr", "Soft Wipe ← (L to R)"),
    ("soft_wipe_angle", "Soft Wipe (angled)"),
    ("fade", "Cross Fade"),
    ("slide_rl", "Slide → (R to L)"),
    ("slide_lr", "Slide ← (L to R)"),
    ("zoom_fade", "Zoom + Fade"),
]

DEFAULT_PASSES = [
    {"name": "Lighting", "image": "", "description": "Base lighting contribution.", "slide_ms": 1200, "pause_ms": 800, "hold": 10, "final": False, "blend": "normal", "transition": "wipe_rl", "wipe_angle": 180},
    {"name": "Global Illumination", "image": "", "description": "Indirect illumination added.", "slide_ms": 1200, "pause_ms": 800, "hold": 10, "final": False, "blend": "add", "transition": "wipe_angle", "wipe_angle": 135},
    {"name": "Reflection", "image": "", "description": "Reflection response added.", "slide_ms": 1200, "pause_ms": 800, "hold": 10, "final": False, "blend": "add", "transition": "soft_wipe_angle", "wipe_angle": 45},
    {"name": "Refraction", "image": "", "description": "Transparent / transmissive contribution.", "slide_ms": 1200, "pause_ms": 800, "hold": 10, "final": False, "blend": "add", "transition": "wipe_rl", "wipe_angle": 180},
    {"name": "Specular", "image": "", "description": "Specular highlights and glossy response.", "slide_ms": 1000, "pause_ms": 700, "hold": 10, "final": False, "blend": "screen", "transition": "fade", "wipe_angle": 180},
    {"name": "SSS", "image": "", "description": "Subsurface scattering contribution.", "slide_ms": 1200, "pause_ms": 800, "hold": 10, "final": False, "blend": "add", "transition": "soft_wipe_rl", "wipe_angle": 180},
    {"name": "Atmosphere", "image": "", "description": "Atmospheric and volumetric contribution.", "slide_ms": 1400, "pause_ms": 900, "hold": 10, "final": False, "blend": "screen", "transition": "zoom_fade", "wipe_angle": 180},
    {"name": "Background", "image": "", "description": "Background contribution.", "slide_ms": 1200, "pause_ms": 800, "hold": 10, "final": False, "blend": "normal", "transition": "slide_rl", "wipe_angle": 180},
    {"name": "Final RGB / Beauty", "image": "", "description": "Final combined render.", "slide_ms": 1200, "pause_ms": 800, "hold": 10, "final": True, "blend": "normal", "transition": "fade", "wipe_angle": 180},
]


HDR_EXTS = {".exr", ".hdr", ".tif", ".tiff"}


def _try_import(name: str):
    """Optional dependency loader (keeps Pylance quiet; missing packages are OK)."""
    try:
        import importlib
        return importlib.import_module(name)
    except Exception:
        return None



# ---------------------------------------------------------------------------
# Software-aware AOV / render-pass detection
# ---------------------------------------------------------------------------
# Canonical pipeline order (shared across DCC/renderers)
PIPELINE_ORDER = [
    "Lighting", "Diffuse", "Global Illumination", "Ambient Occlusion",
    "Reflection", "Refraction", "Specular", "SSS", "Self Illumination",
    "Caustics", "Shadow", "Atmosphere", "Background", "Normals", "Z-Depth",
    "Cryptomatte", "Final RGB / Beauty",
]

# Per-software filename / layer tokens → canonical name
SOFTWARE_AOV_MAP = {
    "generic": [
        (r"beauty|final.?rgb|rgba?(?![a-z])", "Final RGB / Beauty"),
        (r"global.?illum|\bgi\b|indirect", "Global Illumination"),
        (r"reflect", "Reflection"),
        (r"refract", "Refraction"),
        (r"specular|\bspec\b|glossy", "Specular"),
        (r"\bsss\b|subsurface|skin", "SSS"),
        (r"lighting|direct.?light|\blight\b", "Lighting"),
        (r"diffuse|albedo", "Diffuse"),
        (r"atmosphere|volume|fog|environ", "Atmosphere"),
        (r"background|back.?ground|\bbg\b", "Background"),
        (r"self.?illum|emission|emissive", "Self Illumination"),
        (r"shadow", "Shadow"),
        (r"\bao\b|ambient.?occ", "Ambient Occlusion"),
        (r"caustic", "Caustics"),
        (r"z.?depth|\bdepth\b|z.?buffer", "Z-Depth"),
        (r"normal", "Normals"),
        (r"crypto", "Cryptomatte"),
    ],
    "vray": [
        # Official beauty stack elements (3ds Max V-Ray)
        (r"vray.?lighting|(?<![a-z])lighting(?![a-z])|raw.?light|total.?light", "VRayLighting"),
        (r"vray.?global.?illum|global.?illum|\bvray.?gi\b|\bgi\b|raw.?gi", "VRayGlobalIllumination"),
        (r"vray.?reflect|raw.?reflect|reflect", "VRayReflection"),
        (r"vray.?refract|raw.?refract|refract", "VRayRefraction"),
        (r"vray.?specular|specular", "VRaySpecular"),
        (r"vray.?sss2|vray.?sss|\bsss2?\b|subsurface", "VRaySSS2"),
        (r"vray.?self.?illum|self.?illum", "VRaySelfIllumination"),
        (r"vray.?caustics?|caustic", "VRayCaustics"),
        (r"vray.?atmosphere|atmosphere", "VRayAtmosphere"),
        (r"vray.?background|\bbackground\b", "VRayBackground"),
        # Final plate (result of the sum — not added into the stack)
        (r"rgb.?color|vray.?rgb|beauty|final.?rgb|effects.?result", "Final RGB / Beauty"),
        # Other common elements (outside beauty formula)
        (r"vray.?diffuse|diffuse", "Diffuse"),
        (r"vray.?light.?select|light.?select|tube.?light|cone.?light|vraylight", "Light Select"),
        (r"\bao\b|vray.?ao|ambient.?occ|extra.?texture.*ao|dirt.?ao", "Ambient Occlusion"),
        (r"vray.?shadows?|shadow", "Shadow"),
        (r"vray.?bump.?normal|bump.?normal", "Normals"),
        (r"vray.?normals?|(?<![a-z])normals?(?![a-z])", "Normals"),
        (r"vray.?zdepth|zdepth|z.?depth", "Z-Depth"),
        (r"vray.?object.?id|object.?id|wire.?color|wirecolor", "Object ID"),
        (r"vray.?cryptomatte|cryptomatte|crypto", "Cryptomatte"),
        (r"vray.?denoiser|denoiser", "Denoiser"),
        (r"vray.?sample.?rate|sample.?rate", "Sample Rate"),
        (r"\benvironment\b", "VRayAtmosphere"),
        (r"\bglare\b|\balpha\b", "Utility"),
        (r"vr.?scans|scans.?zone", "Utility"),
    ],
    "arnold": [
        (r"RGBA|beauty|final", "Final RGB / Beauty"),
        (r"direct.?diffuse|diffuse.?direct|diffuse", "Diffuse"),
        (r"indirect.?diffuse|diffuse.?indirect|\bgi\b", "Global Illumination"),
        (r"direct.?specular|specular.?direct|specular", "Specular"),
        (r"indirect.?specular|specular.?indirect|reflect", "Reflection"),
        (r"subsurface|\bsss\b", "SSS"),
        (r"transmission|refract|specular.?transmission", "Refraction"),
        (r"emission|emissive|self.?illum", "Self Illumination"),
        (r"volume.?direct|volume.?indirect|atmosphere|volume", "Atmosphere"),
        (r"shadow", "Shadow"),
        (r"\bao\b|ambient.?occ|occlusion", "Ambient Occlusion"),
        (r"N\b|normal", "Normals"),
        (r"Z\b|z.?depth|depth", "Z-Depth"),
        (r"crypto", "Cryptomatte"),
        (r"sheen", "Sheen"),
        (r"coat", "Coat"),
        (r"sss.?direct|sss.?indirect", "SSS"),
    ],
    "blender": [
        (r"combined|beauty|final", "Final RGB / Beauty"),
        (r"diff.?dir|diffuse.?direct|diff.?color", "Diffuse"),
        (r"diff.?ind|diffuse.?indirect", "Global Illumination"),
        (r"gloss.?dir|glossy.?direct", "Specular"),
        (r"gloss.?ind|glossy.?indirect|reflect", "Reflection"),
        (r"trans.?dir|transmission|refract", "Refraction"),
        (r"subsurface|\bsss\b", "SSS"),
        (r"emit|emission", "Self Illumination"),
        (r"env|environment|world", "Background"),
        (r"\bao\b|ambient.?occ|occlusion", "Ambient Occlusion"),
        (r"normal", "Normals"),
        (r"depth|mist|z\b", "Z-Depth"),
        (r"volume.?dir|volume.?ind|volume", "Atmosphere"),
        (r"shadow", "Shadow"),
        (r"crypto", "Cryptomatte"),
        (r"index.?ob|object.?index", "Object Index"),
        (r"index.?ma|material.?index", "Material Index"),
    ],
    "unreal": [
        (r"final.?image|final.?color|lit|beauty|scene.?color", "Final RGB / Beauty"),
        (r"base.?color|diffuse|albedo", "Diffuse"),
        (r"ambient.?occlusion|\bao\b", "Ambient Occlusion"),
        (r"metallic", "Metallic"),
        (r"roughness|specular", "Specular"),
        (r"normal", "Normals"),
        (r"depth|scene.?depth", "Z-Depth"),
        (r"emissive|emission", "Self Illumination"),
        (r"indirect.?lighting|skylight|gi\b", "Global Illumination"),
        (r"reflection", "Reflection"),
        (r"refraction", "Refraction"),
        (r"sss|subsurface", "SSS"),
        (r"bloom", "Bloom"),
        (r"exposure", "Exposure"),
        (r"custom.?depth", "Custom Depth"),
        (r"world.?normal", "Normals"),
        (r"post.?process", "Post Process"),
    ],
}

SOFTWARE_LABELS = [
    ("generic", "Generic / Auto"),
    ("vray", "V-Ray"),
    ("arnold", "Arnold (Maya/C4D/Houdini)"),
    ("blender", "Blender Cycles/Eevee"),
    ("unreal", "Unreal Engine"),
]

def guess_pass_name(filename: str, software: str = "generic") -> str:
    stem = Path(filename).stem
    low = stem.lower().replace("-", "_").replace(" ", "_")
    # Try software-specific first, then generic
    maps = []
    if software and software != "generic":
        maps.append(SOFTWARE_AOV_MAP.get(software, []))
    maps.append(SOFTWARE_AOV_MAP["generic"])
    for patterns in maps:
        for pat, label in patterns:
            if re.search(pat, low, re.I):
                return label
    nice = re.sub(r"[_\.]+", " ", stem).strip()
    return nice.title() if nice else "Pass"

def pipeline_sort_key(name: str) -> tuple:
    try:
        return (PIPELINE_ORDER.index(name), name)
    except ValueError:
        return (len(PIPELINE_ORDER), name)

def smart_sort_passes(passes: list) -> list:
    """Sort passes into canonical lighting pipeline; Final Beauty last."""
    return sorted(passes, key=lambda p: pipeline_sort_key(p.get("name") or ""))

def detect_software_from_names(filenames: list) -> str:
    """Heuristic: which renderer the filenames look like."""
    joined = " ".join(Path(f).stem.lower() for f in filenames)
    scores = {k: 0 for k in SOFTWARE_AOV_MAP if k != "generic"}
    if re.search(r"vray|vr_", joined):
        scores["vray"] += 5
    if re.search(r"arnold|ai_|\brgba\b", joined):
        scores["arnold"] += 3
    if re.search(r"diff_dir|gloss_dir|combined|cycles", joined):
        scores["blender"] += 5
    if re.search(r"scene.?color|base.?color|unreal|ue5|buffer", joined):
        scores["unreal"] += 4
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "generic"





# ---------------------------------------------------------------------------
# Beauty rebuild presets (presentation order + blend hints)
# Roles: stack = additive beauty path, utility = technical, final = end plate
# ---------------------------------------------------------------------------
REBUILD_PRESETS = {
    "vray": {
        "label": "V-Ray (3ds Max)",
        "description": (
            "Official V-Ray beauty reconstruction:\n"
            "VRayLighting + VRayGlobalIllumination + VRayReflection + VRayRefraction +\n"
            "VRaySpecular + VRaySSS2 + VRaySelfIllumination + VRayCaustics +\n"
            "VRayAtmosphere [+ VRayBackground optional, Overwrite].\n"
            "Missing elements are skipped. Final RGB_color shown last as reference."
        ),
        # name → (order, blend, is_final, role)
        # blend "add" = Plus; Background uses normal (Overwrite)
        "roles": {
            "VRayLighting": (10, "add", False, "stack"),
            "VRayGlobalIllumination": (20, "add", False, "stack"),
            "VRayReflection": (30, "add", False, "stack"),
            "VRayRefraction": (40, "add", False, "stack"),
            "VRaySpecular": (50, "add", False, "stack"),
            "VRaySSS2": (60, "add", False, "stack"),
            "VRaySelfIllumination": (70, "add", False, "stack"),
            "VRayCaustics": (80, "add", False, "stack"),
            "VRayAtmosphere": (90, "add", False, "stack"),
            "VRayBackground": (100, "normal", False, "background"),  # optional overwrite
            # Aliases that may still appear from older naming
            "Lighting": (10, "add", False, "stack"),
            "Global Illumination": (20, "add", False, "stack"),
            "Reflection": (30, "add", False, "stack"),
            "Refraction": (40, "add", False, "stack"),
            "Specular": (50, "add", False, "stack"),
            "SSS": (60, "add", False, "stack"),
            "Self Illumination": (70, "add", False, "stack"),
            "Caustics": (80, "add", False, "stack"),
            "Atmosphere": (90, "add", False, "stack"),
            "Background": (100, "normal", False, "background"),
            "Final RGB / Beauty": (500, "normal", True, "final"),
            # Non-formula — drop by default
            "Diffuse": (15, "add", False, "drop"),
            "Light Select": (25, "add", False, "drop"),
            "Ambient Occlusion": (200, "multiply", False, "drop"),
            "Shadow": (210, "multiply", False, "drop"),
            "Denoiser": (220, "normal", False, "drop"),
            "Normals": (300, "normal", False, "drop"),
            "Z-Depth": (310, "normal", False, "drop"),
            "Object ID": (320, "normal", False, "drop"),
            "Cryptomatte": (330, "normal", False, "drop"),
            "Sample Rate": (340, "normal", False, "drop"),
            "Utility": (350, "normal", False, "drop"),
        },
        "always_drop": {
            "Object ID", "Cryptomatte", "Sample Rate", "Utility",
            "Diffuse", "Light Select", "Ambient Occlusion", "Shadow",
            "Denoiser", "Normals", "Z-Depth",
        },
        "drop_name_tokens": (
            "cryptomatte", "crypto", "objectid", "object_id", "wirecolor", "wire_color",
            "alpha", "vrscans", "scanszone", "samplerate", "sample_rate",
            "hierchy", "hierarchy", "bumpnormal", "bump_normal", "glare",
            "extra_texture", "dirt_ao", "lightselect", "tube_light", "cone_light",
        ),
    },
    "arnold": {
        "label": "Arnold",
        "description": "Arnold AOV stack toward beauty; drops IDs / crypto.",
        "roles": {
            "Diffuse": (10, "add", False, "stack"),
            "Lighting": (20, "add", False, "stack"),
            "Global Illumination": (30, "add", False, "stack"),
            "Specular": (40, "add", False, "stack"),
            "Reflection": (50, "add", False, "stack"),
            "Refraction": (60, "add", False, "stack"),
            "SSS": (70, "add", False, "stack"),
            "Self Illumination": (80, "add", False, "stack"),
            "Atmosphere": (90, "screen", False, "stack"),
            "Background": (100, "normal", False, "stack"),
            "Ambient Occlusion": (200, "multiply", False, "utility"),
            "Normals": (300, "normal", False, "utility"),
            "Z-Depth": (310, "normal", False, "utility"),
            "Cryptomatte": (320, "normal", False, "drop"),
            "Final RGB / Beauty": (500, "normal", True, "final"),
        },
        "always_drop": {"Cryptomatte"},
        "drop_name_tokens": ("crypto", "cryptomatte", "ncloseness", "z"),
    },
    "blender": {
        "label": "Blender Cycles",
        "description": "Cycles Diff/Gloss/Trans/Emit → Combined.",
        "roles": {
            "Diffuse": (10, "add", False, "stack"),
            "Lighting": (20, "add", False, "stack"),
            "Global Illumination": (30, "add", False, "stack"),
            "Specular": (40, "add", False, "stack"),
            "Reflection": (50, "add", False, "stack"),
            "Refraction": (60, "add", False, "stack"),
            "SSS": (70, "add", False, "stack"),
            "Self Illumination": (80, "add", False, "stack"),
            "Atmosphere": (90, "screen", False, "stack"),
            "Ambient Occlusion": (200, "multiply", False, "utility"),
            "Normals": (300, "normal", False, "utility"),
            "Z-Depth": (310, "normal", False, "utility"),
            "Final RGB / Beauty": (500, "normal", True, "final"),
        },
        "always_drop": set(),
        "drop_name_tokens": ("index", "vector", "uv"),
    },
    "unreal": {
        "label": "Unreal Engine",
        "description": "Unreal buffer stack toward scene color.",
        "roles": {
            "Diffuse": (10, "add", False, "stack"),
            "Lighting": (20, "add", False, "stack"),
            "Global Illumination": (30, "add", False, "stack"),
            "Reflection": (40, "add", False, "stack"),
            "Specular": (50, "screen", False, "stack"),
            "Self Illumination": (60, "add", False, "stack"),
            "Atmosphere": (70, "screen", False, "stack"),
            "Ambient Occlusion": (200, "multiply", False, "utility"),
            "Normals": (300, "normal", False, "utility"),
            "Z-Depth": (310, "normal", False, "utility"),
            "Final RGB / Beauty": (500, "normal", True, "final"),
        },
        "always_drop": set(),
        "drop_name_tokens": ("customdepth", "custom stencil"),
    },
}


def _classify_pass(p: dict, software: str, preset: dict):
    """Return (canonical_name, order, blend, is_final, role)."""
    roles = preset["roles"]
    img = p.get("image") or ""
    stem = Path(img).stem if img else (p.get("name") or "")
    detected = guess_pass_name(stem, software)
    cur = (p.get("name") or "").strip()
    if (not cur) or re.search(r"\.(png|exr|jpg|jpeg)$", cur, re.I) or re.match(r"^K[\._]", cur) \
            or "VRay" in cur or "vray" in cur.lower() or "VR" in cur:
        name = detected
    elif cur in roles:
        name = cur
    else:
        d2 = guess_pass_name(cur, software)
        name = d2 if d2 in roles else detected
    meta = roles.get(name)
    if meta is None:
        order, blend, is_final, role = (400, "normal", False, "utility")
    else:
        order, blend, is_final, role = meta
    return name, order, blend, is_final, role


def _should_drop(name: str, role: str, p: dict, preset: dict, include_utility: bool,
                 include_light_selects: bool, include_background: bool = False) -> str | None:
    """Return reason string if pass should be removed, else None."""
    always = preset.get("always_drop") or set()
    if name in always or role == "drop":
        return f"not in beauty formula ({name})"
    # VRayBackground is optional — only keep when explicitly enabled
    if role == "background" or name in ("VRayBackground", "Background"):
        if not include_background:
            return "optional background (disabled)"
    tokens = preset.get("drop_name_tokens") or ()
    blob = ((p.get("image") or "") + " " + (p.get("name") or "")).lower()
    blob_compact = blob.replace(" ", "").replace("-", "").replace(".", "")
    # Never drop official stack / final by token accident
    protect = {
        "Final RGB / Beauty",
        "VRayLighting", "VRayGlobalIllumination", "VRayReflection", "VRayRefraction",
        "VRaySpecular", "VRaySSS2", "VRaySelfIllumination", "VRayCaustics", "VRayAtmosphere",
        "VRayBackground",
        "Lighting", "Global Illumination", "Reflection", "Refraction", "Specular",
        "SSS", "Self Illumination", "Caustics", "Atmosphere", "Background",
    }
    if name not in protect:
        for tok in tokens:
            t = tok.lower().replace(" ", "")
            if t and (t in blob_compact or tok.lower() in blob):
                return f"filename token '{tok}'"
    if role == "utility" and not include_utility:
        return f"utility ({name})"
    if name == "Light Select" and not include_light_selects:
        return "light select"
    return None


def apply_rebuild_preset(
    passes: list,
    software: str,
    include_utility: bool = False,
    include_light_selects: bool = False,
    include_background: bool = False,
) -> tuple:
    """
    Automate beauty-rebuild list:
      • rename to canonical AOV labels
      • apply blend modes (add / screen / multiply / normal)
      • reorder stack → utility → final
      • remove unwanted technical passes
      • mark single Final RGB / Beauty
    Returns (new_passes, removed_list[{name,reason}], kept_summary)
    """
    software = (software or "vray").lower()
    if software not in REBUILD_PRESETS:
        software = "vray"
    preset = REBUILD_PRESETS[software]
    kept, removed = [], []

    for p in passes:
        p = dict(p)
        name, order, blend, is_final, role = _classify_pass(p, software, preset)
        p["name"] = name
        reason = _should_drop(
            name, role, p, preset, include_utility, include_light_selects, include_background
        )
        if reason:
            removed.append({"name": name, "image": p.get("image") or "", "reason": reason})
            continue
        p["blend"] = blend
        p["final"] = bool(is_final)
        # Timing defaults for presentation
        if is_final:
            p["transition"] = "fade"
            p["slide_ms"] = int(p.get("slide_ms") or 1200)
            p["pause_ms"] = int(p.get("pause_ms") or 800)
            p["hold"] = float(p.get("hold") or 12)
        elif role in ("stack", "background"):
            p["transition"] = p.get("transition") if p.get("transition") not in (None, "", "fade") else "wipe_angle"
            if p.get("wipe_angle") is None:
                p["wipe_angle"] = 45
            p["slide_ms"] = int(p.get("slide_ms") or 1000)
            p["pause_ms"] = int(p.get("pause_ms") or 600)
            if role == "background":
                p["blend"] = "normal"  # Overwrite, not add
        else:
            p["transition"] = p.get("transition") or "fade"
            p["slide_ms"] = int(p.get("slide_ms") or 900)
            p["pause_ms"] = int(p.get("pause_ms") or 500)
        p["_order"] = order
        p["_role"] = role
        kept.append(p)

    # One final only
    finals = [p for p in kept if p.get("final")]
    if len(finals) > 1:
        prefer = next(
            (p for p in finals if "beauty" in (p.get("name") or "").lower() or "rgb" in (p.get("name") or "").lower()),
            finals[-1],
        )
        for p in kept:
            p["final"] = p is prefer
            if p["final"]:
                p["blend"] = "normal"
                p["transition"] = "fade"
    elif not finals:
        for p in kept:
            if p.get("name") == "Final RGB / Beauty":
                p["final"] = True
                p["blend"] = "normal"
                break
        else:
            stacks = [p for p in kept if p.get("_role") == "stack"]
            if stacks:
                stacks[-1]["final"] = True
                stacks[-1]["blend"] = "normal"
                stacks[-1]["transition"] = "fade"

    kept.sort(key=lambda p: (p.get("_order", 999), p.get("name") or ""))
    for p in kept:
        p.pop("_order", None)
        p.pop("_role", None)

    summary = [f"{p.get('name')} [{p.get('blend')}]" + (" ★" if p.get("final") else "") for p in kept]
    return kept, removed, summary





# ---------------------------------------------------------------------------
# EXR / HDR conversion helpers (ImageMagick `magick` preferred on Windows)
# ---------------------------------------------------------------------------
def _which(cmd: str):
    """Locate an executable, with a bundled FFmpeg fallback.

    FFmpeg is installed through imageio-ffmpeg by install_deps.bat, so users
    do not need to manually edit Windows PATH just to export MP4.
    """
    from shutil import which
    found = which(cmd)
    if found:
        return found
    if str(cmd).lower() in {"ffmpeg", "ffmpeg.exe"}:
        try:
            import imageio_ffmpeg
            bundled = imageio_ffmpeg.get_ffmpeg_exe()
            if bundled and Path(bundled).exists():
                return bundled
        except Exception:
            pass
    return None


def _is_windows_fake_convert(path: str) -> bool:
    if not path:
        return False
    p = path.replace("/", "\\").lower()
    return p.endswith("\\system32\\convert.exe") or p.endswith("\\syswow64\\convert.exe")


def find_imagemagick():
    """Prefer ImageMagick 7 `magick`. Avoid Windows System32\\convert.exe."""
    magick = _which("magick")
    if magick:
        return {
            "kind": "magick",
            "bin": magick,
            "identify": [magick, "identify"],
            "convert_prefix": [magick],
        }
    convert = _which("convert")
    if convert and not _is_windows_fake_convert(convert):
        return {
            "kind": "convert",
            "bin": convert,
            "identify": [_which("identify") or "identify"],
            "convert_prefix": [convert],
        }
    identify = _which("identify")
    if identify and not _is_windows_fake_convert(identify):
        return {
            "kind": "identify-only",
            "bin": identify,
            "identify": [identify],
            "convert_prefix": None,
        }
    return {"kind": None, "bin": None, "identify": None, "convert_prefix": None}



def find_oiiotool():
    return _which("oiiotool")


def _exr_channel_groups(src: Path):
    """
    Group OpenEXR channels into pass-like names (VRayLighting.R/G/B → VRayLighting).
    Returns list of dicts: {name, channels:[...], size}
    """
    src = Path(src)
    try:
        OpenEXR = _try_import("OpenEXR")
        if OpenEXR is None:
            return []
        exr = OpenEXR.InputFile(str(src))
        header = exr.header()
        dw = header["dataWindow"]
        w = dw.max.x - dw.min.x + 1
        h = dw.max.y - dw.min.y + 1
        size = f"{w}x{h}"
        chans = list(header.get("channels", {}).keys())
        groups = {}
        for ch in chans:
            if "." in ch:
                prefix, suffix = ch.rsplit(".", 1)
            elif ch.upper() in ("R", "G", "B", "A", "X", "Y", "Z"):
                prefix, suffix = "RGB", ch.upper()
            else:
                prefix, suffix = ch, ""
            groups.setdefault(prefix, []).append(ch)
        out = []
        for name, clist in groups.items():
            out.append({"name": name, "channels": sorted(clist), "size": size})
        # Prefer stable beauty-ish order
        def rank(n):
            low = n.lower()
            for i, key in enumerate(
                ("rgb", "beauty", "rgba", "vraylighting", "lighting", "gi", "reflect", "refract",
                 "specular", "sss", "self", "caustic", "atmos", "background")
            ):
                if key in low:
                    return i
            return 50
        out.sort(key=lambda g: (rank(g["name"]), g["name"]))
        return out
    except Exception:
        return []


def _python_read_exr(src: Path, layer_index: int = 0, channel_group: str | None = None):
    """
    Read EXR via Python libs (handles multi-channel V-Ray EXRs ImageMagick cannot).
    channel_group: optional OpenEXR channel prefix (e.g. 'VRayReflection').
    Returns HxWx3 float array or None.
    """
    src_s = str(src)
    # 1) imageio (subimage index — not channel groups)
    if not channel_group:
        try:
            iio = _try_import("imageio.v3")
            np = _try_import("numpy")
            if iio is None or np is None:
                raise ImportError("imageio/numpy not installed")
            arr = iio.imread(src_s, index=layer_index)
            arr = np.asarray(arr)
            if arr.ndim == 2:
                arr = np.stack([arr, arr, arr], axis=-1)
            if arr.shape[-1] > 3:
                arr = arr[..., :3]
            return arr.astype("float32")
        except Exception:
            pass
    # 2) OpenEXR + numpy
    try:
        OpenEXR = _try_import("OpenEXR")
        Imath = _try_import("Imath")
        np = _try_import("numpy")
        if OpenEXR is None or np is None:
            raise ImportError("OpenEXR/numpy not installed")
        if Imath is None:
            Imath = _try_import("Imath")
        exr = OpenEXR.InputFile(src_s)
        header = exr.header()
        dw = header["dataWindow"]
        w = dw.max.x - dw.min.x + 1
        h = dw.max.y - dw.min.y + 1
        channels = list(header["channels"].keys())
        pt = Imath.PixelType(Imath.PixelType.FLOAT) if Imath is not None else None

        def pick(names):
            for n in names:
                if n in channels:
                    return n
            return None

        r_ch = g_ch = b_ch = None
        if channel_group:
            # Match prefix.R / prefix.G / prefix.B or exact group channels
            cand = [c for c in channels if c == channel_group or c.startswith(channel_group + ".")]
            def pick_suffix(suffixes):
                for s in suffixes:
                    for c in cand:
                        if c.upper().endswith("." + s) or c.upper() == s or c.upper().endswith(s):
                            return c
                return cand[0] if cand else None
            r_ch = pick_suffix(["R", "X"])
            g_ch = pick_suffix(["G", "Y"])
            b_ch = pick_suffix(["B", "Z"])
            if r_ch and not g_ch and not b_ch:
                # single channel → gray
                mono = np.frombuffer(exr.channel(r_ch, pt), dtype=np.float32).reshape(h, w)
                return np.stack([mono, mono, mono], axis=-1)
        if not (r_ch and g_ch and b_ch):
            r_ch = pick(["R", "r", "RGB.R", "rgba.R", "Beauty.R"])
            g_ch = pick(["G", "g", "RGB.G", "rgba.G", "Beauty.G"])
            b_ch = pick(["B", "b", "RGB.B", "rgba.B", "Beauty.B"])
        if not (r_ch and g_ch and b_ch):
            rgb = channels[:3]
            if len(rgb) < 3:
                return None
            r_ch, g_ch, b_ch = rgb[0], rgb[1], rgb[2]
        r = np.frombuffer(exr.channel(r_ch, pt), dtype=np.float32).reshape(h, w)
        g = np.frombuffer(exr.channel(g_ch, pt), dtype=np.float32).reshape(h, w)
        b = np.frombuffer(exr.channel(b_ch, pt), dtype=np.float32).reshape(h, w)
        return np.stack([r, g, b], axis=-1)
    except Exception:
        pass
    return None


def _float_rgb_to_png(arr, dst: Path) -> bool:
    """Tone-map float RGB to 8-bit PNG."""
    try:
        np = _try_import("numpy")
        Image_mod = _try_import("PIL.Image")
        if np is None or Image_mod is None:
            return False
        Image = Image_mod
        a = np.asarray(arr, dtype=np.float32)
        if a.ndim == 2:
            a = np.stack([a, a, a], axis=-1)
        a = a[..., :3]
        # simple display map: clamp after exposure-ish gamma
        a = np.nan_to_num(a, nan=0.0, posinf=1.0, neginf=0.0)
        # auto-expose: use 99th percentile
        finite = a[np.isfinite(a)]
        if finite.size:
            p = float(np.percentile(np.abs(finite), 99)) or 1.0
            a = a / p
        a = np.clip(a, 0.0, 1.0)
        a = np.power(a, 1.0 / 2.2)  # approx gamma
        img = (a * 255.0).astype("uint8")
        Image.fromarray(img, mode="RGB").save(str(dst), format="PNG")
        return dst.exists() and dst.stat().st_size > 0
    except Exception as e:
        print("PNG write failed:", e)
        return False


def list_exr_layers(src: Path):
    """
    Discover subimages / channel groups in EXR (or multipage TIFF).
    Returns list of dicts: {index, label, size, group?}
    group = OpenEXR channel prefix when applicable.
    """
    src = Path(src).resolve()
    layers = []
    im = find_imagemagick()
    oiio = find_oiiotool()

    # Multi-channel single-part EXR (typical V-Ray): list channel groups as passes
    groups = _exr_channel_groups(src)
    if len(groups) > 1:
        for i, g in enumerate(groups):
            layers.append({
                "index": i,
                "label": g["name"],
                "size": g.get("size", "?"),
                "group": g["name"],
                "channels": g.get("channels") or [],
            })
        return layers

    # Prefer oiiotool for multi-channel V-Ray EXRs (ImageMagick often fails)
    if oiio:
        r = subprocess.run([oiio, "--info", "-v", str(src)], capture_output=True, text=True)
        if r.returncode == 0:
            text_out = r.stdout or ""
            found = re.findall(r"subimage\s+(\d+).*?(?:name\s*=\s*\"([^\"]+)\")?", text_out, re.I)
            if found:
                for idx_s, name in found:
                    idx = int(idx_s)
                    label = f"Layer {idx}" + (f" — {name}" if name else "")
                    layers.append({"index": idx, "label": label, "size": "?"})
                if layers:
                    return layers
            # channel list as single beauty
            if re.search(r"channel list:", text_out, re.I):
                return [{"index": 0, "label": "Beauty / default (multi-channel EXR)", "size": "?"}]

    if im["identify"]:
        r = subprocess.run(im["identify"] + [str(src)], capture_output=True, text=True)
        err = (r.stderr or "") + (r.stdout or "")
        if r.returncode == 0 and r.stdout.strip() and "maximum channels exceeded" not in err:
            lines = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
            for i, ln in enumerate(lines):
                m = re.search(r"\[(\d+)\]", ln)
                idx = int(m.group(1)) if m else i
                sm = re.search(r"\b(\d+x\d+)\b", ln)
                size = sm.group(1) if sm else "?"
                layers.append({"index": idx, "label": f"Layer {idx}", "size": size})
            if layers:
                seen, uniq = set(), []
                for L in layers:
                    if L["index"] not in seen:
                        seen.add(L["index"])
                        uniq.append(L)
                return uniq

    # Python OpenEXR — channel names as pseudo info
    try:
        OpenEXR = _try_import("OpenEXR")
        if OpenEXR is None:
            return []
        exr = OpenEXR.InputFile(str(src))
        chans = list(exr.header().get("channels", {}).keys())
        if chans:
            return [{"index": 0, "label": f"Default ({len(chans)} channels)", "size": "?"}]
    except Exception:
        pass

    # Single layer fallback (import can still use Python/oiiotool)
    return [{"index": 0, "label": "Layer 0 (default)", "size": "?"}]


def convert_layer_to_web(src: Path, dst: Path, layer_index: int = 0, channel_group: str | None = None) -> None:
    """Convert EXR/HDR/TIFF (optional subimage or channel group) to PNG preview."""
    src = Path(src).resolve()
    dst = Path(dst)
    ext = src.suffix.lower()
    src_spec = f"{src}[{int(layer_index)}]" if ext in (".exr", ".hdr", ".tif", ".tiff") else str(src)

    if ext not in (".exr", ".hdr", ".tif", ".tiff"):
        shutil.copy2(src, dst)
        return

    if dst.exists():
        try:
            dst.unlink()
        except Exception:
            pass

    im = find_imagemagick()
    oiio = find_oiiotool()
    attempts = []
    errors = []

    # --- 1) oiiotool FIRST (handles multi-channel V-Ray EXR) ---
    if oiio and ext in (".exr", ".hdr", ".tif", ".tiff"):
        attempts.append([
            oiio, str(src), "--subimage", str(int(layer_index)),
            "--ch", "R,G,B", "--iscolorspace", "lin_srgb", "--tocolorspace", "srgb",
            "-o", str(dst),
        ])
        attempts.append([
            oiio, str(src), "--subimage", str(int(layer_index)),
            "--ch", "R,G,B", "-o", str(dst),
        ])
        attempts.append([oiio, str(src), "--subimage", str(int(layer_index)), "-o", str(dst)])
        attempts.append([oiio, str(src), "-o", str(dst)])

    # --- 2) Python imageio / OpenEXR (no external limit on channels) ---
    if ext in (".exr", ".hdr"):
        try:
            arr = _python_read_exr(src, layer_index, channel_group=channel_group)
            if arr is not None and _float_rgb_to_png(arr, dst):
                return
            errors.append((0, "Python EXR read returned no image", "python-exr"))
        except Exception as e:
            errors.append((-1, str(e)[:300], "python-exr"))

    # --- 3) ImageMagick (fails on many V-Ray multi-channel EXRs) ---
    if im["convert_prefix"]:
        prefix = im["convert_prefix"]
        if ext in (".exr", ".hdr"):
            attempts.extend([
                prefix + [src_spec, "-channel", "RGB", "-colorspace", "sRGB", "-depth", "8", str(dst)],
                prefix + [src_spec, "-auto-level", "-gamma", "2.2", "-depth", "8", str(dst)],
                prefix + [src_spec, "-depth", "8", str(dst)],
                prefix + [str(src), "-depth", "8", str(dst)],
            ])
        else:
            attempts.extend([
                prefix + [src_spec, "-depth", "8", str(dst)],
                prefix + [str(src), "-depth", "8", str(dst)],
            ])

    if not attempts and not errors:
        raise RuntimeError(
            "No EXR converter found.\n\n"
            "For multi-channel V-Ray EXRs, ImageMagick often fails with\n"
            "'maximum channels exceeded'. Install one of:\n\n"
            "  1) OpenImageIO  →  oiiotool  (recommended)\n"
            "  2) pip install imageio numpy Pillow\n"
            "  3) pip install OpenEXR numpy Pillow\n\n"
            "Or export PNG render elements from 3ds Max instead of one huge EXR."
        )

    for cmd in attempts:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        except FileNotFoundError as e:
            errors.append((-1, str(e), " ".join(cmd[:3])))
            continue
        except subprocess.TimeoutExpired:
            errors.append((-1, "timeout", " ".join(cmd[:3])))
            continue
        if r.returncode == 0 and dst.exists() and dst.stat().st_size > 0:
            return
        err = (r.stderr or r.stdout or "").strip()[:500]
        if "maximum channels exceeded" in err:
            errors.append((r.returncode, "ImageMagick cannot open multi-channel V-Ray EXR (channel limit)", " ".join(cmd[:3])))
            continue
        if "Invalid Parameter" in err:
            errors.append((r.returncode, "Windows convert.exe — skipped", " ".join(cmd[:3])))
            continue
        errors.append((r.returncode, err, " ".join(str(c) for c in cmd[:5])))

    detail = "\n---\n".join(f"[{rc}] {cmd}…\n{err}" for rc, err, cmd in errors if err)
    raise RuntimeError(
        f"Could not convert {src.name} (layer {layer_index}) to PNG.\n\n"
        f"This EXR has too many channels for ImageMagick "
        f"('maximum channels exceeded').\n\n"
        f"Fix (pick one):\n"
        f"  A) Install OpenImageIO and add oiiotool to PATH\n"
        f"  B) pip install imageio numpy Pillow\n"
        f"  C) In 3ds Max: export separate PNG elements (or RGB EXR only)\n\n"
        f"{detail}"
    )



# Shared pass library (load once → use in Breakdown + Showcase)
try:
    import sys as _sys
    _sys.path.insert(0, str(BASE))
    from shared import library as pass_library
except Exception:
    pass_library = None


class LayerPickDialog(QDialog):
    """Multi-select EXR subimages / channel groups → import as pass 1, 2, 3…"""
    def __init__(self, layers, parent=None, multi=True):
        super().__init__(parent)
        self.setWindowTitle("Select EXR passes to import")
        self.resize(520, 420)
        self.layers = layers or []
        self.multi = multi
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            "Select one or more passes from this EXR.\n"
            "Each checked item becomes image 1, 2, 3… in the list."
        ))
        self.list = QListWidget()
        if multi:
            self.list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for L in self.layers:
            extra = ""
            if L.get("group"):
                nch = len(L.get("channels") or [])
                extra = f"  ·  {nch} ch" if nch else ""
            item = QListWidgetItem(f"{L.get('label', 'Layer')}   ({L.get('size', '?')}){extra}")
            item.setSelected(True)  # default: all selected
            self.list.addItem(item)
        lay.addWidget(self.list, 1)
        row = QHBoxLayout()
        b_all = QPushButton("Select all")
        b_all.clicked.connect(self.list.selectAll)
        b_none = QPushButton("Select none")
        b_none.clicked.connect(self.list.clearSelection)
        row.addWidget(b_all)
        row.addWidget(b_none)
        row.addStretch()
        lay.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def selected_layers(self):
        """Return list of layer dicts the user checked/selected (order preserved)."""
        out = []
        for i in range(self.list.count()):
            if self.list.item(i).isSelected():
                out.append(self.layers[i])
        return out

    def layer_index(self):
        """Legacy single-select index."""
        rows = self.selected_layers()
        if not rows:
            return 0
        return int(rows[0].get("index", 0))



class CollapsibleSection(QWidget):
    """Collapsible panel: click header to expand/collapse content."""
    toggled = Signal(bool)

    def __init__(self, title: str, parent=None, collapsed=False):
        super().__init__(parent)
        self._title = title
        self._collapsed = bool(collapsed)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = QPushButton()
        self._header.setObjectName("collapseHeader")
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.setCheckable(True)
        self._header.setChecked(not self._collapsed)
        self._header.clicked.connect(self._on_toggle)
        root.addWidget(self._header)

        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(8, 6, 8, 8)
        self._body_layout.setSpacing(6)
        root.addWidget(self._body)

        self._refresh_header()
        self._body.setVisible(not self._collapsed)

    def body_layout(self):
        return self._body_layout

    def add_widget(self, w):
        self._body_layout.addWidget(w)

    def add_layout(self, layout):
        self._body_layout.addLayout(layout)

    def set_collapsed(self, collapsed: bool):
        self._collapsed = bool(collapsed)
        self._header.setChecked(not self._collapsed)
        self._body.setVisible(not self._collapsed)
        self._refresh_header()
        self.toggled.emit(not self._collapsed)

    def is_collapsed(self):
        return self._collapsed

    def _on_toggle(self):
        self._collapsed = not self._header.isChecked()
        self._body.setVisible(not self._collapsed)
        self._refresh_header()
        self.toggled.emit(not self._collapsed)

    def _refresh_header(self):
        arrow = "▼" if not self._collapsed else "▶"
        self._header.setText(f"  {arrow}  {self._title}")


class TimelineWidget(QWidget):
    """Interactive render-pass timeline.

    Visual order is intentionally bottom-up: pass 1 is the bottom row, pass 2
    sits above it, etc.  Each row has three editable timing regions:
    transition, pause and final hold.  Dragging boundaries edits timing
    directly; dragging the label vertically reorders passes.
    """
    clickedRow = Signal(int)
    timingChanged = Signal(int)
    editStarted = Signal(int)
    editFinished = Signal(int)
    reorderRequested = Signal(int, int)
    contextAction = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []
        self.selected = -1
        self.zoom = 1.0
        self._drag = None
        self._history_started = False
        self.setMinimumHeight(240)
        self.setMaximumHeight(520)
        self.setMouseTracking(True)
        self.setToolTip(
            "Timeline: pass 1 is at the bottom. Drag timing boundaries to edit; "
            "drag a pass label vertically to reorder. Right-click for more actions."
        )

    def set_rows(self, passes, selected=-1):
        self.rows = list(passes or [])
        self.selected = int(selected if selected is not None else -1)
        self.setMinimumHeight(max(220, 78 + max(1, len(self.rows)) * 34))
        self.update()

    def _layout(self):
        left = 190
        right = 28
        # Header (title) + secondary hint + ruler band — keep bands separate so text never overlaps.
        top = 62
        row_h = 34
        max_total = max([
            float(x.get("slide_ms", 1200)) + float(x.get("pause_ms", 800)) +
            max(0.0, float(x.get("hold", 10))) * 1000.0
            for x in self.rows
        ] or [1000.0])
        # Zoom expands the timeline horizontally while preserving a usable fit.
        usable = max(320, (self.width() - left - right) * self.zoom)
        scale = usable / max(1.0, max_total)
        return left, right, top, row_h, max_total, usable, scale

    def _display_rows(self):
        # Reverse visual order: highest pass is at top, image 1 is bottom.
        return list(reversed(list(enumerate(self.rows))))

    def _row_rect(self, display_pos):
        left, right, top, row_h, *_ = self._layout()
        return top + display_pos * row_h, row_h

    def _segment_positions(self, p):
        left, _, _, _, _, _, scale = self._layout()
        dur = max(100.0, float(p.get("slide_ms", 1200)))
        pause = max(0.0, float(p.get("pause_ms", 800)))
        hold = max(0.0, float(p.get("hold", 10))) * 1000.0
        x0 = left
        x1 = x0 + dur * scale
        x2 = x1 + pause * scale
        x3 = x2 + hold * scale
        return x0, x1, x2, x3

    def _hit_row(self, pos):
        _, _, top, row_h, *_ = self._layout()
        display = int((pos.y() - top) // row_h)
        displayed = self._display_rows()
        if 0 <= display < len(displayed):
            return displayed[display][0], display
        return -1, -1

    def _format_ms(self, ms):
        return f"{ms/1000:.2f}s" if ms < 10000 else f"{ms/1000:.1f}s"

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0c1118"))
        left, right, top, row_h, max_total, usable, scale = self._layout()
        font = painter.font()

        # --- Title band (y ~ 4–20) ---
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#d7dee8"), 1))
        painter.drawText(10, 18, "PASS TIMELINE")
        font.setBold(False)
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#6f7b8d"), 1))
        painter.drawText(118, 18, "bottom → top = render stack")

        # --- Hint band (y ~ 22–36) — left side only so it never collides with ruler ---
        painter.setPen(QPen(QColor("#5a6578"), 1))
        painter.drawText(10, 34, "Drag T / P / H  ·  drag label = reorder  ·  right-click")

        # --- Ruler band sits just above the rows (top - 18 .. top) ---
        ruler_y = top - 6
        ruler_steps = max(4, min(12, int(max_total / 1000) + 1))
        for n in range(ruler_steps + 1):
            ms = max_total * n / ruler_steps
            x = left + ms * scale
            if x > self.width() - right:
                continue
            painter.setPen(QPen(QColor("#293444"), 1))
            painter.drawLine(int(x), top - 10, int(x), top + max(1, len(self.rows)) * row_h)
            # Time labels only in the bar area, not over the left name column
            label = f"{ms/1000:.1f}s"
            painter.setPen(QColor("#748096"))
            # Center-ish under tick but keep inside track
            painter.drawText(int(x) + 2, ruler_y, label)

        displayed = self._display_rows()
        for display_pos, (idx, p) in enumerate(displayed):
            y = top + display_pos * row_h
            selected = idx == self.selected
            if selected:
                painter.fillRect(4, y + 2, self.width() - 8, row_h - 4, QColor("#202c3f"))
            painter.setPen(QColor("#f0f3f7" if selected else "#bac4d0"))
            name = str(p.get("name") or f"Pass {idx+1}")
            # Truncate by available label width so long names don't bleed into bars
            max_chars = 22
            label_name = name if len(name) <= max_chars else name[:max_chars - 1] + "…"
            hidden_mark = "  ·H" if p.get("hidden") else ""
            painter.drawText(10, y + 22, f"{idx+1:02d}  {label_name}{hidden_mark}")

            x0, x1, x2, x3 = self._segment_positions(p)
            parts = [
                (x0, x1, QColor("#c9a227"), f"T {self._format_ms(float(p.get('slide_ms', 1200)))}"),
                (x1, x2, QColor("#63738b"), f"P {self._format_ms(float(p.get('pause_ms', 800)))}"),
                (x2, x3, QColor("#355447"), f"H {self._format_ms(float(p.get('hold', 10)) * 1000.0)}"),
            ]
            for xa, xb, color, label in parts:
                w = max(2.0, xb - xa)
                painter.fillRect(int(xa), y + 8, int(w), 18, color)
                # Only draw text when the segment is wide enough to avoid overlap
                if w >= 52:
                    painter.setPen(QColor("#f7f9fb"))
                    painter.drawText(int(xa) + 5, y + 21, label)
                elif w >= 28:
                    # Short segment: show letter only
                    painter.setPen(QColor("#f7f9fb"))
                    painter.drawText(int(xa) + 3, y + 21, label[0])
            # Boundary handles.
            for bx in (x1, x2, x3):
                painter.setPen(QPen(QColor("#f2d46b" if selected else "#8290a5"), 2))
                painter.drawLine(int(bx), y + 5, int(bx), y + 29)

        painter.end()

    def _cursor_for(self, x, y):
        idx, display = self._hit_row(type("P", (), {"x": lambda s: x, "y": lambda s: y})())
        if idx < 0:
            return Qt.CursorShape.ArrowCursor
        p = self.rows[idx]
        x0, x1, x2, x3 = self._segment_positions(p)
        if min(abs(x-x1), abs(x-x2), abs(x-x3)) <= 7:
            return Qt.CursorShape.SizeHorCursor
        if x < x0:
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.PointingHandCursor

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self._drag:
            d = self._drag
            idx = d["idx"]
            if idx < 0 or idx >= len(self.rows):
                return
            p = self.rows[idx]
            left, *_rest = self._layout()
            _, _, _, _, _, _, scale = self._layout()
            ms = max(0.0, (pos.x() - left) / max(scale, 1e-9))
            if d["kind"] == "transition":
                # Keep a small, usable transition.
                p["slide_ms"] = int(max(100, min(30000, ms)))
            elif d["kind"] == "pause":
                dur = float(p.get("slide_ms", 1200))
                p["pause_ms"] = int(max(0, min(30000, ms - dur)))
            elif d["kind"] == "hold":
                dur = float(p.get("slide_ms", 1200))
                pause = float(p.get("pause_ms", 800))
                p["hold"] = max(0, min(120, (ms - dur - pause) / 1000.0))
            self.timingChanged.emit(idx)
            self.update()
            return
        self.setCursor(self._cursor_for(pos.x(), pos.y()))
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        pos = event.position()
        idx, display = self._hit_row(pos)
        if idx < 0:
            return
        if event.button() == Qt.MouseButton.RightButton:
            menu = QMenu(self)
            a_edit = menu.addAction("Edit selected pass")
            a_hide = menu.addAction("Toggle visibility")
            menu.addSeparator()
            a_t = menu.addAction("Reset timing")
            a_dup = menu.addAction("Duplicate pass")
            a_del = menu.addAction("Delete pass")
            chosen = menu.exec(event.globalPosition().toPoint())
            if chosen == a_edit: self.contextAction.emit("edit", idx)
            elif chosen == a_hide: self.contextAction.emit("toggle", idx)
            elif chosen == a_t: self.contextAction.emit("reset_timing", idx)
            elif chosen == a_dup: self.contextAction.emit("duplicate", idx)
            elif chosen == a_del: self.contextAction.emit("delete", idx)
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.selected = idx
        self.clickedRow.emit(idx)
        p = self.rows[idx]
        x0, x1, x2, x3 = self._segment_positions(p)
        dx = min((abs(pos.x()-x1), "transition"), (abs(pos.x()-x2), "pause"), (abs(pos.x()-x3), "hold"))
        if dx[0] <= 8:
            self._drag = {"idx": idx, "kind": dx[1], "start": pos.x()}
            self._history_started = True
            self.editStarted.emit(idx)
        elif pos.x() < x0:
            self._drag = {"idx": idx, "kind": "reorder", "start_y": pos.y(), "last_display": display}
            self._history_started = True
            self.editStarted.emit(idx)
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag:
            d = self._drag
            if d.get("kind") == "reorder":
                _, new_display = self._hit_row(event.position())
                if new_display >= 0:
                    displayed = self._display_rows()
                    old_display = d.get("last_display", -1)
                    if old_display != new_display and 0 <= old_display < len(displayed):
                        self.reorderRequested.emit(d["idx"], displayed[new_display][0])
            elif d.get("kind") in {"transition", "pause", "hold"}:
                self.timingChanged.emit(d["idx"])
            self.editFinished.emit(d["idx"])
            self._drag = None
            self._history_started = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            self.zoom = max(0.65, min(3.0, self.zoom * (1.15 if delta > 0 else 1/1.15)))
            self.update()
            event.accept()
            return
        super().wheelEvent(event)

class Editor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Render Pass Breakdown — Editor")
        self.resize(1040, 680)
        self.setMinimumSize(700, 500)
        self.passes = []
        self.custom_presets = {}
        self._thumb_cache = {}
        self._solo_backup = None
        self._undo_stack = []
        self._redo_stack = []
        self._history_pending = False
        self._history_restoring = False
        self._history_limit = 60
        self._build_menu()
        self.ui()
        self.load()
        self._autosave_path = BASE / "backups" / "autosave.json"
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(30_000)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start()
        self._check_autosave_recovery()
        self._update_history_ui()

    def _build_menu(self):
        mb = self.menuBar()
        m_file = mb.addMenu("File")
        act_save = m_file.addAction("Save / Generate")
        act_save.triggered.connect(self.save)
        act_open = m_file.addAction("Open Viewer")
        act_open.triggered.connect(self.open)
        m_file.addSeparator()
        act_quit = m_file.addAction("Quit")
        act_quit.triggered.connect(self.close)

        m_edit = mb.addMenu("Edit")
        self.act_undo = m_edit.addAction("Undo")
        self.act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.act_undo.triggered.connect(self.undo)
        self.act_redo = m_edit.addAction("Redo")
        self.act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.act_redo.triggered.connect(self.redo)
        m_edit.addSeparator()
        act_reset = m_edit.addAction("Reset selected pass")
        act_reset.setShortcut(QKeySequence("Ctrl+Shift+R"))
        act_reset.triggered.connect(self.reset_selected_pass)

        m_tools = mb.addMenu("Tools")
        act_deps = m_tools.addAction("Install Python dependencies…")
        act_deps.triggered.connect(self.install_dependencies)
        act_check = m_tools.addAction("Check installed packages")
        act_check.triggered.connect(self.check_dependencies)
        act_req = m_tools.addAction("Open requirements.txt")
        act_req.triggered.connect(self.open_requirements_file)

        m_help = mb.addMenu("Help")
        act_help = m_help.addAction("Install guide")
        act_help.triggered.connect(self.show_install_help)

    def ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(6, 4, 6, 4)
        main.setSpacing(4)

        top = QHBoxLayout()
        top.addWidget(QLabel("<b style='color:#d6aa63'>RENDER PASS BREAKDOWN</b>  ·  editor"))
        top.addStretch()
        self.title = QLineEdit("V-Ray Render Pass Breakdown")
        self.title.setMinimumWidth(160)
        self.title.setMaximumWidth(420)
        top.addWidget(self.title, 1)
        b_deps = QPushButton("Install deps")
        b_deps.setToolTip("Install imageio / numpy / Pillow / OpenEXR via pip")
        b_deps.clicked.connect(self.install_dependencies)
        top.addWidget(b_deps)
        main.addLayout(top)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        main.addWidget(split, 1)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(4, 4, 4, 4)
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.select)
        self.pass_search = QLineEdit()
        self.pass_search.setObjectName("passSearch")
        self.pass_search.setPlaceholderText("🔍  Search passes by name or blend mode…")
        self.pass_search.setClearButtonEnabled(True)
        self.pass_search.setToolTip("Filter the pass list. Clear the search to return to the full stack.")
        self.pass_search.textChanged.connect(self._filter_passes)
        ll.insertWidget(0, self.pass_search)
        self.list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list.model().rowsMoved.connect(self._on_rows_moved)
        self.list.setAcceptDrops(True)
        # External file drop → import images
        self.list.dragEnterEvent = self._list_drag_enter  # type: ignore
        self.list.dragMoveEvent = self._list_drag_move  # type: ignore
        self.list.dropEvent = self._list_drop_files  # type: ignore
        self.pass_filter = QLineEdit()
        self.pass_filter.setPlaceholderText("Filter passes…")
        self.pass_filter.setClearButtonEnabled(True)
        self.pass_filter.textChanged.connect(self._apply_pass_filter)
        ll.addWidget(self.pass_filter)
        ll.addWidget(self.list, 1)

        self.preview_section = CollapsibleSection("Preview", collapsed=False)
        self.preview_section.setObjectName("previewBox")
        self.preview = QLabel("Select a pass\nto preview")
        self.preview.setObjectName("previewPane")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(120)
        self.preview.setMaximumHeight(180)
        self.preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.preview.setToolTip("Preview of selected pass — double-click to open full size")
        self.preview.mouseDoubleClickEvent = lambda e: self.open_selected_image()
        self.preview_section.add_widget(self.preview)
        self.preview_composite = QCheckBox("Composite up to selection (1+2+…)")
        self.preview_composite.setChecked(True)
        self.preview_composite.setToolTip(
            "On: show stacked result through the selected pass (e.g. select 2 → 1 blended with 2).\n"
            "Off: show only the selected pass image."
        )
        self.preview_composite.stateChanged.connect(lambda *_: self._update_preview())
        self.preview_section.add_widget(self.preview_composite)
        ll.addWidget(self.preview_section)

        r = QHBoxLayout()
        for label, fn in [("+ Add", self.add), ("Dup", self.dup), ("Remove", self.remove), ("↑", self.up), ("↓", self.down)]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            r.addWidget(b)
        ll.addLayout(r)
        r2 = QHBoxLayout()
        b_load = QPushButton("Load images…")
        b_load.setToolTip("Select many images at once. Order in the dialog = order in the viewer.")
        b_load.clicked.connect(self.load_images_batch)
        b_clear = QPushButton("Clear all")
        b_clear.clicked.connect(self.clear_all)
        b_relink = QPushButton("Relink missing")
        b_relink.setToolTip("Search asset folders by filename for missing passes")
        b_relink.clicked.connect(self.relink_missing_passes)
        r2.addWidget(b_load)
        r2.addWidget(b_clear)
        r2.addWidget(b_relink)
        ll.addLayout(r2)
        r_lib = QHBoxLayout()
        b_to_lib = QPushButton("Save → Library")
        b_to_lib.setToolTip("Push current passes into the shared library (used by Showcase too).")
        b_to_lib.clicked.connect(self.push_passes_to_library)
        b_from_lib = QPushButton("Load ← Library")
        b_from_lib.setToolTip("Load passes from the shared library into this project.")
        b_from_lib.clicked.connect(self.pull_passes_from_library)
        r_lib.addWidget(b_to_lib)
        r_lib.addWidget(b_from_lib)
        ll.addLayout(r_lib)
        r_tools = QHBoxLayout()
        b_batch = QPushButton("Batch timing…")
        b_batch.setToolTip("Set transition / pause / hold for ALL passes at once")
        b_batch.clicked.connect(self.batch_timing_dialog)
        b_smart2 = QPushButton("Smart blends")
        b_smart2.setToolTip("Suggest blend modes from pass names")
        b_smart2.clicked.connect(self.apply_smart_suggestions)
        b_sort = QPushButton("Pipeline sort")
        b_sort.setToolTip("Sort passes into a typical lighting pipeline order")
        b_sort.clicked.connect(self.smart_sort)
        b_rename = QPushButton("Rename table…")
        b_rename.setToolTip("Optional rename suggestions — review and apply only what you want")
        b_rename.clicked.connect(self.open_rename_table)
        b_shot = QPushButton("Shot preset…")
        b_shot.setToolTip("Apply Interior / Car paint / Character blend packs")
        b_shot.clicked.connect(self.apply_shot_preset_dialog)
        r_tools.addWidget(b_batch)
        r_tools.addWidget(b_smart2)
        r_tools.addWidget(b_sort)
        r_tools.addWidget(b_rename)
        r_tools.addWidget(b_shot)
        ll.addLayout(r_tools)
        r3 = QHBoxLayout()
        b_open = QPushButton("Open image")
        b_open.setToolTip("Open selected pass image in system viewer")
        b_open.clicked.connect(self.open_selected_image)
        b_swap = QPushButton("Swap positions…")
        b_swap.setToolTip("Swap this pass with another index (1, 2, 3…)")
        b_swap.clicked.connect(self.swap_positions)
        b_move = QPushButton("Move to…")
        b_move.setToolTip("Move selected pass to a specific position")
        b_move.clicked.connect(self.move_to_position)
        r3.addWidget(b_open)
        r3.addWidget(b_swap)
        r3.addWidget(b_move)
        ll.addLayout(r3)
        r4 = QHBoxLayout()
        b_solo = QPushButton("Solo selected")
        b_solo.setToolTip("Show only the selected pass. Click again to restore the previous visibility state.")
        b_solo.clicked.connect(self.toggle_solo)
        self.b_solo = b_solo
        b_show = QPushButton("Show all")
        b_show.setToolTip("Make every pass visible in the viewer.")
        b_show.clicked.connect(self.show_all_passes)
        r4.addWidget(b_solo)
        r4.addWidget(b_show)
        ll.addLayout(r4)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        left_scroll.setWidget(left)
        left_scroll.setMinimumWidth(200)
        split.addWidget(left_scroll)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)

        self.pass_settings_section = CollapsibleSection("Pass Settings  ·  selected pass only", collapsed=False)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        self.pass_settings_section.body_layout().addLayout(form)

        self.name = QLineEdit()
        self.image = QLineEdit()
        b_img = QPushButton("Choose Image…")
        b_img.clicked.connect(self.choose_image)
        row_img = QHBoxLayout()
        row_img.addWidget(self.image)
        row_img.addWidget(b_img)

        self.desc = QTextEdit()
        self.desc.setFixedHeight(48)

        self.blend = QComboBox()
        for val, label in BLEND_MODES:
            self.blend.addItem(label, val)

        self.transition = QComboBox()
        for val, label in TRANSITIONS:
            self.transition.addItem(label, val)
        self.transition.currentIndexChanged.connect(self._on_transition_changed)

        self.wipe_angle = QDoubleSpinBox()
        self.wipe_angle.setRange(0, 360)
        self.wipe_angle.setValue(180)
        self.wipe_angle.setSuffix(" °")
        self.wipe_angle.setSingleStep(15)
        self.wipe_angle.setToolTip(
            "0° = left→right, 90° = top→bottom, 180° = right→left, 270° = bottom→top"
        )

        self.slide = QDoubleSpinBox()
        self.slide.setRange(0.3, 8.0)
        self.slide.setValue(1.2)
        self.slide.setSuffix(" sec")
        self.slide.setSingleStep(0.1)

        self.pause = QDoubleSpinBox()
        self.pause.setRange(0.0, 10.0)
        self.pause.setValue(0.8)
        self.pause.setSuffix(" sec")
        self.pause.setSingleStep(0.1)

        self.hold = QDoubleSpinBox()
        self.hold.setRange(1, 120)
        self.hold.setValue(10)
        self.hold.setSuffix(" sec")

        self.final = QCheckBox("This is the final beauty frame (hold, no transition out)")

        form.addRow("Pass name", self.name)
        form.addRow("Image (PNG/JPG/EXR/HDR)", row_img)
        form.addRow("Description", self.desc)
        form.addRow("Blend mode", self.blend)
        form.addRow("Transition", self.transition)
        form.addRow("Wipe angle", self.wipe_angle)
        form.addRow("Transition duration", self.slide)
        form.addRow("Pause after land", self.pause)
        form.addRow("Final hold", self.hold)
        form.addRow("", self.final)

        self.hide_in_viewer = QCheckBox("Hide in viewer (skip this pass when playing)")
        self.hide_in_viewer.setToolTip("Pass stays in the list/load section but is not shown in the presentation viewer.")
        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(0, 100)
        self.opacity.setValue(100)
        self.opacity.setSuffix(" %")
        self.opacity.setSingleStep(5)
        self.opacity.setToolTip("Blend strength when compositing onto previous (100% = full effect).")
        form.addRow("", self.hide_in_viewer)
        form.addRow("Blend opacity", self.opacity)

        hint = QLabel("Settings above apply to the <b>selected pass only</b>.")
        hint.setWordWrap(True)
        hint.setObjectName("info")
        form.addRow(hint)
        b_all = QPushButton("Apply blend / transition / timing → ALL passes")
        b_all.setToolTip(
            "Copy this pass's blend, transition, wipe angle, duration, and pause to every pass."
        )
        b_all.clicked.connect(self.apply_settings_to_all)
        form.addRow(b_all)

        self.preset_section = CollapsibleSection("Quick Presets", collapsed=False)
        preset_l = QHBoxLayout()
        preset_l.setContentsMargins(0, 0, 0, 0)
        self.preset_section.body_layout().addLayout(preset_l)
        self.preset_combo = QComboBox()
        self.preset_combo.setToolTip("Choose a compositing preset for the selected pass.")
        self.b_apply_preset = QPushButton("Apply")
        self.b_apply_preset.setToolTip("Apply the selected preset to the current pass.")
        self.b_save_preset = QPushButton("Save current…")
        self.b_save_preset.setToolTip("Save the current pass look as a reusable custom preset.")
        self.b_reset_pass = QPushButton("Reset")
        self.b_reset_pass.setToolTip("Reset the selected pass to friendly default settings.")
        preset_l.addWidget(self.preset_combo, 1)
        preset_l.addWidget(self.b_apply_preset)
        preset_l.addWidget(self.b_save_preset)
        preset_l.addWidget(self.b_reset_pass)
        self.b_apply_preset.clicked.connect(self.apply_selected_preset)
        self.b_save_preset.clicked.connect(self.save_current_preset)
        self.b_reset_pass.clicked.connect(self.reset_selected_pass)
        rl.addWidget(self.preset_section)
        self._rebuild_preset_combo()
        rl.addWidget(self.pass_settings_section)

        # —— Apply one look to every pass ——
        self.all_section = CollapsibleSection("Apply to ALL passes", collapsed=True)
        all_form = QFormLayout()
        all_form.setContentsMargins(0, 0, 0, 0)
        self.all_section.body_layout().addLayout(all_form)
        self.all_blend = QComboBox()
        for val, label in BLEND_MODES:
            self.all_blend.addItem(label, val)
        self.all_transition = QComboBox()
        for val, label in TRANSITIONS:
            self.all_transition.addItem(label, val)
        self.all_angle = QDoubleSpinBox()
        self.all_angle.setRange(0, 360)
        self.all_angle.setValue(180)
        self.all_angle.setSuffix(" °")
        self.all_angle.setSingleStep(15)
        self.all_slide = QDoubleSpinBox()
        self.all_slide.setRange(0.3, 8.0)
        self.all_slide.setValue(1.2)
        self.all_slide.setSuffix(" sec")
        self.all_pause = QDoubleSpinBox()
        self.all_pause.setRange(0.0, 10.0)
        self.all_pause.setValue(0.8)
        self.all_pause.setSuffix(" sec")
        # Checkboxes: only checked properties are written to all passes
        self.chk_all_blend = QCheckBox("Blend / compositing")
        self.chk_all_blend.setChecked(True)
        self.chk_all_transition = QCheckBox("Transition")
        self.chk_all_transition.setChecked(True)
        self.chk_all_angle = QCheckBox("Wipe angle")
        self.chk_all_angle.setChecked(False)
        self.chk_all_slide = QCheckBox("Duration")
        self.chk_all_slide.setChecked(False)
        self.chk_all_pause = QCheckBox("Pause after")
        self.chk_all_pause.setChecked(False)

        def _row(chk, widget):
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(chk)
            h.addWidget(widget, 1)
            return w

        all_form.addRow(_row(self.chk_all_blend, self.all_blend))
        all_form.addRow(_row(self.chk_all_transition, self.all_transition))
        all_form.addRow(_row(self.chk_all_angle, self.all_angle))
        all_form.addRow(_row(self.chk_all_slide, self.all_slide))
        all_form.addRow(_row(self.chk_all_pause, self.all_pause))

        chk_row = QHBoxLayout()
        b_chk_all = QPushButton("Check all")
        b_chk_none = QPushButton("Check none")
        def _set_all(v):
            for c in (
                self.chk_all_blend, self.chk_all_transition, self.chk_all_angle,
                self.chk_all_slide, self.chk_all_pause,
            ):
                c.setChecked(v)
        b_chk_all.clicked.connect(lambda: _set_all(True))
        b_chk_none.clicked.connect(lambda: _set_all(False))
        chk_row.addWidget(b_chk_all)
        chk_row.addWidget(b_chk_none)
        chk_row.addStretch()
        all_form.addRow(chk_row)

        b_apply = QPushButton("Apply checked settings → ALL passes")
        b_apply.setToolTip("Only properties with a checkmark are applied to every pass.")
        b_apply.clicked.connect(self.apply_look_to_all)
        all_form.addRow(b_apply)
        rl.addWidget(self.all_section)

        info = QLabel(
            "Load images… selects many files at once (dialog order = viewer order). "
            "Apply look to ALL sets one blend + transition on every pass. "
            "Per-pass settings still work. Multilayer EXR: pick a layer when importing."
        )
        info.setWordWrap(True)
        info.setObjectName("info")
        rl.addWidget(info)
        rl.addStretch()

        # Project extras
        # Collapsible timeline — user can open/close without losing state
        self.timeline_section = CollapsibleSection(
            "Timeline  ·  bottom = Pass 1  ·  top = latest pass", collapsed=False
        )
        timeline_tools = QHBoxLayout()
        timeline_hint = QLabel("Drag T/P/H boundaries to edit timing  ·  Ctrl+wheel = zoom  ·  drag label = reorder")
        timeline_hint.setObjectName("timelineHint")
        timeline_tools.addWidget(timeline_hint, 1)
        b_fit = QPushButton("Fit")
        b_fit.setToolTip("Fit the timeline to the available width")
        b_fit.clicked.connect(lambda: self.timeline_fit())
        timeline_tools.addWidget(b_fit)
        b_zoom_out = QPushButton("−")
        b_zoom_out.setToolTip("Zoom out timeline")
        b_zoom_out.clicked.connect(lambda: self.timeline_zoom(1/1.15))
        timeline_tools.addWidget(b_zoom_out)
        b_zoom_in = QPushButton("+")
        b_zoom_in.setToolTip("Zoom in timeline")
        b_zoom_in.clicked.connect(lambda: self.timeline_zoom(1.15))
        timeline_tools.addWidget(b_zoom_in)
        self.timeline_section.add_layout(timeline_tools)
        self.timeline = TimelineWidget()
        self.timeline.clickedRow.connect(self._select_from_timeline)
        self.timeline.timingChanged.connect(self._timeline_timing_changed)
        self.timeline.editStarted.connect(self._timeline_edit_started)
        self.timeline.editFinished.connect(self._timeline_edit_finished)
        self.timeline.reorderRequested.connect(self._timeline_reorder)
        self.timeline.contextAction.connect(self._timeline_context_action)
        self.timeline_section.add_widget(self.timeline)
        rl.addWidget(self.timeline_section)

        self.extra_section = CollapsibleSection("Project extras", collapsed=True)
        extra_l = self.extra_section.body_layout()
        soft_row = QHBoxLayout()
        soft_row.addWidget(QLabel("Renderer / DCC"))
        self.software = QComboBox()
        for val, label in SOFTWARE_LABELS:
            self.software.addItem(label, val)
        soft_row.addWidget(self.software, 1)
        extra_l.addLayout(soft_row)

        template_row = QHBoxLayout()
        template_row.addWidget(QLabel("Project template"))
        self.project_template = QComboBox()
        self.project_template.addItems(["Custom", "Basic Breakdown", "Cinematic Breakdown", "Technical AOV", "Product Visualization"])
        self.project_template.setToolTip("Apply a safe project-wide starting style. Images and pass order are preserved.")
        template_row.addWidget(self.project_template, 1)
        b_template = QPushButton("Apply")
        b_template.clicked.connect(self.apply_project_template)
        template_row.addWidget(b_template)
        b_smart = QPushButton("Smart suggest")
        b_smart.setToolTip("Suggest blend modes and transitions from common pass names without changing anything until you apply them.")
        b_smart.clicked.connect(self.apply_smart_suggestions)
        template_row.addWidget(b_smart)
        extra_l.addLayout(template_row)

        logo_row = QHBoxLayout()
        self.logo = QLineEdit()
        self.logo.setPlaceholderText("Optional logo path for burn-in (PNG)")
        b_logo = QPushButton("Logo…")
        b_logo.clicked.connect(self.choose_logo)
        logo_row.addWidget(self.logo)
        logo_row.addWidget(b_logo)
        extra_l.addLayout(logo_row)

        bed_row = QHBoxLayout()
        self.soundtrack = QLineEdit()
        self.soundtrack.setPlaceholderText("Optional soundtrack audio (mp3/wav) for viewer pitch sessions")
        self.soundtrack.setToolTip("Saved into viewer SETTINGS.soundtrack — press M in the viewer to play/pause")
        b_bed = QPushButton("Audio…")
        b_bed.setToolTip("Browse for background music / VO bed")
        def _pick_bed():
            path, _ = QFileDialog.getOpenFileName(
                self, "Soundtrack", "",
                "Audio (*.mp3 *.wav *.ogg *.m4a);;All (*.*)"
            )
            if path:
                self.soundtrack.setText(path)
        b_bed.clicked.connect(_pick_bed)
        bed_row.addWidget(self.soundtrack, 1)
        bed_row.addWidget(b_bed)
        extra_l.addLayout(bed_row)
        vo_hint = QLabel(
            "Voice-over: in the Viewer press  V  to toggle spoken pass names ·  M  for soundtrack · needs Save first"
        )
        vo_hint.setWordWrap(True)
        vo_hint.setStyleSheet("color:#9aa3b2; font-size:11px;")
        extra_l.addWidget(vo_hint)

        edge_box = QHBoxLayout()
        self.edge_show = QCheckBox("Wipe edge line")
        self.edge_show.setChecked(True)
        self.edge_show.setToolTip("Show a colored border along the wipe for linear / angled transitions")
        self.edge_color = QLineEdit("#ffffff")
        self.edge_color.setFixedWidth(90)
        self.edge_color.setToolTip("Edge color (hex), e.g. #ffffff or #d6aa63")
        b_col = QPushButton("Color…")
        b_col.clicked.connect(self.pick_edge_color)
        self.edge_width = QDoubleSpinBox()
        self.edge_width.setRange(1, 12)
        self.edge_width.setValue(2)
        self.edge_width.setSuffix(" px")
        self.edge_glow = QCheckBox("Glow")
        self.edge_glow.setChecked(True)
        edge_box.addWidget(self.edge_show)
        edge_box.addWidget(self.edge_color)
        edge_box.addWidget(b_col)
        edge_box.addWidget(self.edge_width)
        edge_box.addWidget(self.edge_glow)
        extra_l.addLayout(edge_box)
        # Compact grid so small screens still see all tools
        extra_grid = QGridLayout()
        extra_grid.setHorizontalSpacing(6)
        extra_grid.setVerticalSpacing(6)
        b_auto = QPushButton("Auto-name AOVs")
        b_auto.setToolTip("Rename passes using selected renderer naming (V-Ray, Arnold, Blender, Unreal…)")
        b_auto.clicked.connect(self.auto_name_aovs)
        b_sort = QPushButton("Smart sort")
        b_sort.setToolTip("Order passes: Lighting → GI → Reflection → … → Beauty")
        b_sort.clicked.connect(self.smart_sort)
        b_rebuild = QPushButton("Beauty rebuild preset")
        b_rebuild.setToolTip(
            "Official V-Ray beauty formula: Lighting + GI + Reflection + Refraction + "
            "Specular + SSS + SelfIllum + Caustics + Atmosphere [+ Background optional]."
        )
        b_rebuild.clicked.connect(self.apply_beauty_rebuild)
        self.include_utility = QCheckBox("Keep utility (AO, Z…)")
        self.include_utility.setChecked(False)
        self.include_utility.setToolTip(
            "Off (default): remove AO / ZDepth / normals.\n"
            "Crypto / ObjectID / Wire / Alpha are always removed."
        )
        self.include_light_selects = QCheckBox("Keep light selects")
        self.include_light_selects.setChecked(False)
        self.include_light_selects.setToolTip("Off for pure beauty formula")
        self.include_background = QCheckBox("Include VRayBackground")
        self.include_background.setChecked(False)
        self.include_background.setToolTip("Optional Overwrite plate before Final Beauty")
        b_exp = QPushButton("Export MP4…")
        b_exp.setToolTip("Export sequence to MP4 with ffmpeg")
        b_exp.clicked.connect(self.export_mp4)
        b_sheet = QPushButton("Contact sheet…")
        b_sheet.setToolTip("Export a grid image of all passes")
        b_sheet.clicked.connect(self.export_contact_sheet)
        extra_grid.addWidget(b_auto, 0, 0)
        extra_grid.addWidget(b_sort, 0, 1)
        extra_grid.addWidget(b_rebuild, 0, 2)
        extra_grid.addWidget(b_exp, 0, 3)
        extra_grid.addWidget(b_sheet, 1, 3)
        extra_grid.addWidget(self.include_utility, 1, 0)
        extra_grid.addWidget(self.include_light_selects, 1, 1)
        extra_grid.addWidget(self.include_background, 2, 0, 1, 2)
        extra_l.addLayout(extra_grid)
        rl.addWidget(self.extra_section)

        actions = QHBoxLayout()
        self.b_undo = QPushButton("↶ Undo")
        self.b_undo.setToolTip("Undo last change (Ctrl+Z)")
        self.b_undo.clicked.connect(self.undo)
        self.b_redo = QPushButton("↷ Redo")
        self.b_redo.setToolTip("Redo last undone change (Ctrl+Y / Ctrl+Shift+Z)")
        self.b_redo.clicked.connect(self.redo)
        actions.addWidget(self.b_undo)
        actions.addWidget(self.b_redo)
        s = QPushButton("SAVE / GENERATE")
        s.clicked.connect(self.save)
        o = QPushButton("OPEN VIEWER")
        o.clicked.connect(self.open)
        actions.addWidget(s)
        actions.addWidget(o)
        rl.addLayout(actions)
        self.status = QLabel("")
        self.status.setObjectName("statusBar")
        self.status.setWordWrap(True)
        rl.addWidget(self.status)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        right_scroll.setWidget(right)
        split.addWidget(right_scroll)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 3)
        split.setSizes([280, 720])

        self.setStyleSheet("""
        QMainWindow, QWidget {
            background: #0a0d12; color: #e8ecf1; font-size: 12px;
            font-family: "Segoe UI", Inter, system-ui, sans-serif;
        }
        QMenuBar {
            background: #0a0d12; color: #cdd3db; border-bottom: 1px solid #2e3746;
            padding: 3px 6px;
        }
        QMenuBar::item { padding: 4px 10px; border-radius: 5px; }
        QMenuBar::item:selected { background: #1a2230; color: #fff; }
        QMenu {
            background: #121821; color: #e8ecf1; border: 1px solid #3a4558; padding: 6px;
            border-radius: 8px;
        }
        QMenu::item { padding: 6px 16px; border-radius: 5px; }
        QMenu::item:selected { background: #c9a227; color: #0b0e14; }
        QMenu::separator { height: 1px; background: #2e3746; margin: 4px 8px; }
        QLineEdit, QTextEdit, QListWidget, QSpinBox, QDoubleSpinBox, QComboBox {
            background: #121821; border: 1px solid #3a4558; border-radius: 7px;
            padding: 6px 8px; color: #e8ecf1; selection-background-color: #3d4f6f;
            min-height: 20px;
        }
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
            border: 1px solid #c9a227;
        }
        QComboBox::drop-down {
            border: none; width: 22px;
            background: #1a2230;
            border-left: 1px solid #3a4558;
            border-top-right-radius: 7px;
            border-bottom-right-radius: 7px;
        }
        QComboBox::down-arrow {
            width: 0; height: 0;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid #c9a227;
            margin-right: 6px;
        }
        QComboBox QAbstractItemView {
            background: #121821; color: #e8ecf1;
            selection-background-color: #c9a227; selection-color: #0b0e14;
            border: 1px solid #3a4558; border-radius: 6px; padding: 4px;
        }
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            background: #1a2230; border: none; width: 18px;
        }
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
            border-left: 4px solid transparent; border-right: 4px solid transparent;
            border-bottom: 5px solid #c9a227; width: 0; height: 0;
        }
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
            border-left: 4px solid transparent; border-right: 4px solid transparent;
            border-top: 5px solid #c9a227; width: 0; height: 0;
        }
        QPushButton {
            background: #161e2c; border: 1px solid #4a5568; border-radius: 7px;
            padding: 6px 11px; color: #e8ecf1; font-weight: 500;
        }
        QPushButton:hover { background: #1f2a3c; border-color: #c9a227; }
        QPushButton:pressed { background: #c9a227; border-color: #c9a227; color: #0b0e14; }
        QPushButton:disabled { color: #5a6570; border-color: #2e3746; background: #0f141c; }
        QListWidget {
            outline: none; background: #0c1018; border: 1px solid #3a4558;
            border-radius: 9px; padding: 3px;
        }
        QListWidget::item {
            padding: 7px 10px; border-radius: 6px; margin: 1px 2px; color: #c5ccd6;
        }
        QListWidget::item:selected {
            background: #1a2436; border-left: 3px solid #c9a227; color: #fff;
        }
        QListWidget::item:hover:!selected { background: #141c28; }
        QGroupBox {
            border: 1px solid #3a4558; border-radius: 9px;
            margin-top: 14px; padding: 14px 12px 12px 12px;
            background: #0e131b;
        }
        QGroupBox::title {
            subcontrol-origin: margin; left: 12px; padding: 0 8px;
            color: #e0b84a; font-weight: 650; font-size: 11px;
            background: #0e131b;
        }
        QGroupBox#previewBox {
            background: #080b10; border: 1px solid #3a4558;
        }
        QCheckBox { spacing: 7px; color: #b8c0cb; }
        QCheckBox::indicator {
            width: 15px; height: 15px; border-radius: 4px;
            border: 1px solid #4a5568; background: #121821;
        }
        QCheckBox::indicator:checked { background: #c9a227; border-color: #c9a227; }
        QCheckBox::indicator:hover { border-color: #c9a227; }
        QLabel#info {
            background: #121821; border: 1px solid #3a4558; border-radius: 7px;
            padding: 9px; color: #8b949e; font-size: 11px;
        }
        QLabel#statusBar { color: #7d8796; font-size: 11px; padding: 3px 4px; }
        QLabel#previewPane {
            background: #05070b; border: 1px solid #3a4558; border-radius: 9px;
            color: #6a7380; padding: 8px; font-size: 11px; min-height: 110px;
        }
        QLineEdit#passSearch {
            border: 1px solid #3a4558; border-radius: 7px; padding: 8px 10px;
            background: #0b0f15; color: #e9edf2;
        }
        QLineEdit#passSearch:focus { border-color: #c9a227; }
        QGroupBox#previewBox { margin-top: 4px; }
        QPushButton { min-height: 30px; }
        QScrollArea { background: transparent; border: none; }
        QSplitter::handle { background: #2e3746; width: 3px; margin: 2px 0; border-radius: 2px; }
        QSplitter::handle:hover { background: #c9a227; }
        QFormLayout { spacing: 7px; }
        QPushButton#collapseHeader {
            background: #121821;
            border: 1px solid #3a4558;
            border-radius: 8px;
            padding: 8px 10px;
            text-align: left;
            font-weight: 650;
            color: #e0b84a;
            min-height: 28px;
        }
        QPushButton#collapseHeader:hover {
            border-color: #c9a227;
            background: #161e2c;
        }
        QPushButton#collapseHeader:checked {
            border-color: #4a5568;
        }

        QToolTip {
            background: #1a2230; color: #e8ecf1; border: 1px solid #4a5568;
            padding: 6px 10px; border-radius: 6px; font-size: 11px;
        }
        """)




        self._on_transition_changed()
        self._active_row = -1
        # Editor keyboard workflow
        self._shortcuts = []
        for seq, fn in [
            ("Ctrl+Z", self.undo), ("Ctrl+Y", self.redo), ("Ctrl+Shift+Z", self.redo),
            ("Ctrl+S", self.save), ("Ctrl+Delete", self.remove), ("Alt+Up", self.up), ("Alt+Down", self.down),
        ]:
            sc = QShortcut(QKeySequence(seq), self)
            sc.activated.connect(fn)
            self._shortcuts.append(sc)
        self._loading = False
        # Live-commit so blend/transition never get lost when switching passes
        self.blend.currentIndexChanged.connect(self._on_field_changed)
        self.transition.currentIndexChanged.connect(self._on_field_changed)
        self.wipe_angle.valueChanged.connect(self._on_field_changed)
        self.slide.valueChanged.connect(self._on_field_changed)
        self.pause.valueChanged.connect(self._on_field_changed)
        self.hold.valueChanged.connect(self._on_field_changed)
        self.final.stateChanged.connect(self._on_field_changed)
        if hasattr(self, "hide_in_viewer"):
            self.hide_in_viewer.stateChanged.connect(self._on_field_changed)
            self.hide_in_viewer.stateChanged.connect(lambda *_: self._update_preview())
        if hasattr(self, "opacity"):
            self.opacity.valueChanged.connect(self._on_field_changed)
            self.opacity.valueChanged.connect(lambda *_: self._update_preview())
        self.name.editingFinished.connect(self._on_field_changed)
        self.image.editingFinished.connect(self._on_field_changed)
        self.image.editingFinished.connect(self._update_preview)
        self.desc.textChanged.connect(self._on_field_changed)

    def _snapshot_state(self):
        """Return a JSON-safe editor snapshot for undo/redo."""
        settings = {}
        for key in ("logo", "soundtrack", "edge_show", "edge_color", "edge_width", "edge_glow", "show_topbar", "show_brand", "show_counter", "show_pass_name", "show_tags", "show_timeline", "show_hint", "show_caption"):
            w = getattr(self, key, None)
            if w is None:
                continue
            if hasattr(w, "isChecked"):
                settings[key] = bool(w.isChecked())
            elif hasattr(w, "value"):
                settings[key] = float(w.value())
            elif hasattr(w, "text"):
                settings[key] = w.text()
        return {"passes": json.loads(json.dumps(self.passes, ensure_ascii=False)), "title": self.title.text(), "custom_presets": json.loads(json.dumps(self.custom_presets, ensure_ascii=False)), "settings": settings}

    def _push_history(self, snapshot=None):
        if self._history_restoring:
            return
        snap = snapshot if snapshot is not None else self._snapshot_state()
        self._undo_stack.append(snap)
        if len(self._undo_stack) > self._history_limit:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._history_pending = True
        self._update_history_ui()

    def _begin_history(self):
        if self._history_restoring or self._history_pending:
            return
        self._push_history(self._snapshot_state())

    def _finish_history(self):
        self._history_pending = False
        self._update_history_ui()

    def _restore_snapshot(self, snap):
        self._history_restoring = True
        try:
            self.passes = json.loads(json.dumps(snap.get("passes", []), ensure_ascii=False))
            self.custom_presets = json.loads(json.dumps(snap.get("custom_presets", {}), ensure_ascii=False))
            if hasattr(self, "title"):
                self.title.setText(str(snap.get("title", self.title.text())))
            for key, val in (snap.get("settings") or {}).items():
                w = getattr(self, key, None)
                if w is None:
                    continue
                if hasattr(w, "setChecked") and isinstance(val, bool):
                    w.setChecked(val)
                elif hasattr(w, "setValue") and isinstance(val, (int,float)):
                    w.setValue(val)
                elif hasattr(w, "setText"):
                    w.setText(str(val))
            self._solo_backup = None
            self.refresh()
            self._rebuild_preset_combo()
            r = min(max(self._active_row, 0), len(self.passes)-1) if self.passes else -1
            if r >= 0:
                self.list.setCurrentRow(r)
                self.select(r)
            self._update_timeline()
        finally:
            self._history_restoring = False
            self._history_pending = False
            self._update_history_ui()

    def undo(self):
        self.commit_active()
        if not self._undo_stack:
            self._toast("Nothing to undo")
            return
        # status visibility
        current = self._snapshot_state()
        target = self._undo_stack.pop()
        self._redo_stack.append(current)
        self._restore_snapshot(target)
        self._toast("Undone")

    def redo(self):
        self.commit_active()
        if not self._redo_stack:
            self._toast("Nothing to redo")
            return
        current = self._snapshot_state()
        target = self._redo_stack.pop()
        self._undo_stack.append(current)
        self._restore_snapshot(target)
        self._toast("Redone")

    def _update_history_ui(self):
        if hasattr(self, "act_undo"):
            self.act_undo.setEnabled(bool(self._undo_stack))
        if hasattr(self, "act_redo"):
            self.act_redo.setEnabled(bool(self._redo_stack))
        if hasattr(self, "b_undo"):
            self.b_undo.setEnabled(bool(self._undo_stack))
        if hasattr(self, "b_redo"):
            self.b_redo.setEnabled(bool(self._redo_stack))

    def timeline_fit(self):
        if hasattr(self, "timeline"):
            self.timeline.zoom = 1.0
            self.timeline.update()

    def timeline_zoom(self, factor):
        if hasattr(self, "timeline"):
            self.timeline.zoom = max(0.65, min(3.0, self.timeline.zoom * float(factor)))
            self.timeline.update()

    def _timeline_edit_started(self, row):
        if 0 <= row < len(self.passes):
            self._begin_history()
            self.list.setCurrentRow(row)
            self.select(row)
            self._timeline_history_active = True

    def _timeline_timing_changed(self, row):
        if not (0 <= row < len(self.passes)):
            return
        # Keep the inspector synchronized while dragging, without creating
        # a separate undo entry for every mouse-move event.
        self.refresh()
        self.list.setCurrentRow(row)
        self.select(row)

    def _timeline_edit_finished(self, row):
        if getattr(self, "_timeline_history_active", False):
            self._finish_history()
            self._timeline_history_active = False

    def _timeline_reorder(self, old_row, new_row):
        if old_row == new_row or not (0 <= old_row < len(self.passes)) or not (0 <= new_row < len(self.passes)):
            return
        self._begin_history()
        self.commit_active()
        item = self.passes.pop(old_row)
        self.passes.insert(new_row, item)
        self._reload_list(select=new_row)
        self._finish_history()
        self._toast(f"Moved pass to {new_row + 1:02d}")

    def _timeline_context_action(self, action, row):
        if not (0 <= row < len(self.passes)):
            return
        self.list.setCurrentRow(row)
        self.select(row)
        if action == "edit":
            self.name.setFocus()
        elif action == "toggle":
            self._begin_history()
            self.passes[row]["hidden"] = not bool(self.passes[row].get("hidden"))
            self.refresh(); self.select(row); self._finish_history()
        elif action == "reset_timing":
            self._begin_history()
            self.passes[row]["slide_ms"] = 1200
            self.passes[row]["pause_ms"] = 800
            self.passes[row]["hold"] = 10
            self.refresh(); self.select(row); self._finish_history()
        elif action == "duplicate":
            self.dup()
        elif action == "delete":
            self.remove()

    def _select_from_timeline(self, row):
        if 0 <= row < len(self.passes):
            self.list.setCurrentRow(row)
            self.select(row)

    def _update_timeline(self):
        if hasattr(self, "timeline"):
            self.timeline.set_rows(self.passes, self.list.currentRow() if hasattr(self, "list") else -1)

    def _filter_passes(self, text):
        """Filter visible list items without changing their real pass indices."""
        q = str(text or "").strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            p = self.passes[i] if i < len(self.passes) else {}
            hay = f"{p.get('name', '')} {p.get('blend', '')} {p.get('transition', '')}".lower()
            item.setHidden(bool(q) and q not in hay)
        self.list.setDragDropMode(
            QListWidget.DragDropMode.NoDragDrop if q else QListWidget.DragDropMode.InternalMove
        )
        if q and self.list.currentItem() and self.list.currentItem().isHidden():
            for i in range(self.list.count()):
                if not self.list.item(i).isHidden():
                    self.list.setCurrentRow(i)
                    break

    def toggle_solo(self):
        r = self.list.currentRow()
        if r < 0 or r >= len(self.passes):
            self._toast("Select a pass first")
            return
        self.commit_active()
        if self._solo_backup is None:
            self._solo_backup = {id(p): bool(p.get("hidden", False)) for p in self.passes}
            for i, p in enumerate(self.passes):
                p["hidden"] = i != r
            self.b_solo.setText("Exit solo")
            self._toast(f"Solo: {r + 1:02d} {self.passes[r].get('name', 'Pass')}")
        else:
            for p in self.passes:
                if id(p) in self._solo_backup:
                    p["hidden"] = self._solo_backup[id(p)]
            self._solo_backup = None
            self.b_solo.setText("Solo selected")
            self._toast("Solo mode off")
        self.refresh()
        self.list.setCurrentRow(r)
        self.select(r)

    def show_all_passes(self):
        self.commit_active()
        for p in self.passes:
            p["hidden"] = False
        self._solo_backup = None
        if hasattr(self, "b_solo"):
            self.b_solo.setText("Solo selected")
        self.refresh()
        r = max(0, min(self.list.currentRow(), len(self.passes) - 1)) if self.passes else -1
        if r >= 0:
            self.list.setCurrentRow(r)
            self.select(r)
        self._toast("All passes visible")

    def _builtin_presets(self):
        return {
            "Natural": {"blend": "normal", "transition": "fade", "wipe_angle": 180, "slide_ms": 1200, "pause_ms": 800, "opacity": 100},
            "Ambient Occlusion": {"blend": "multiply", "transition": "wipe_angle", "wipe_angle": 45, "slide_ms": 1200, "pause_ms": 600, "opacity": 100},
            "Reflection": {"blend": "screen", "transition": "soft_wipe_angle", "wipe_angle": 45, "slide_ms": 1000, "pause_ms": 600, "opacity": 80},
            "Glow / Emission": {"blend": "add", "transition": "fade", "wipe_angle": 180, "slide_ms": 900, "pause_ms": 500, "opacity": 100},
            "Subtle": {"blend": "screen", "transition": "fade", "wipe_angle": 180, "slide_ms": 1000, "pause_ms": 500, "opacity": 55},
            "Cinematic": {"blend": "screen", "transition": "zoom_fade", "wipe_angle": 180, "slide_ms": 1600, "pause_ms": 900, "opacity": 85},
        }

    def _rebuild_preset_combo(self):
        if not hasattr(self, "preset_combo"):
            return
        current = self.preset_combo.currentText()
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItems(list(self._builtin_presets().keys()))
        if self.custom_presets:
            self.preset_combo.insertSeparator(self.preset_combo.count())
            self.preset_combo.addItems([f"Custom · {k}" for k in self.custom_presets])
        idx = self.preset_combo.findText(current)
        self.preset_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.preset_combo.blockSignals(False)

    def _selected_preset_values(self):
        name = self.preset_combo.currentText() if hasattr(self, "preset_combo") else "Natural"
        if name.startswith("Custom · "):
            return self.custom_presets.get(name[9:], {})
        return self._builtin_presets().get(name, {})

    def apply_selected_preset(self):
        self._begin_history()
        r = self.list.currentRow()
        if r < 0 or r >= len(self.passes):
            self._toast("Select a pass first")
            return
        vals = self._selected_preset_values()
        if not vals:
            return
        self.commit_active()
        p = self.passes[r]
        for k, v in vals.items():
            p[k] = v
        self.select(r)
        self.refresh()
        self.list.setCurrentRow(r)
        self._finish_history()
        self._toast(f"Applied preset: {self.preset_combo.currentText()}")

    def save_current_preset(self):
        self._begin_history()
        r = self.list.currentRow()
        if r < 0 or r >= len(self.passes):
            self._toast("Select a pass first")
            return
        self.commit_active()
        name, ok = QInputDialog.getText(self, "Save preset", "Preset name:")
        name = name.strip()
        if not ok or not name:
            return
        p = self.passes[r]
        self.custom_presets[name] = {
            "blend": p.get("blend", "normal"),
            "transition": p.get("transition", "wipe_rl"),
            "wipe_angle": float(p.get("wipe_angle", 180)),
            "slide_ms": int(p.get("slide_ms", 1200)),
            "pause_ms": int(p.get("pause_ms", 800)),
            "opacity": float(p.get("opacity", 100)),
        }
        self._rebuild_preset_combo()
        idx = self.preset_combo.findText(f"Custom · {name}")
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self._finish_history()
        self._toast(f"Saved custom preset: {name}")

    def reset_selected_pass(self):
        self._begin_history()
        r = self.list.currentRow()
        if r < 0 or r >= len(self.passes):
            return
        self.commit_active()
        p = self.passes[r]
        p.update({
            "slide_ms": 1200, "pause_ms": 800, "hold": 10,
            "blend": "normal", "transition": "wipe_rl", "wipe_angle": 180,
            "opacity": 100, "hidden": False, "final": False,
        })
        self.select(r)
        self.refresh()
        self.list.setCurrentRow(r)
        self._finish_history()
        self._toast("Selected pass reset")

    def _combo_val(self, combo, default=""):
        v = combo.currentData()
        if v is None:
            v = combo.itemData(combo.currentIndex())
        if v is None:
            # last resort: match visible text
            text = combo.currentText()
            for i in range(combo.count()):
                if combo.itemText(i) == text:
                    v = combo.itemData(i)
                    break
        return default if v is None else v

    def _on_transition_changed(self):
        t = self._combo_val(self.transition, "")
        self.wipe_angle.setEnabled("angle" in str(t) or t in ("wipe_rl", "wipe_lr", "soft_wipe_rl", "soft_wipe_lr"))

    def _on_field_changed(self, *args):
        if self._loading:
            return
        self._begin_history()
        # transition enable state
        if self.sender() is self.transition:
            self._on_transition_changed()
        self.commit_row(self._active_row)
        # refresh list label for blend/name
        r = self._active_row
        if 0 <= r < len(self.passes):
            p = self.passes[r]
            self.list.blockSignals(True)
            item = self.list.item(r)
            if item:
                item.setText(f"{r+1:02d}  {p.get('name', 'Pass')}  [{p.get('blend', 'normal')}]")
            self.list.blockSignals(False)

    def load(self):
        if DATA.exists():
            try:
                t = DATA.read_text(encoding="utf8")
                a = t.index("window.PASSES = ") + len("window.PASSES = ")
                b = t.index(";", a)
                raw = json.loads(t[a:b])
                self.passes = []
                for p in raw:
                    img = p.get("image") or p.get("after") or p.get("before") or ""
                    self.passes.append({
                        "name": str(p.get("name", "Pass")),
                        "image": str(img),
                        "description": str(p.get("description", "")),
                        "slide_ms": max(300, int(float(p.get("slide_ms", p.get("travel_ms", 1200))))),
                        "pause_ms": max(0, int(float(p.get("pause_ms", 800)))),
                        "hold": max(1.0, float(p.get("hold", 10))),
                        "final": bool(p.get("final", False)),
                        "blend": str(p.get("blend", "normal")),
                        "transition": str(p.get("transition", "wipe_rl")),
                        "wipe_angle": max(0.0, min(360.0, float(p.get("wipe_angle", 180)))),
                        "hidden": bool(p.get("hidden", p.get("hide", False))),
                        "opacity": max(0.0, min(100.0, float(p.get("opacity", 100)))),
                    })
                a = t.index("window.PROJECT_TITLE = ") + len("window.PROJECT_TITLE = ")
                b = t.index(";", a)
                self.title.setText(json.loads(t[a:b]))
                if "window.SETTINGS = " in t:
                    try:
                        sa = t.index("window.SETTINGS = ") + len("window.SETTINGS = ")
                        sb = t.index(";", sa)
                        st = json.loads(t[sa:sb])
                        self.custom_presets = dict(st.get("custom_presets", {}) or {})
                        if hasattr(self, "logo"):
                            self.logo.setText(st.get("logo", ""))
                        if hasattr(self, "soundtrack"):
                            self.soundtrack.setText(st.get("soundtrack", ""))
                        if hasattr(self, "edge_show"):
                            self.edge_show.setChecked(st.get("edge_show", True))
                        if hasattr(self, "edge_color"):
                            self.edge_color.setText(st.get("edge_color", "#ffffff"))
                        if hasattr(self, "edge_width"):
                            self.edge_width.setValue(float(st.get("edge_width", 2)))
                        if hasattr(self, "edge_glow"):
                            self.edge_glow.setChecked(st.get("edge_glow", True))
                        for key, attr in (
                            ("show_topbar", "show_topbar"),
                            ("show_brand", "show_brand"),
                            ("show_counter", "show_counter"),
                            ("show_pass_name", "show_pass_name"),
                            ("show_tags", "show_tags"),
                            ("show_timeline", "show_timeline"),
                            ("show_hint", "show_hint"),
                            ("show_caption", "show_caption"),
                        ):
                            w = getattr(self, attr, None)
                            if w is not None:
                                w.setChecked(st.get(key, True) is not False)
                    except Exception:
                        pass
            except Exception:
                self.passes = []
        if not self.passes:
            self.passes = [dict(p, hidden=False, opacity=100) for p in DEFAULT_PASSES]
        else:
            for p in self.passes:
                p["hidden"] = bool(p.get("hidden", p.get("hide", False)))
                try:
                    p["opacity"] = max(0.0, min(100.0, float(p.get("opacity", 100))))
                except Exception:
                    p["opacity"] = 100.0
        self._active_row = -1
        self.refresh()
        if self.passes:
            self.list.setCurrentRow(0)
            self._active_row = 0
            # force load UI for row 0 (in case signal didn't fire)
            self.select(0)

    def refresh(self):
        from PySide6.QtCore import Qt as _Qt
        self.list.blockSignals(True)
        self.list.clear()
        for i, p in enumerate(self.passes):
            tag = p.get("blend", "normal")
            hid = "  👁✕" if p.get("hidden") else ""
            op = p.get("opacity", 100)
            op_s = f" {int(op)}%" if op is not None and float(op) < 100 else ""
            item = QListWidgetItem(f"{i+1:02d}  {p.get('name', 'Pass')}  [{tag}{op_s}]{hid}")
            item.setData(_Qt.ItemDataRole.UserRole, i)
            item.setData(_Qt.ItemDataRole.UserRole + 1, id(p))  # stable identity for drag-drop
            self.list.addItem(item)
        self.list.blockSignals(False)
        self._update_timeline()

    def _set_combo(self, combo, value):
        idx = combo.findData(value)
        if idx < 0:
            # try string match on data
            for i in range(combo.count()):
                if str(combo.itemData(i)) == str(value):
                    idx = i
                    break
        if idx < 0:
            idx = 0
        combo.blockSignals(True)
        combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    def apply_settings_to_all(self):
        self._begin_history()
        """Copy current pass blend/transition/timing onto every pass."""
        self.commit_active()
        r = self.list.currentRow()
        if r < 0 or not self.passes:
            self._toast("Select a pass first")
            return
        src = self.passes[r]
        keys = ("blend", "transition", "wipe_angle", "slide_ms", "pause_ms")
        for i, p in enumerate(self.passes):
            if i == r:
                continue
            for k in keys:
                if k in src:
                    p[k] = src[k]
        self.refresh()
        self.list.setCurrentRow(r)
        self.select(r)
        self._finish_history()
        self._toast(f"Applied blend/transition/timing from pass {r+1} → all {len(self.passes)} passes")

    def commit_row(self, r):

        """Write current form widgets into passes[r]."""
        if r is None or r < 0 or r >= len(self.passes):
            return
        p = self.passes[r]
        p["name"] = self.name.text().strip() or "Untitled Pass"
        p["image"] = self.image.text().strip()
        p["description"] = self.desc.toPlainText().strip()
        p["slide_ms"] = int(self.slide.value() * 1000)
        p["pause_ms"] = int(self.pause.value() * 1000)
        p["hold"] = float(self.hold.value())
        p["final"] = bool(self.final.isChecked())
        p["blend"] = self._combo_val(self.blend, "normal")
        p["transition"] = self._combo_val(self.transition, "wipe_rl")
        p["wipe_angle"] = float(self.wipe_angle.value())
        if hasattr(self, "hide_in_viewer"):
            p["hidden"] = bool(self.hide_in_viewer.isChecked())
        if hasattr(self, "opacity"):
            p["opacity"] = float(self.opacity.value())

    def commit_active(self):
        """Commit the currently active (or list-selected) row."""
        r = self._active_row if self._active_row >= 0 else self.list.currentRow()
        self.commit_row(r)

    def select(self, r):
        # Finish the current undo group before moving to another pass.
        if self._active_row >= 0 and self._active_row != r and not self._loading:
            self._finish_history()
            # CRITICAL: commit previous pass BEFORE loading the new one
            self.commit_row(self._active_row)

        if r < 0 or r >= len(self.passes):
            self._active_row = r
            return

        self._loading = True
        self._active_row = r
        p = self.passes[r]
        self.name.blockSignals(True)
        self.image.blockSignals(True)
        self.desc.blockSignals(True)

        self.name.setText(p.get("name", ""))
        self.image.setText(p.get("image", ""))
        self.desc.setPlainText(p.get("description", ""))
        self.slide.blockSignals(True)
        self.pause.blockSignals(True)
        self.hold.blockSignals(True)
        self.wipe_angle.blockSignals(True)
        self.final.blockSignals(True)

        self.slide.setValue(float(p.get("slide_ms", 1200)) / 1000)
        self.pause.setValue(float(p.get("pause_ms", 800)) / 1000)
        self.hold.setValue(float(p.get("hold", 10)))
        self.final.setChecked(bool(p.get("final", False)))
        if hasattr(self, "hide_in_viewer"):
            self.hide_in_viewer.blockSignals(True)
            self.hide_in_viewer.setChecked(bool(p.get("hidden", False)))
            self.hide_in_viewer.blockSignals(False)
        if hasattr(self, "opacity"):
            self.opacity.blockSignals(True)
            self.opacity.setValue(float(p.get("opacity", 100)))
            self.opacity.blockSignals(False)
        self._set_combo(self.blend, p.get("blend", "normal"))
        self._set_combo(self.transition, p.get("transition", "wipe_rl"))
        self.wipe_angle.setValue(float(p.get("wipe_angle", 180)))
        self._on_transition_changed()

        self.name.blockSignals(False)
        self.image.blockSignals(False)
        self.desc.blockSignals(False)
        self.slide.blockSignals(False)
        self.pause.blockSignals(False)
        self.hold.blockSignals(False)
        self.wipe_angle.blockSignals(False)
        self.final.blockSignals(False)
        self._loading = False
        self._update_preview()
        self._update_timeline()

    def _resolve_image_path(self, rel: str):
        """Find on-disk path for a pass image (relative or absolute)."""
        if not rel:
            return None
        rel = rel.strip().replace("\\", "/").replace("\\", "/")
        name = Path(rel).name
        candidates = [
            Path(rel),
            VIEWER / rel,
            VIEWER / rel.lstrip("/"),
            ASSETS / name,
            VIEWER / "assets" / "passes" / name,
            VIEWER / "assets" / name,
            BASE / rel,
            BASE.parent / rel,
        ]
        # Windows absolute paths
        if len(rel) > 2 and rel[1] == ":":
            candidates.insert(0, Path(rel))
        seen = set()
        for c in candidates:
            try:
                c = c.resolve()
            except Exception:
                continue
            key = str(c).lower()
            if key in seen:
                continue
            seen.add(key)
            if c.is_file():
                return c
        return None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Rescale preview when window size changes
        if hasattr(self, "preview") and getattr(self, "_preview_src", None):
            self._update_preview()

    def _update_preview(self):
        if not hasattr(self, "preview"):
            return
        r = self.list.currentRow()
        if r < 0 or r >= len(self.passes):
            self.preview.setPixmap(QPixmap())
            self.preview.setText("Select a pass\nto preview")
            return

        use_comp = hasattr(self, "preview_composite") and self.preview_composite.isChecked()
        if use_comp:
            pix = self._build_composite_preview(r)
            if pix is not None and not pix.isNull():
                pw = max(40, self.preview.width() - 16) if self.preview.width() > 40 else 240
                ph = max(40, self.preview.height() - 16) if self.preview.height() > 40 else 160
                scaled = pix.scaled(pw, ph, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.preview.setPixmap(scaled)
                self.preview.setText("")
                self._preview_src = None
                return

        rel = (self.passes[r].get("image") or self.image.text() or "").strip()
        if not rel:
            self.preview.setPixmap(QPixmap())
            self.preview.setText("No image assigned\nChoose Image… or Load images")
            return
        path = self._resolve_image_path(rel)
        if not path:
            self.preview.setPixmap(QPixmap())
            self.preview.setText("File not found\n" + (Path(rel).name if rel else ""))
            return
        pix = QPixmap(str(path))
        if pix.isNull():
            self.preview.setPixmap(QPixmap())
            self.preview.setText("Cannot load\n" + path.name)
            return
        pw = self.preview.width()
        ph = self.preview.height()
        if pw < 40:
            pw = 240
        if ph < 40:
            ph = 160
        scaled = pix.scaled(
            max(40, pw - 16), max(40, ph - 16),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview.setPixmap(scaled)
        self.preview.setText("")
        self._preview_src = str(path)

    def _build_composite_preview(self, upto_index: int):
        """Composite passes[0..upto] with blend/opacity (skip hidden). Returns QPixmap or None."""
        try:
            from PySide6.QtGui import QPainter, QImage
            from PySide6.QtCore import QSize
        except Exception:
            return None

        # Map editor blend names to QPainter composition modes
        modes = {
            "normal": QPainter.CompositionMode.CompositionMode_SourceOver,
            "add": QPainter.CompositionMode.CompositionMode_Plus,
            "plus": QPainter.CompositionMode.CompositionMode_Plus,
            "screen": QPainter.CompositionMode.CompositionMode_Screen,
            "multiply": QPainter.CompositionMode.CompositionMode_Multiply,
            "overlay": QPainter.CompositionMode.CompositionMode_Overlay,
            "soft-light": QPainter.CompositionMode.CompositionMode_SoftLight,
            "hard-light": QPainter.CompositionMode.CompositionMode_HardLight,
            "lighten": QPainter.CompositionMode.CompositionMode_Lighten,
            "darken": QPainter.CompositionMode.CompositionMode_Darken,
            "color-dodge": QPainter.CompositionMode.CompositionMode_ColorDodge,
            "color-burn": QPainter.CompositionMode.CompositionMode_ColorBurn,
            "difference": QPainter.CompositionMode.CompositionMode_Difference,
        }

        base_img = None
        for i in range(0, upto_index + 1):
            p = self.passes[i]
            if p.get("hidden"):
                continue
            rel = (p.get("image") or "").strip()
            path = self._resolve_image_path(rel)
            if not path:
                continue
            pix = QPixmap(str(path))
            if pix.isNull():
                continue
            if base_img is None:
                base_img = pix.toImage().convertToFormat(QImage.Format.Format_ARGB32)
                continue
            # Blend this layer onto base
            layer = pix.toImage().convertToFormat(QImage.Format.Format_ARGB32)
            if layer.size() != base_img.size():
                layer = layer.scaled(base_img.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
            painter = QPainter(base_img)
            blend = str(p.get("blend") or "normal").lower()
            op = float(p.get("opacity", 100)) / 100.0
            op = max(0.0, min(1.0, op))
            painter.setOpacity(op)
            painter.setCompositionMode(modes.get(blend, QPainter.CompositionMode.CompositionMode_SourceOver))
            painter.drawImage(0, 0, layer)
            painter.end()

        if base_img is None:
            return None
        return QPixmap.fromImage(base_img)


    def open_selected_image(self):
        r = self.list.currentRow()
        if r < 0 or r >= len(self.passes):
            self._toast("Select a pass first")
            return
        rel = (self.passes[r].get("image") or "").strip()
        path = self._resolve_image_path(rel)
        if not path:
            QMessageBox.warning(self, "Open image", f"File not found:\n{rel or '(empty)'}")
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
            self._toast(f"Opened {path.name}")
        except Exception as e:
            QMessageBox.warning(self, "Open image", str(e))

    def swap_positions(self):
        self._begin_history()
        """Swap two pass slots (view order only — does not copy image files)."""
        self.commit_active()
        r = self.list.currentRow()
        n = len(self.passes)
        if r < 0 or n < 2:
            self._toast("Need at least 2 passes")
            return
        other, ok = QInputDialog.getInt(
            self,
            "Swap positions",
            f"Swap pass {r + 1} with position (1–{n}):\n"
            "(Only list order changes — images stay the same files.)",
            min(r + 2, n),
            1,
            n,
            1,
        )
        if not ok:
            return
        j = other - 1
        if j == r:
            return
        # Pure in-place swap of pass dicts (same image paths)
        self.passes[r], self.passes[j] = self.passes[j], self.passes[r]
        self._reload_list(select=j)
        self._finish_history()
        self._toast(f"Swapped positions {r + 1} ↔ {other}")

    def move_to_position(self):
        self._begin_history()
        """
        Move selected pass to a new index; others shift to fill the gap.
        Example: move 1 → 5  ⇒  old2,old3,old4,old5,old1
        Does not copy or change image files.
        """
        self.commit_active()
        r = self.list.currentRow()
        n = len(self.passes)
        if r < 0 or n < 1:
            return
        dest, ok = QInputDialog.getInt(
            self,
            "Move to position",
            f"Move pass {r + 1} to position (1–{n}):\n"
            "Others shift up/down. Images are not duplicated.",
            r + 1,
            1,
            n,
            1,
        )
        if not ok:
            return
        j = dest - 1
        if j == r:
            return
        item = self.passes.pop(r)
        self.passes.insert(j, item)
        self._reload_list(select=j)
        self._finish_history()
        self._toast(f"Moved to position {dest}")

    def _reload_list(self, select=None):
        """Refresh list UI and selection without touching image files."""
        cur = select if select is not None else self.list.currentRow()
        self._active_row = -1
        self.refresh()
        if self.passes:
            cur = max(0, min(cur, len(self.passes) - 1))
            self.list.setCurrentRow(cur)
            self.select(cur)

    def _on_rows_moved(self, parent, start, end, dest, dest_row):
        self._begin_history()
        """
        After drag-and-drop: rebuild passes order from list items.
        Uses pass object identity stored on each item — no file copy.
        """
        from PySide6.QtCore import Qt as _Qt
        # Items were moved by Qt; UserRole still points at old indices — use stored id
        new_order = []
        for i in range(self.list.count()):
            item = self.list.item(i)
            pid = item.data(_Qt.ItemDataRole.UserRole + 1)
            if pid is not None:
                # find pass by id
                for p in self.passes:
                    if id(p) == pid:
                        new_order.append(p)
                        break
            else:
                idx = item.data(_Qt.ItemDataRole.UserRole)
                if idx is not None and 0 <= int(idx) < len(self.passes):
                    p = self.passes[int(idx)]
                    if p not in new_order:
                        new_order.append(p)
        # Deduplicate while preserving order
        seen = set()
        ordered = []
        for p in new_order:
            k = id(p)
            if k not in seen:
                seen.add(k)
                ordered.append(p)
        if len(ordered) == len(self.passes) and ordered:
            self.passes = ordered
            cur = self.list.currentRow()
            self._active_row = -1
            self.refresh()
            self.list.setCurrentRow(max(0, min(cur, len(self.passes) - 1)))
            self.select(self.list.currentRow())
            self._finish_history()
            self._toast("Order updated")


    def add(self):
        self._begin_history()
        self.commit_active()
        self.passes.append({
            "name": "New Render Pass",
            "image": "",
            "description": "",
            "slide_ms": 1200,
            "pause_ms": 800,
            "hold": 10,
            "final": False,
            "blend": "add",
            "transition": "wipe_angle",
            "wipe_angle": 180,
            "hidden": False,
            "opacity": 100,
        })
        self.refresh()
        self.list.setCurrentRow(len(self.passes) - 1)
        self.select(len(self.passes) - 1)
        self._finish_history()

    def dup(self):
        self._begin_history()
        self.commit_active()
        r = self.list.currentRow()
        if r < 0:
            return
        p = dict(self.passes[r])
        p["name"] = p.get("name", "Pass") + " Copy"
        self.passes.insert(r + 1, p)
        self.refresh()
        self.list.setCurrentRow(r + 1)
        self.select(r + 1)
        self._finish_history()

    def remove(self):
        self._begin_history()
        self.commit_active()
        r = self.list.currentRow()
        if r < 0 or not self.passes:
            return
        self.passes.pop(r)
        self._active_row = -1
        self.refresh()
        if self.passes:
            nr = min(r, len(self.passes) - 1)
            self.list.setCurrentRow(nr)
            self.select(nr)
        else:
            self.name.setText("")
            self.image.setText("")
            self.desc.setPlainText("")
            if hasattr(self, "preview"):
                self.preview.setText("No image")
                self.preview.setPixmap(QPixmap())

    def up(self):
        self._begin_history()
        self.commit_active()
        r = self.list.currentRow()
        if r > 0:
            self.passes[r - 1], self.passes[r] = self.passes[r], self.passes[r - 1]
            self._reload_list(select=r - 1)
        self._finish_history()

    def down(self):
        self._begin_history()
        self.commit_active()
        r = self.list.currentRow()
        if 0 <= r < len(self.passes) - 1:
            self.passes[r + 1], self.passes[r] = self.passes[r], self.passes[r + 1]
            self._reload_list(select=r + 1)
        self._finish_history()

    def _import_file(self, path: Path, layer_index: int = 0, channel_group: str | None = None, pass_name: str | None = None):
        """Copy/convert one image into assets/passes. Returns relative viewer path or None."""
        src = Path(path)
        ASSETS.mkdir(parents=True, exist_ok=True)
        stem = "".join(c if c.isalnum() or c in "._-" else "_" for c in src.stem)
        tag = channel_group or str(layer_index)
        tag_safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in str(tag))[:40]
        h = hashlib.md5(f"{src.resolve()}::{tag}".encode()).hexdigest()[:6]
        if src.suffix.lower() in (".exr", ".hdr", ".tif", ".tiff"):
            out_name = f"{stem}_{tag_safe}_{h}.png"
            dst = ASSETS / out_name
            convert_layer_to_web(src, dst, layer_index, channel_group=channel_group)
        else:
            out_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in src.name)
            dst = ASSETS / out_name
            shutil.copy2(src, dst)
        return "assets/passes/" + out_name

    def _pick_layers_if_needed(self, src: Path):
        """
        For EXR/HDR/TIFF return list of selected layer dicts.
        Non-EXR → single dummy layer.
        """
        if src.suffix.lower() not in (".exr", ".hdr", ".tif", ".tiff"):
            return [{"index": 0, "label": src.stem, "size": "?", "group": None}]
        try:
            layers = list_exr_layers(src)
        except Exception as e:
            QMessageBox.warning(self, "EXR layer list", f"Could not list layers (using default):\n\n{e}")
            return [{"index": 0, "label": src.stem, "size": "?", "group": None}]
        if len(layers) <= 1:
            L = layers[0] if layers else {"index": 0, "label": src.stem, "size": "?", "group": None}
            return [L]
        dlg = LayerPickDialog(layers, self, multi=True)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        selected = dlg.selected_layers()
        return selected or None

    def choose_image(self):
        r = self.list.currentRow()
        if r < 0:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Render Image", "",
            "Images (*.png *.jpg *.jpeg *.webp *.tif *.tiff *.exr *.hdr);;EXR/HDR (*.exr *.hdr);;All (*.*)"
        )
        if not path:
            return
        src = Path(path)
        selected = self._pick_layers_if_needed(src)
        if not selected:
            return
        try:
            # single-image UI: use first selection
            L = selected[0]
            value = self._import_file(
                src,
                int(L.get("index", 0)),
                channel_group=L.get("group"),
                pass_name=L.get("label"),
            )
        except Exception as e:
            QMessageBox.critical(self, "Import failed", str(e))
            return
        self.image.setText(value)
        self.commit_row(r if self._active_row < 0 else self._active_row)
        self._finish_history()
        self._toast(f"Image → {value}")

    def load_images_batch(self):
        self._begin_history()
        """Import many images; multi-layer EXR opens a pass picker."""
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Load images / EXR",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.tif *.tiff *.exr *.hdr);;EXR/HDR (*.exr *.hdr);;All (*.*)",
        )
        if not paths:
            return
        self.commit_active()
        added = 0
        errors = []
        for path in paths:
            src = Path(path)
            try:
                if src.suffix.lower() in (".exr", ".hdr", ".tif", ".tiff"):
                    selected = self._pick_layers_if_needed(src)
                    if not selected:
                        continue
                    for L in selected:
                        rel = self._import_file(
                            src,
                            int(L.get("index", 0)),
                            channel_group=L.get("group"),
                            pass_name=L.get("label"),
                        )
                        name = L.get("label") or L.get("group") or src.stem
                        soft = self._software_id() if hasattr(self, "_software_id") else "generic"
                        nice = guess_pass_name(name, soft)
                        self.passes.append({
                            "name": nice,
                            "image": rel,
                            "description": "",
                            "slide_ms": 1000,
                            "pause_ms": 600,
                            "hold": 10,
                            "final": False,
                            "blend": "add",
                            "transition": "wipe_angle",
                            "wipe_angle": 45,
                        })
                        added += 1
                else:
                    rel = self._import_file(src, 0)
                    soft = self._software_id() if hasattr(self, "_software_id") else "generic"
                    nice = guess_pass_name(src.name, soft)
                    self.passes.append({
                        "name": nice,
                        "image": rel,
                        "description": "",
                        "slide_ms": 1000,
                        "pause_ms": 600,
                        "hold": 10,
                        "final": False,
                        "blend": "normal",
                        "transition": "wipe_angle",
                        "wipe_angle": 45,
                    })
                    added += 1
            except Exception as e:
                errors.append(f"{src.name}: {e}")
        self.refresh()
        if self.passes:
            self.list.setCurrentRow(max(0, len(self.passes) - 1))
            self.select(self.list.currentRow())
        msg = f"Imported {added} pass(es)"
        if errors:
            msg += f" — {len(errors)} error(s)"
            QMessageBox.warning(self, "Load images", msg + "\n\n" + "\n".join(str(e)[:120] for e in errors[:8]))
        self._toast(msg)
        self._finish_history()


    def apply_look_to_all(self):
        """Apply only the checked global fields onto every pass."""
        if not self.passes:
            self._toast("No passes")
            return
        self._begin_history()
        self.commit_active()

        def _combo(c, default=""):
            v = c.currentData()
            if v is None:
                v = c.itemData(c.currentIndex())
            return v if v is not None else default

        applied = []
        for p in self.passes:
            if self.chk_all_blend.isChecked():
                p["blend"] = _combo(self.all_blend, "normal")
            if self.chk_all_transition.isChecked():
                p["transition"] = _combo(self.all_transition, "wipe_rl")
            if self.chk_all_angle.isChecked():
                p["wipe_angle"] = float(self.all_angle.value())
            if self.chk_all_slide.isChecked():
                p["slide_ms"] = int(self.all_slide.value() * 1000)
            if self.chk_all_pause.isChecked():
                p["pause_ms"] = int(self.all_pause.value() * 1000)

        if self.chk_all_blend.isChecked():
            applied.append("blend")
        if self.chk_all_transition.isChecked():
            applied.append("transition")
        if self.chk_all_angle.isChecked():
            applied.append("wipe angle")
        if self.chk_all_slide.isChecked():
            applied.append("duration")
        if self.chk_all_pause.isChecked():
            applied.append("pause")

        if not applied:
            QMessageBox.information(
                self,
                "Apply to all",
                "Check at least one setting (blend, transition, angle, duration, or pause).",
            )
            return

        r = self.list.currentRow()
        self.refresh()
        if r >= 0:
            self.list.setCurrentRow(r)
            self.select(r)
        self._toast(f"Applied {', '.join(applied)} → {len(self.passes)} passes")
        self._finish_history()


    def clear_all(self):
        self._begin_history()
        if not self.passes:
            return
        if QMessageBox.question(self, "Clear all", "Remove all passes from the list?") != QMessageBox.StandardButton.Yes:
            return
        self.passes = []
        self._active_row = -1
        self.refresh()
        self._finish_history()


    def pick_edge_color(self):
        cur = QColor(self.edge_color.text().strip() or "#ffffff")
        col = QColorDialog.getColor(cur, self, "Wipe edge color")
        if col.isValid():
            self.edge_color.setText(col.name())

    def choose_logo(self):

        path, _ = QFileDialog.getOpenFileName(self, "Studio logo", "", "Images (*.png *.jpg *.webp *.svg)")
        if not path:
            return
        src = Path(path)
        ASSETS.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in src.name)
        dst = ASSETS.parent / safe  # assets/
        try:
            shutil.copy2(src, dst)
        except Exception as e:
            QMessageBox.critical(self, "Logo", str(e))
            return
        self.logo.setText("assets/" + safe)
        self._toast("Logo → assets/" + safe)

    def _software_id(self):
        if hasattr(self, "software"):
            v = self.software.currentData()
            if v is None:
                v = self.software.itemData(self.software.currentIndex())
            return v or "generic"
        return "generic"


    def _deps_list(self):
        return [
            ("PySide6", "PySide6", True),
            ("numpy", "numpy", True),
            ("Pillow", "PIL", True),
            ("imageio", "imageio", True),
            ("OpenEXR", "OpenEXR", False),  # optional but recommended for channel groups
        ]

    def check_dependencies(self):
        lines = []
        for pip_name, mod_name, required in self._deps_list():
            mod = _try_import(mod_name if mod_name != "PIL" else "PIL")
            if mod_name == "PIL":
                mod = _try_import("PIL") or _try_import("PIL.Image")
            ok = mod is not None
            flag = "OK" if ok else ("MISSING (required)" if required else "missing (optional)")
            lines.append(f"  {pip_name}: {flag}")
        QMessageBox.information(self, "Package check", "Installed packages:\n\n" + "\n".join(lines))

    def install_dependencies(self):
        """Run pip install for required EXR / image packages."""
        req = BASE.parent / "requirements.txt"
        if not req.exists():
            req = Path(__file__).resolve().parent.parent / "requirements.txt"
        pkgs = "imageio numpy Pillow OpenEXR PySide6"
        reply = QMessageBox.question(
            self,
            "Install dependencies",
            "Install / update Python packages needed for EXR import?\n\n"
            f"  pip install {pkgs}\n\n"
            "A console window may open. Continue?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        import sys
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "imageio", "numpy", "Pillow", "OpenEXR", "PySide6"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            out = (r.stdout or "")[-1500:]
            err = (r.stderr or "")[-800:]
            if r.returncode == 0:
                QMessageBox.information(
                    self, "Install done",
                    "Packages installed successfully.\nRestart the editor if imports still fail.\n\n" + out[-600:],
                )
                self._toast("Dependencies installed")
            else:
                QMessageBox.warning(
                    self, "Install failed",
                    f"pip exited with code {r.returncode}.\n\n{err or out}\n\n"
                    "Or double-click install_deps.bat next to the editor.",
                )
        except Exception as e:
            QMessageBox.critical(self, "Install error", str(e))

    def open_requirements_file(self):
        candidates = [
            BASE.parent / "requirements.txt",
            Path(__file__).resolve().parent.parent / "requirements.txt",
            Path(__file__).resolve().parent / "requirements.txt",
        ]
        for p in candidates:
            if p.exists():
                try:
                    if sys.platform == "win32":
                        os.startfile(str(p))  # noqa: S606
                    else:
                        subprocess.Popen(["xdg-open", str(p)])
                    return
                except Exception:
                    pass
        QMessageBox.information(
            self, "requirements.txt",
            "Place requirements.txt next to the project root.\n"
            "Contents:\n\nPySide6\nnumpy\nPillow\nimageio\nOpenEXR\n",
        )

    def show_install_help(self):
        QMessageBox.information(
            self,
            "Install guide",
            "EXR import needs:\n\n"
            "  1. Double-click install_deps.bat\n"
            "     OR Tools → Install Python dependencies\n\n"
            "  2. Packages:\n"
            "     • PySide6 (UI)\n"
            "     • numpy, Pillow, imageio (EXR→PNG)\n"
            "     • OpenEXR (optional, channel groups)\n\n"
            "  3. ImageMagick is optional; multi-channel V-Ray EXR\n"
            "     works better with imageio/OpenEXR.\n",
        )

    def auto_name_aovs(self):
        self._begin_history()
        if not self.passes:
            self._toast("No passes")
            return
        self.commit_active()
        soft = self._software_id()
        # If generic, try detect from filenames
        if soft == "generic":
            names = [p.get("image") or p.get("name") or "" for p in self.passes]
            soft = detect_software_from_names(names)
            # sync UI
            idx = self.software.findData(soft)
            if idx >= 0:
                self.software.setCurrentIndex(idx)
        for p in self.passes:
            img = p.get("image") or ""
            src = img if img else p.get("name", "")
            if src:
                p["name"] = guess_pass_name(Path(src).name, soft)
        self.refresh()
        r = max(0, self.list.currentRow())
        self.select(r)
        self._toast(f"Named with {soft} rules ({len(self.passes)} passes)")
        self._finish_history()

    def apply_project_template(self):
        """Apply a presentation/timing style while preserving images and pass order."""
        template = self.project_template.currentText()
        if template == "Custom":
            self._toast("Choose a project template first")
            return
        self._begin_history()
        self.commit_active()
        for i, p in enumerate(self.passes):
            name = str(p.get("name", "")).lower()
            if template == "Basic Breakdown":
                p.update({"transition": "fade", "slide_ms": 900, "pause_ms": 600, "hold": 6})
                if any(k in name for k in ("ao", "ambient", "shadow")):
                    p["blend"] = "multiply"
                elif any(k in name for k in ("reflection", "specular", "glow", "emission")):
                    p["blend"] = "screen"
            elif template == "Cinematic Breakdown":
                p.update({"transition": "soft_wipe_angle", "slide_ms": 1400, "pause_ms": 900, "hold": 8})
                if any(k in name for k in ("ao", "ambient", "shadow")):
                    p["blend"] = "multiply"
                elif any(k in name for k in ("reflection", "specular", "emission", "glow")):
                    p["blend"] = "screen"
                else:
                    p["blend"] = p.get("blend") or "normal"
            elif template == "Technical AOV":
                p.update({"transition": "wipe_rl", "slide_ms": 800, "pause_ms": 500, "hold": 5})
                p["blend"] = "normal"
            elif template == "Product Visualization":
                p.update({"transition": "zoom_fade", "slide_ms": 1100, "pause_ms": 700, "hold": 7})
                if any(k in name for k in ("ao", "ambient", "shadow")):
                    p["blend"] = "multiply"
                elif any(k in name for k in ("reflection", "specular", "gloss", "highlight")):
                    p["blend"] = "screen"
            if i == len(self.passes) - 1:
                p["final"] = bool(p.get("final", True))
        self.refresh()
        r = max(0, self.list.currentRow()) if self.passes else -1
        if r >= 0: self.select(r)
        self._finish_history()
        self._toast(f"Applied template: {template}")

    def apply_smart_suggestions(self):
        """Apply conservative name-based compositing suggestions after confirmation."""
        if not self.passes:
            self._toast("No passes to analyze")
            return
        suggestions = []
        for i, p in enumerate(self.passes):
            n = str(p.get("name", "")).lower()
            blend = p.get("blend", "normal")
            trans = p.get("transition", "fade")
            if any(k in n for k in ("ao", "ambient occlusion", "shadow", "dirt", "cavity", "occlusion")):
                blend = "multiply"
            elif any(k in n for k in ("reflection", "specular", "gloss", "emission", "glow", "lighting", "light", "gi", "global illum", "self illum", "diffuse")):
                blend = "add"
            elif any(k in n for k in ("refraction", "sss", "subsurface", "coat", "sheen")):
                blend = "screen"
            elif any(k in n for k in ("zdepth", "z-depth", "normal", "crypto", "mask")):
                blend = "normal"
            if "beauty" in n or "final" in n:
                trans = "fade"
            elif any(k in n for k in ("ao", "shadow")):
                trans = "wipe_rl"
            elif any(k in n for k in ("reflection", "refraction")):
                trans = "soft_wipe_angle"
            if blend != p.get("blend") or trans != p.get("transition"):
                suggestions.append((i, blend, trans))
        if not suggestions:
            self._toast("No new suggestions found")
            return
        names = ", ".join(f"{self.passes[i].get('name','Pass')}: {b}/{t}" for i,b,t in suggestions[:6])
        if len(suggestions) > 6: names += f" … +{len(suggestions)-6} more"
        answer = QMessageBox.question(self, "Apply smart suggestions?", f"Suggested changes:\n\n{names}\n\nApply them?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._begin_history()
        for i, blend, trans in suggestions:
            self.passes[i]["blend"] = blend
            self.passes[i]["transition"] = trans
        self.refresh()
        r = max(0, self.list.currentRow()) if self.passes else -1
        if r >= 0: self.select(r)
        self._finish_history()
        self._toast(f"Applied {len(suggestions)} smart suggestions")

    def smart_sort(self):
        self._begin_history()
        if not self.passes:
            return
        self.commit_active()
        self.passes = smart_sort_passes(self.passes)
        self.refresh()
        self.list.setCurrentRow(0)
        self.select(0)
        self._finish_history()
        self._toast("Sorted to pipeline order (Beauty last)")

    def apply_beauty_rebuild(self):
        self._begin_history()
        """Reorder + blend + remove unwanted + mark final (preset-driven automation)."""
        if not self.passes:
            self._toast("No passes loaded")
            return
        self.commit_active()
        soft = self._software_id()
        if soft == "generic":
            names = [p.get("image") or p.get("name") or "" for p in self.passes]
            soft = detect_software_from_names(names)
            idx = self.software.findData(soft) if hasattr(self, "software") else -1
            if idx >= 0:
                self.software.setCurrentIndex(idx)
        if soft not in REBUILD_PRESETS:
            soft = "vray"
        include_util = False
        if hasattr(self, "include_utility"):
            include_util = self.include_utility.isChecked()
        include_ls = False
        if hasattr(self, "include_light_selects"):
            include_ls = self.include_light_selects.isChecked()
        include_bg = False
        if hasattr(self, "include_background"):
            include_bg = self.include_background.isChecked()

        # Dry-run preview
        preview_kept, preview_removed, summary = apply_rebuild_preset(
            [dict(p) for p in self.passes], soft,
            include_utility=include_util,
            include_light_selects=include_ls,
            include_background=include_bg,
        )
        preset = REBUILD_PRESETS[soft]
        lines = [
            f"{preset['label']}",
            "",
            preset.get("description", ""),
            "",
            f"KEEP ({len(preview_kept)}):",
        ]
        for s in summary:
            lines.append(f"  • {s}")
        if preview_removed:
            lines.append("")
            lines.append(f"REMOVE ({len(preview_removed)}):")
            for r in preview_removed[:40]:
                lines.append(f"  ✕ {r['name']} — {r['reason']}")
            if len(preview_removed) > 40:
                lines.append(f"  … +{len(preview_removed)-40} more")
        lines.append("")
        lines.append("Apply these changes to the pass list?")
        reply = QMessageBox.question(
            self,
            "Beauty rebuild — preview",
            "\n".join(lines),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            self._toast("Rebuild cancelled")
            return

        self.passes, removed, summary = apply_rebuild_preset(
            self.passes, soft,
            include_utility=include_util,
            include_light_selects=include_ls,
            include_background=include_bg,
        )
        self.refresh()
        self.list.setCurrentRow(0)
        self.select(0)
        self._finish_history()
        self._toast(
            f"{preset['label']}: {len(self.passes)} kept, {len(removed)} removed — SAVE when ready"
        )

    def export_mp4(self):
        """Build a simple slideshow MP4 from pass images via ffmpeg."""
        self.commit_active()
        imgs = []
        for p in self.passes:
            rel = p.get("image") or ""
            if not rel:
                continue
            fp = VIEWER / rel
            if fp.exists():
                imgs.append((fp, max(0.5, float(p.get("slide_ms", 1200)) / 1000 + float(p.get("pause_ms", 800)) / 1000)))
        if not imgs:
            QMessageBox.warning(self, "Export", "No images to export. Load passes first.")
            return
        out, _ = QFileDialog.getSaveFileName(self, "Export MP4", str(BASE / "breakdown.mp4"), "MP4 (*.mp4)")
        if not out:
            return
        # concat demuxer with durations
        lst = ASSETS / "_export_list.txt"
        lines = []
        for fp, dur in imgs:
            lines.append(f"file '{fp.resolve()}'")
            lines.append(f"duration {dur:.3f}")
        # last frame needs a file line again
        lines.append(f"file '{imgs[-1][0].resolve()}'")
        lst.write_text("\n".join(lines), encoding="utf8")
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-movflags", "+faststart", out,
        ]
        ffmpeg = _which("ffmpeg")
        if not ffmpeg:
            try:
                lst.unlink(missing_ok=True)
            except Exception:
                pass
            QMessageBox.warning(
                self,
                "FFmpeg not found",
                "MP4 export needs FFmpeg. The editor checks normal PATH first and then the imageio-ffmpeg bundled executable.\n\n"
                "Run install_deps.bat and try again."
            )
            return
        cmd[0] = ffmpeg
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except FileNotFoundError:
            QMessageBox.warning(self, "FFmpeg not found", "FFmpeg could not be started. Run install_deps.bat to install the bundled FFmpeg dependency and try again.")
            return
        except subprocess.TimeoutExpired:
            QMessageBox.warning(self, "Export timed out", "FFmpeg did not finish within 10 minutes. Check the source images and try again.")
            return
        finally:
            try:
                lst.unlink(missing_ok=True)
            except Exception:
                pass
        if r.returncode != 0:
            QMessageBox.critical(self, "Export failed", (r.stderr or r.stdout or "ffmpeg error")[-1200:])
            return
        self._toast(f"Exported → {out}")

    def _toast(self, msg: str):
        """Non-blocking status line instead of modal popups."""
        if hasattr(self, "status"):
            self.status.setText(msg)
        print(msg)

    def validate_project(self):
        """Return (errors, warnings) for the current project without modifying it."""
        errors = []
        warnings = []
        seen = {}
        valid_blends = {v for v, _ in BLEND_MODES}
        valid_transitions = {v for v, _ in TRANSITIONS}
        for i, p in enumerate(self.passes, 1):
            name = str(p.get("name", "")).strip()
            if not name:
                errors.append(f"Pass {i}: empty pass name")
            key = name.casefold()
            if key:
                seen.setdefault(key, []).append(i)
            image = str(p.get("image", "")).strip()
            if image and not self._resolve_image_path(image):
                warnings.append(f"Pass {i} ({name or 'Untitled'}): image not found — {image}")
            try:
                op = float(p.get("opacity", 100))
                if not 0 <= op <= 100:
                    errors.append(f"Pass {i} ({name or 'Untitled'}): opacity must be 0–100%")
            except Exception:
                errors.append(f"Pass {i} ({name or 'Untitled'}): invalid opacity")
            try:
                if float(p.get("slide_ms", 1200)) < 300:
                    errors.append(f"Pass {i} ({name or 'Untitled'}): transition duration is below 0.3 sec")
            except Exception:
                errors.append(f"Pass {i} ({name or 'Untitled'}): invalid transition duration")
            if str(p.get("blend", "normal")) not in valid_blends:
                errors.append(f"Pass {i} ({name or 'Untitled'}): unknown blend mode")
            if str(p.get("transition", "wipe_rl")) not in valid_transitions:
                errors.append(f"Pass {i} ({name or 'Untitled'}): unknown transition")
        for name, rows in seen.items():
            if len(rows) > 1:
                warnings.append(f"Duplicate pass name: {self.passes[rows[0]-1].get('name','Pass')} (rows {', '.join(map(str, rows))})")
        return errors, warnings

    def _autosave(self):
        """Write a lightweight recovery snapshot; never interrupts the editor."""
        try:
            self.commit_active()
            self._autosave_path.parent.mkdir(parents=True, exist_ok=True)
            snap = {
                "version": 1,
                "saved_at": __import__("time").time(),
                "title": self.title.text().strip() if hasattr(self, "title") else "Render Pass Breakdown",
                "passes": self.passes,
            }
            tmp = self._autosave_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(snap, indent=2, ensure_ascii=False), encoding="utf8")
            tmp.replace(self._autosave_path)
        except Exception as e:
            print("Autosave skipped:", e)

    def _check_autosave_recovery(self):
        """Offer recovery only when the autosave is newer than viewer/data.js."""
        try:
            if not self._autosave_path.exists():
                return
            data_mtime = DATA.stat().st_mtime if DATA.exists() else 0
            if self._autosave_path.stat().st_mtime <= data_mtime:
                return
            raw = json.loads(self._autosave_path.read_text(encoding="utf8"))
            recovered = raw.get("passes")
            if not isinstance(recovered, list) or not recovered:
                return
            answer = QMessageBox.question(
                self, "Recover Autosave",
                "A newer autosave was found.\n\nRecover the last editor state?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.passes = recovered
                if hasattr(self, "title"):
                    self.title.setText(str(raw.get("title", "Render Pass Breakdown")))
                self.refresh()
                self.list.setCurrentRow(0)
                self.select(0)
                self._toast("Recovered autosave")
        except Exception as e:
            print("Autosave recovery skipped:", e)

    def save(self):
        """Validate and atomically write the viewer data file."""
        try:
            self.commit_active()
            cr = self.list.currentRow()
            if cr >= 0:
                self.commit_row(cr)
            errors, warnings = self.validate_project()
            if errors:
                QMessageBox.warning(self, "Project validation failed", "\n".join("• " + e for e in errors))
                return False
            if warnings:
                self._toast(f"Saved with {len(warnings)} warning(s): check missing/duplicate pass data")
            ASSETS.mkdir(parents=True, exist_ok=True)
            title = json.dumps(self.title.text().strip() or "Render Pass Breakdown", ensure_ascii=False)
            payload = json.dumps(self.passes, indent=2, ensure_ascii=False)
            logo_rel = self.logo.text().strip() if hasattr(self, "logo") else ""
            bed_rel = ""
            if hasattr(self, "soundtrack"):
                bed_src = self.soundtrack.text().strip()
                if bed_src:
                    bp = Path(bed_src)
                    if bp.is_file():
                        try:
                            ASSETS.mkdir(parents=True, exist_ok=True)
                            dest = ASSETS.parent / bp.name  # viewer/assets/
                            if not dest.exists() or dest.stat().st_mtime < bp.stat().st_mtime:
                                shutil.copy2(bp, dest)
                            bed_rel = "assets/" + bp.name
                        except Exception:
                            bed_rel = bed_src
                    else:
                        bed_rel = bed_src
            def _chk(name, default=True):
                w = getattr(self, name, None)
                return bool(w.isChecked()) if w is not None else default
            settings = json.dumps({
                "logo": logo_rel,
                "soundtrack": bed_rel,
                "soundtrack_volume": 0.25,
                "edge_show": _chk("edge_show", True),
                "edge_color": (self.edge_color.text().strip() or "#ffffff") if hasattr(self, "edge_color") else "#ffffff",
                "edge_width": float(self.edge_width.value()) if hasattr(self, "edge_width") else 2,
                "edge_glow": _chk("edge_glow", True),
                "show_topbar": _chk("show_topbar", True),
                "show_brand": _chk("show_brand", True),
                "show_counter": _chk("show_counter", True),
                "show_pass_name": _chk("show_pass_name", True),
                "show_tags": _chk("show_tags", True),
                "show_timeline": _chk("show_timeline", True),
                "show_hint": _chk("show_hint", True),
                "show_caption": _chk("show_caption", True),
                "custom_presets": self.custom_presets,
            }, ensure_ascii=False)
            content = (
                "// Generated by Render Pass Breakdown Editor.\n"
                "window.PROJECT_TITLE = " + title + ";\n"
                "window.SETTINGS = " + settings + ";\n"
                "window.PASSES = " + payload + ";\n"
            )
            tmp = DATA.with_suffix(DATA.suffix + ".tmp")
            tmp.write_text(content, encoding="utf8")
            # Keep one previous known-good viewer data file.
            backup = DATA.with_suffix(DATA.suffix + ".bak")
            if DATA.exists():
                shutil.copy2(DATA, backup)
            tmp.replace(DATA)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", f"Could not write viewer/data.js:\n\n{e}")
            return False
        self._toast(f"Saved {len(self.passes)} pass(es) → viewer/data.js")
        # Keep shared library in sync so Showcase sees the same passes
        try:
            if pass_library is not None:
                pass_library.import_from_rpb_passes(self.passes)
        except Exception:
            pass
        # Notify host (Showcase Studio) to pull breakdown → project
        try:
            cb = getattr(self, "_on_saved_callback", None)
            if callable(cb):
                cb()
        except Exception:
            pass
        return True

    def closeEvent(self, event):
        try:
            self._autosave()
        except Exception:
            pass
        event.accept()



    # ----- Power features: drag-drop, batch timing, project bridge -----
    def _list_drag_enter(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def _list_drag_move(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def _list_drop_files(self, event):
        """Drop image files onto the pass list to import them."""
        urls = event.mimeData().urls() if event.mimeData() else []
        paths = []
        for u in urls or []:
            p = u.toLocalFile()
            if p and Path(p).is_file():
                paths.append(p)
        if paths:
            event.acceptProposedAction()
            self._import_image_paths(paths)
            return
        # fall back to internal reorder
        QListWidget.dropEvent(self.list, event)

    def _import_image_paths(self, paths):
        from pathlib import Path as _P
        exts = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".exr", ".hdr", ".bmp"}
        self._begin_history()
        added = 0
        for path in paths:
            p = _P(path)
            if p.suffix.lower() not in exts:
                continue
            name = p.stem.replace("_", " ").replace(".", " ")
            # Copy into viewer assets when possible
            try:
                ASSETS.mkdir(parents=True, exist_ok=True)
                dest = ASSETS / p.name
                if not dest.exists():
                    shutil.copy2(p, dest)
                image = str(dest)
            except Exception:
                image = str(p)
            self.passes.append({
                "name": name,
                "image": image,
                "description": "",
                "slide_ms": 1000,
                "pause_ms": 600,
                "hold": 8.0,
                "final": False,
                "blend": "normal",
                "transition": "wipe_rl",
                "wipe_angle": 180,
                "hidden": False,
                "opacity": 100.0,
            })
            added += 1
        self._finish_history()
        self.refresh()
        if added:
            self._toast(f"Imported {added} image(s) via drop")
            # auto smart blends for new names
            try:
                self.apply_smart_suggestions()
            except Exception:
                pass

    def batch_timing_dialog(self):
        if not self.passes:
            self._toast("No passes")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Batch timing — all passes")
        form = QFormLayout(dlg)
        slide = QDoubleSpinBox(); slide.setRange(0.2, 10); slide.setValue(1.0); slide.setSuffix(" s")
        pause = QDoubleSpinBox(); pause.setRange(0.0, 10); pause.setValue(0.6); pause.setSuffix(" s")
        hold = QDoubleSpinBox(); hold.setRange(1.0, 60); hold.setValue(8.0); hold.setSuffix(" s")
        only_final_hold = QCheckBox("Apply hold only to Final Beauty / last pass")
        only_final_hold.setChecked(True)
        form.addRow("Transition", slide)
        form.addRow("Pause", pause)
        form.addRow("Hold", hold)
        form.addRow(only_final_hold)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._begin_history()
        for i, p in enumerate(self.passes):
            p["slide_ms"] = int(slide.value() * 1000)
            p["pause_ms"] = int(pause.value() * 1000)
            is_final = bool(p.get("final")) or i == len(self.passes) - 1
            if only_final_hold.isChecked():
                if is_final:
                    p["hold"] = float(hold.value())
            else:
                p["hold"] = float(hold.value())
        self.refresh()
        r = max(0, self.list.currentRow()) if self.passes else -1
        if r >= 0:
            self.select(r)
        self._finish_history()
        self._toast("Batch timing applied to all passes")


    def open_rename_table(self):
        """Show optional rename table — user picks which suggestions to apply."""
        if not self.passes:
            self._toast("No passes")
            return
        try:
            from shared.pass_naming import build_rename_table
        except Exception:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from shared.pass_naming import build_rename_table

        rows = build_rename_table(self.passes)
        dlg = QDialog(self)
        dlg.setWindowTitle("Rename passes (optional review)")
        dlg.resize(720, 420)
        lay = QVBoxLayout(dlg)
        tip = QLabel(
            "Suggestions only clean engine prefixes and separators.\n"
            "They do NOT invent Key/Fill/Rim — check each name (e.g. kitchen light vs key light)."
        )
        tip.setWordWrap(True)
        lay.addWidget(tip)
        table = QTableWidget(len(rows), 3)
        table.setHorizontalHeaderLabels(["Use", "Current name", "Suggested name (editable)"])
        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(0, 48)
        table.setColumnWidth(1, 260)
        for r, row in enumerate(rows):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            # Pre-check only when suggestion differs
            if row["suggested"] != row["original"]:
                chk.setCheckState(Qt.CheckState.Checked)
            else:
                chk.setCheckState(Qt.CheckState.Unchecked)
            table.setItem(r, 0, chk)
            table.setItem(r, 1, QTableWidgetItem(row["original"]))
            table.setItem(r, 2, QTableWidgetItem(row["suggested"]))
        lay.addWidget(table, 1)
        btn_row = QHBoxLayout()
        b_all = QPushButton("Check all changed")
        b_none = QPushButton("Uncheck all")
        def check_changed():
            for r in range(table.rowCount()):
                a = table.item(r, 1).text()
                b = table.item(r, 2).text()
                table.item(r, 0).setCheckState(
                    Qt.CheckState.Checked if a != b else Qt.CheckState.Unchecked
                )
        b_all.clicked.connect(check_changed)
        b_none.clicked.connect(lambda: [
            table.item(r, 0).setCheckState(Qt.CheckState.Unchecked)
            for r in range(table.rowCount())
        ])
        btn_row.addWidget(b_all)
        btn_row.addWidget(b_none)
        btn_row.addStretch(1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        btn_row.addWidget(buttons)
        lay.addLayout(btn_row)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._begin_history()
        applied = 0
        for r in range(table.rowCount()):
            if table.item(r, 0).checkState() != Qt.CheckState.Checked:
                continue
            new_name = table.item(r, 2).text().strip()
            if not new_name:
                continue
            if r < len(self.passes):
                self.passes[r]["name"] = new_name
                applied += 1
        self.refresh()
        row = max(0, self.list.currentRow()) if self.passes else -1
        if row >= 0:
            self.select(row)
        self._finish_history()
        self._toast(f"Renamed {applied} pass(es)")

    def apply_shot_preset_dialog(self):
        try:
            from shared.pass_naming import SHOT_PRESETS, apply_shot_preset
        except Exception:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from shared.pass_naming import SHOT_PRESETS, apply_shot_preset
        if not self.passes:
            self._toast("No passes")
            return
        names = list(SHOT_PRESETS.keys())
        name, ok = QInputDialog.getItem(
            self, "Shot preset",
            "Apply blend/transition pack for:",
            names, 0, False,
        )
        if not ok or not name:
            return
        desc = SHOT_PRESETS[name].get("description", "")
        if QMessageBox.question(
            self, "Apply preset?",
            f"{name}\n\n{desc}\n\nApply to current pass stack?",
        ) != QMessageBox.StandardButton.Yes:
            return
        self._begin_history()
        self.commit_active()
        self.passes = apply_shot_preset(self.passes, name)
        self.refresh()
        row = max(0, self.list.currentRow()) if self.passes else -1
        if row >= 0:
            self.select(row)
        self._finish_history()
        self._toast(f"Applied shot preset: {name}")



    def _apply_pass_filter(self, text=""):
        q = (text or "").strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            if not item:
                continue
            if not q:
                item.setHidden(False)
                continue
            item.setHidden(q not in item.text().lower())

    def export_contact_sheet(self):
        """Export a simple contact sheet PNG of all pass images."""
        if not self.passes:
            self._toast("No passes")
            return
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            QMessageBox.warning(self, "Contact sheet", "Pillow is required:\npip install Pillow")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Contact sheet", str(BASE / "contact_sheet.png"), "PNG (*.png)"
        )
        if not path:
            return
        thumbs = []
        labels = []
        size = 256
        for p in self.passes:
            src = self._resolve_image_path(p.get("image") or "") if hasattr(self, "_resolve_image_path") else p.get("image")
            if not src:
                src = p.get("image") or ""
            im = None
            try:
                from pathlib import Path as _P
                fp = _P(src)
                if fp.is_file():
                    im = Image.open(fp).convert("RGB")
                    im.thumbnail((size, size))
            except Exception:
                im = None
            if im is None:
                im = Image.new("RGB", (size, size), (30, 34, 42))
            thumbs.append(im)
            labels.append(str(p.get("name") or "Pass")[:40])
        cols = min(4, max(1, len(thumbs)))
        rows = (len(thumbs) + cols - 1) // cols
        pad = 8
        label_h = 22
        cell_w, cell_h = size + pad, size + label_h + pad
        sheet = Image.new("RGB", (cols * cell_w + pad, rows * cell_h + pad), (12, 14, 18))
        draw = ImageDraw.Draw(sheet)
        for i, (im, lab) in enumerate(zip(thumbs, labels)):
            r, c = divmod(i, cols)
            x, y = pad + c * cell_w, pad + r * cell_h
            sheet.paste(im, (x, y))
            draw.text((x, y + size + 2), lab, fill=(220, 210, 180))
        sheet.save(path)
        self._toast(f"Contact sheet saved: {path}")
        QMessageBox.information(self, "Contact sheet", f"Saved:\n{path}")





    def relink_missing_passes(self):
        """Search asset folders by filename; manual pick for leftovers."""
        from pathlib import Path as _P
        roots = [
            ASSETS,
            VIEWER / "assets" / "passes",
            BASE / "shared" / "passes",
            BASE / "showcase" / "assets" / "images",
        ]
        index = {}
        for root in roots:
            if not getattr(root, "is_dir", lambda: False)():
                try:
                    if not root.is_dir():
                        continue
                except Exception:
                    continue
            try:
                for dirpath, _, files in os.walk(root):
                    for fn in files:
                        key = fn.lower()
                        if key not in index:
                            index[key] = str(_P(dirpath) / fn)
            except Exception:
                continue
        fixed = 0
        missing = []
        for i, p in enumerate(self.passes):
            img = p.get("image") or ""
            if not img:
                continue
            ok = False
            try:
                resolved = self._resolve_image_path(img) if hasattr(self, "_resolve_image_path") else None
                if resolved and _P(resolved).is_file():
                    ok = True
                elif _P(img).is_file():
                    ok = True
            except Exception:
                ok = False
            if ok:
                continue
            found = index.get(_P(img).name.lower())
            if found:
                p["image"] = found
                fixed += 1
            else:
                missing.append(i)
        for i in missing:
            p = self.passes[i]
            img = p.get("image") or ""
            path, _ok = QFileDialog.getOpenFileName(
                self, f"Locate pass: {p.get('name') or img}",
                str(ASSETS),
                "Images (*.png *.jpg *.jpeg *.webp *.exr *.tif *.tiff);;All (*.*)",
            )
            if path:
                p["image"] = path
                fixed += 1
        self.refresh()
        self._toast(f"Relinked {fixed} pass image(s)")
        QMessageBox.information(self, "Relink", f"Relinked {fixed} pass path(s).")


    def apply_host_theme(self, theme: str = "dark"):
        """Match Showcase Studio theme: dark | light | slate."""
        theme = (theme or "dark").lower()
        if theme == "light":
            bg, bg2, bg3 = "#faf9f7", "#ffffff", "#f5f3ef"
            text, text2, muted = "#0d0d0d", "#2a2a2a", "#6b6b6b"
            border, accent = "#e8e3d8", "#b8860b"
            hover, panel = "#f0ece2", "#ffffff"
            list_bg, item_sel = "#f5f3ef", "#f0e6c8"
        elif theme == "slate":
            bg, bg2, bg3 = "#1a1d24", "#22262f", "#2a303b"
            text, text2, muted = "#e8ecf1", "#c5ccd6", "#8b93a0"
            border, accent = "#3a4250", "#c9a227"
            hover, panel = "#2a303b", "#22262f"
            list_bg, item_sel = "#161a22", "#2a3344"
        else:
            bg, bg2, bg3 = "#0a0d12", "#121821", "#161e2c"
            text, text2, muted = "#e8ecf1", "#c5ccd6", "#9aa3b2"
            border, accent = "#3a4558", "#c9a227"
            hover, panel = "#1a2230", "#121821"
            list_bg, item_sel = "#0c1018", "#1a2436"

        self.setStyleSheet(f"""
        QMainWindow, QWidget {{
            background: {bg}; color: {text}; font-size: 12px;
            font-family: "Segoe UI", Inter, system-ui, sans-serif;
        }}
        QMenuBar {{
            background: {bg}; color: {text2}; border-bottom: 1px solid {border};
            padding: 3px 6px;
        }}
        QMenuBar::item {{ padding: 4px 10px; border-radius: 5px; }}
        QMenuBar::item:selected {{ background: {hover}; color: {text}; }}
        QMenu {{
            background: {bg2}; color: {text}; border: 1px solid {border}; padding: 6px;
            border-radius: 8px;
        }}
        QMenu::item {{ padding: 6px 16px; border-radius: 5px; }}
        QMenu::item:selected {{ background: {accent}; color: #0b0e14; }}
        QMenu::separator {{ height: 1px; background: {border}; margin: 4px 8px; }}
        QLineEdit, QTextEdit, QListWidget, QSpinBox, QDoubleSpinBox, QComboBox {{
            background: {bg2}; border: 1px solid {border}; border-radius: 7px;
            padding: 6px 8px; color: {text}; selection-background-color: {item_sel};
            min-height: 20px;
        }}
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1px solid {accent};
        }}
        QComboBox::drop-down {{
            border: none; width: 22px; background: {bg3};
            border-left: 1px solid {border};
            border-top-right-radius: 7px; border-bottom-right-radius: 7px;
        }}
        QComboBox::down-arrow {{
            width: 0; height: 0;
            border-left: 5px solid transparent; border-right: 5px solid transparent;
            border-top: 6px solid {accent}; margin-right: 6px;
        }}
        QComboBox QAbstractItemView {{
            background: {bg2}; color: {text};
            selection-background-color: {accent}; selection-color: #0b0e14;
            border: 1px solid {border}; border-radius: 6px; padding: 4px;
        }}
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
            background: {bg3}; border: none; width: 18px;
        }}
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
            border-left: 4px solid transparent; border-right: 4px solid transparent;
            border-bottom: 5px solid {accent}; width: 0; height: 0;
        }}
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
            border-left: 4px solid transparent; border-right: 4px solid transparent;
            border-top: 5px solid {accent}; width: 0; height: 0;
        }}
        QPushButton {{
            background: {bg3}; border: 1px solid {border}; border-radius: 7px;
            padding: 6px 11px; color: {text}; font-weight: 500;
        }}
        QPushButton:hover {{ background: {hover}; border-color: {accent}; }}
        QPushButton:pressed {{ background: {accent}; border-color: {accent}; color: #0b0e14; }}
        QPushButton:disabled {{ color: {muted}; border-color: {border}; background: {bg}; }}
        QListWidget {{
            outline: none; background: {list_bg}; border: 1px solid {border};
            border-radius: 9px; padding: 3px;
        }}
        QListWidget::item {{
            padding: 7px 10px; border-radius: 6px; margin: 1px 2px; color: {text2};
        }}
        QListWidget::item:selected {{
            background: {item_sel}; border-left: 3px solid {accent}; color: {text};
        }}
        QListWidget::item:hover:!selected {{ background: {hover}; }}
        QGroupBox {{
            border: 1px solid {border}; border-radius: 8px; margin-top: 10px;
            padding-top: 12px; color: {text2};
        }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 6px; color: {accent}; }}
        QCheckBox {{ color: {text}; spacing: 6px; }}
        QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {border}; border-radius: 3px; background: {bg2}; }}
        QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
        QScrollBar:vertical {{ background: {bg}; width: 10px; margin: 0; }}
        QScrollBar::handle:vertical {{ background: {border}; border-radius: 4px; min-height: 24px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QLabel {{ color: {text}; }}
        QStatusBar {{ background: {bg2}; color: {muted}; border-top: 1px solid {border}; }}
        QSplitter::handle {{ background: {border}; }}
        QToolTip {{
            background: {bg3}; color: {text}; border: 1px solid {border}; padding: 5px 8px;
        }}
        """)
        self._host_theme = theme


    def load_passes_list(self, passes: list, title: str = ""):
        """Replace current stack from an external list (Showcase bridge)."""
        self._begin_history()
        self.passes = [dict(p) for p in (passes or [])]
        if title and hasattr(self, "title"):
            try:
                self.title.setText(title)
            except Exception:
                pass
        self.refresh()
        if self.passes:
            self.list.setCurrentRow(0)
            self.select(0)
        self._finish_history()
        self._toast(f"Loaded {len(self.passes)} pass(es) from project")

    def get_passes_list(self) -> list:
        self.commit_active()
        cr = self.list.currentRow()
        if cr >= 0:
            self.commit_row(cr)
        return [dict(p) for p in self.passes]

    def set_project_context(self, key: str, title: str):
        self._project_key = key
        self._project_title = title
        if hasattr(self, "status") and self.status:
            self.status.setText(f"Project: {title}  ({key})")


    def push_passes_to_library(self):
        if pass_library is None:
            QMessageBox.warning(self, "Library", "Shared library module not available.")
            return
        self.commit()
        n = pass_library.import_from_rpb_passes(self.passes)
        self.status.setText(f"Saved {n} pass(es) to shared library")
        QMessageBox.information(self, "Library", f"Saved {n} pass(es) to the shared library.\nShowcase can load the same passes.")

    def pull_passes_from_library(self):
        if pass_library is None:
            QMessageBox.warning(self, "Library", "Shared library module not available.")
            return
        lib = pass_library.export_to_rpb_format()
        if not lib:
            QMessageBox.information(self, "Library", "Shared library is empty. Load images or save passes first.")
            return
        self._begin_history()
        # Merge by name: update existing, append new
        by_name = {str(p.get("name") or "").lower(): i for i, p in enumerate(self.passes)}
        added = 0
        updated = 0
        for item in lib:
            key = str(item.get("name") or "").lower()
            if key in by_name:
                i = by_name[key]
                self.passes[i].update(item)
                updated += 1
            else:
                self.passes.append(dict(item))
                added += 1
        self._finish_history()
        self.refresh()
        self.status.setText(f"Library: +{added} new, {updated} updated")

    def open(self):
        if not self.save():
            return
        index = (VIEWER / "index.html").resolve()
        if not index.is_file():
            QMessageBox.warning(self, "Open Viewer", f"Viewer file not found:\n{index}")
            return
        try:
            webbrowser.open(index.as_uri())
        except Exception as e:
            QMessageBox.warning(self, "Open Viewer", str(e))


def main():
    app = QApplication(sys.argv)
    try:
        app.setStyle("Fusion")
    except Exception:
        pass
    w = Editor()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
