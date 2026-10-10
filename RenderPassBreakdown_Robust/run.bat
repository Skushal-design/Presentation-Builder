@echo off
cd /d "%~dp0"
python studio.py
if errorlevel 1 (
  echo.
  echo If modules are missing, run install_deps.bat first.
  pause
)
