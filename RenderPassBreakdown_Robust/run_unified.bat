@echo off
cd /d "%~dp0"
python showcase\editor.py
if errorlevel 1 pause
