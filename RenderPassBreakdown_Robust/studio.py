#!/usr/bin/env python3
"""
Render Pass Studio — single entry point.

First run creates missing showcase, viewer, editor, shared files.
Works as source (python studio.py) or frozen Windows EXE (PyInstaller).

Usage:
  python studio.py
  python studio.py --init [folder]
  python studio.py --repair-tree
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _app_root() -> Path:
    """Folder that holds bundled showcase/ viewer/ shared/."""
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "showcase").is_dir():
            return exe_dir
        if (meipass / "showcase").is_dir():
            return meipass
        return exe_dir
    return Path(__file__).resolve().parent


ROOT = _app_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Writable location for user data (beside .exe when frozen)
STUDIO_DATA = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else ROOT


def _bootstrap(target: Path | None = None, source: Path | None = None) -> list[str]:
    from shared.studio_bootstrap import ensure_studio_tree
    return ensure_studio_tree(root=target or STUDIO_DATA, source_root=source or ROOT)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    if argv and argv[0] == "--init":
        target = Path(argv[1]).resolve() if len(argv) >= 2 else Path.cwd().resolve()
        target.mkdir(parents=True, exist_ok=True)
        created = _bootstrap(target, source=ROOT)
        print("Studio initialized at:", target)
        for p in created:
            print(" ", p)
        print("Run:  cd", target, "&& python studio.py")
        return 0

    if argv and argv[0] == "--repair-tree":
        created = _bootstrap(STUDIO_DATA, source=ROOT)
        print("Repaired missing files:")
        for p in created:
            print(" ", p)
        if not created:
            print(" (nothing missing)")
        return 0

    # Normal launch
    created = _bootstrap(STUDIO_DATA, source=ROOT)
    if created:
        print("Studio bootstrap created", len(created), "item(s)")

    editor = STUDIO_DATA / "showcase" / "editor.py"
    if not editor.is_file():
        editor = ROOT / "showcase" / "editor.py"
    if not editor.is_file():
        print("ERROR: showcase/editor.py missing after bootstrap.", file=sys.stderr)
        return 1

    # When frozen, BASE_DIR inside editor is showcase folder — ensure we run that file
    # but studio root for relative parent paths should be STUDIO_DATA
    os.environ["STUDIO_ROOT"] = str(STUDIO_DATA)
    if str(STUDIO_DATA) not in sys.path:
        sys.path.insert(0, str(STUDIO_DATA))

    import runpy
    sys.argv = [str(editor)] + [a for a in argv if a not in ("--init", "--repair-tree")]
    runpy.run_path(str(editor), run_name="__main__")
    return 0


def _excepthook(exc_type, exc, tb):
    try:
        import traceback
        log = STUDIO_DATA / "studio_log.txt"
        with open(log, "a", encoding="utf-8") as f:
            f.write("\n---\n")
            traceback.print_exception(exc_type, exc, tb, file=f)
        print("Error written to", log, file=sys.stderr)
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc, tb)


if __name__ == "__main__":
    sys.excepthook = _excepthook
    raise SystemExit(main())
