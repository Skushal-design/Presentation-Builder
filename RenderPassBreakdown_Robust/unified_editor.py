#!/usr/bin/env python3
"""Compatibility launcher — use studio.py."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).resolve().parent / "studio.py"), run_name="__main__")
