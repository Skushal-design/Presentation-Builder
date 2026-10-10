"""Lightweight source smoke tests; no GUI/display required."""
from pathlib import Path
import ast
import json
import re

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "editor" / "editor.py"
VIEWER = ROOT / "viewer"

# Python syntax
ast.parse(EDITOR.read_text(encoding="utf-8"))

# JavaScript syntax is checked by Node when available; these checks cover project wiring.
html = (VIEWER / "index.html").read_text(encoding="utf-8")
assert 'src="data.js"' in html
assert 'src="app.js"' in html
assert 'href="style.css"' in html

js = (VIEWER / "app.js").read_text(encoding="utf-8")
data = (VIEWER / "data.js").read_text(encoding="utf-8")
assert "window.PASSES = " in data
assert "function showInstant" in js
assert "function runTransition" in js
assert "function waitImg" in js
assert "IMAGE NOT FOUND" in js
assert "function passOpacity" in js
assert "function passOpacityPct" in js
assert 'id="opacityTag"' in html
assert "targetOpacity" in js
assert "let committedStack = []" in js
assert "function rebuildCommittedThrough" in js
assert "function commitPass" in js
assert "commit the exact incoming pass as a permanent layer" in js
assert "applyBlend(blend, targetOpacity * 100)" in js
assert "mixBlendMode" in js
assert "resetTransitionLayer" in js

# Extract the JSON payload from the generated data.js.
start = data.index("window.PASSES = ") + len("window.PASSES = ")
end = data.index(";", start)
passes = json.loads(data[start:end])
assert isinstance(passes, list)
for p in passes:
    assert isinstance(p, dict)
    assert "name" in p and "image" in p
    assert 0 <= float(p.get("opacity", 100)) <= 100
    assert 0 <= float(p.get("wipe_angle", 180)) <= 360

editor = EDITOR.read_text(encoding="utf-8")
assert "def validate_project" in editor
assert "def _autosave" in editor
assert "def _check_autosave_recovery" in editor
assert "imageio_ffmpeg" in editor
assert "bundled FFmpeg" in editor
# Phase 2 editor UX: timeline, undo/redo, and keyboard workflow
assert "class TimelineWidget" in editor
assert "def undo" in editor and "def redo" in editor
assert "_undo_stack" in editor and "_redo_stack" in editor
assert "Ctrl+Z" in editor and "Ctrl+Y" in editor
assert "Alt+Up" in editor and "Alt+Down" in editor
assert "Timeline  ·  bottom = Pass 1  ·  top = latest pass" in editor
assert "editStarted = Signal(int)" in editor
assert "editFinished = Signal(int)" in editor
assert "reorderRequested = Signal(int, int)" in editor
assert "Ctrl+wheel = zoom" in editor
assert "Reset timing" in editor
assert "apply_project_template" in editor
assert "apply_smart_suggestions" in editor
assert "presentation" in js
assert "togglePresentation" in js
# Viewer already exposes the core playback keyboard workflow.
assert "ArrowRight" in js and "ArrowLeft" in js and "e.key === " "" in js
print(f"PASS: Python syntax, viewer wiring, opacity pipeline, validation/autosave, Phase 3 interactive reverse-stack timeline, undo/shortcuts, data JSON, and {len(passes)} pass records")
