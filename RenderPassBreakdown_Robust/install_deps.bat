@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ================================================
echo  Render Pass Studio — Global dependency install
echo ================================================
echo.
echo  Installs into your GLOBAL Python (user site).
echo  After this once, you can run the Studio from any folder.
echo.
echo  Packages: PySide6, numpy, Pillow, imageio, imageio-ffmpeg, OpenEXR
echo.

REM Prefer "py -3" launcher on Windows, then python, then python3
set "PYEXE="
where py >nul 2>&1 && (
  py -3 -c "import sys; print(sys.executable)" >nul 2>&1 && set "PYEXE=py -3"
)
if not defined PYEXE (
  where python >nul 2>&1 && set "PYEXE=python"
)
if not defined PYEXE (
  where python3 >nul 2>&1 && set "PYEXE=python3"
)
if not defined PYEXE (
  echo ERROR: Python not found on PATH.
  echo Install Python 3.10+ from https://www.python.org/downloads/
  echo Check "Add python.exe to PATH" during setup.
  pause
  exit /b 1
)

echo Using: %PYEXE%
%PYEXE% -c "import sys; print(' ', sys.executable); print(' ', sys.version)"
echo.

REM Upgrade pip tooling (user scope when possible)
echo [1/3] Upgrading pip...
%PYEXE% -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
  echo Retrying pip upgrade with --user ...
  %PYEXE% -m pip install --user --upgrade pip setuptools wheel
)

echo.
echo [2/3] Installing requirements into global/user site...
echo      (skips packages already satisfied)
%PYEXE% -m pip install --user -r "%~dp0requirements.txt"
if errorlevel 1 (
  echo.
  echo --user install failed; trying without --user (admin/venv)...
  %PYEXE% -m pip install -r "%~dp0requirements.txt"
  if errorlevel 1 goto :fail
)

echo.
echo [3/3] Verifying imports...
%PYEXE% -c "import PySide6; print('  PySide6', getattr(PySide6,'__version__','ok'))"
if errorlevel 1 goto :fail
%PYEXE% -c "import numpy; print('  numpy', numpy.__version__)"
if errorlevel 1 goto :fail
%PYEXE% -c "import PIL; print('  Pillow ok')"
if errorlevel 1 goto :fail
%PYEXE% -c "import imageio; print('  imageio ok')"
if errorlevel 1 goto :fail
%PYEXE% -c "import imageio_ffmpeg; print('  FFmpeg', imageio_ffmpeg.get_ffmpeg_exe())"
if errorlevel 1 (
  echo   Warning: imageio-ffmpeg check failed — MP4 export may need a retry.
)
%PYEXE% -c "import OpenEXR; print('  OpenEXR ok')" 2>nul
if errorlevel 1 (
  echo   Note: OpenEXR optional — EXR import may be limited without it.
)

echo.
echo ================================================
echo  Install complete (global/user site).
echo.
echo  You can move this project folder anywhere.
echo  Run with:  run.bat   or   python studio.py
echo.
echo  Re-running this script is safe — already-installed
echo  packages are skipped.
echo ================================================
goto :done

:fail
echo.
echo ================================================
echo  Install FAILED. Read the messages above.
echo  Common fixes:
echo    - Reinstall Python with "Add to PATH"
echo    - Open "cmd" as normal user and retry
echo    - Or:  python -m pip install --user -r requirements.txt
echo ================================================
exit /b 1

:done
pause
endlocal
