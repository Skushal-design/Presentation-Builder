@echo off
cd /d "%~dp0"
echo Building single-file EXE (slower start, one file)...
python -m pip install --upgrade pyinstaller >nul 2>&1
python -m PyInstaller --noconfirm --clean ^
  --name "RenderPassStudio" ^
  --windowed ^
  --onefile ^
  --collect-all PySide6 ^
  --collect-data imageio_ffmpeg ^
  --hidden-import PySide6.QtCore ^
  --hidden-import PySide6.QtGui ^
  --hidden-import PySide6.QtWidgets ^
  --add-data "showcase;showcase" ^
  --add-data "viewer;viewer" ^
  --add-data "editor;editor" ^
  --add-data "shared;shared" ^
  studio.py
echo.
echo Output: dist\RenderPassStudio.exe
pause
