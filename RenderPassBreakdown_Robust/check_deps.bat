@echo off
cd /d "%~dp0"
echo Checking global Python packages for Render Pass Studio...
echo.
python -c "import sys; print(sys.executable); print(sys.version)"
echo.
python -c "import importlib; mods=['PySide6','numpy','PIL','imageio','imageio_ffmpeg'];
import sys
missing=[]
for m in mods:
  try:
    importlib.import_module(m)
    print('OK ', m)
  except Exception as e:
    print('MISS', m, '-', e)
    missing.append(m)
sys.exit(1 if missing else 0)"
if errorlevel 1 (
  echo.
  echo Some packages missing. Run install_deps.bat once.
) else (
  echo.
  echo All core packages available — project can run from any folder.
)
pause
