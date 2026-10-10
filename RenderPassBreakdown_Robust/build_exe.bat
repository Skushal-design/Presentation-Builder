@echo off
cd /d "%~dp0"
echo ============================================
echo  Render Pass Studio — Windows EXE builder
echo ============================================
echo.

python -c "import PyInstaller" 2>nul
if errorlevel 1 (
  echo Installing PyInstaller...
  python -m pip install --upgrade pyinstaller
)

echo.
echo Building studio.exe  (this can take several minutes)...
echo.

python -m PyInstaller --noconfirm --clean ^
  --name "RenderPassStudio" ^
  --windowed ^
  --onedir ^
  --collect-all PySide6 ^
  --collect-data imageio_ffmpeg ^
  --hidden-import PySide6.QtCore ^
  --hidden-import PySide6.QtGui ^
  --hidden-import PySide6.QtWidgets ^
  --hidden-import PIL ^
  --hidden-import numpy ^
  --hidden-import imageio ^
  --hidden-import OpenEXR ^
  --hidden-import Imath ^
  --add-data "showcase;showcase" ^
  --add-data "viewer;viewer" ^
  --add-data "editor;editor" ^
  --add-data "shared;shared" ^
  studio.py

if errorlevel 1 (
  echo.
  echo BUILD FAILED
  pause
  exit /b 1
)

echo.
echo ============================================
echo  DONE
echo ============================================
echo.
echo Output folder:
echo   dist\RenderPassStudio\
echo.
echo Run:
echo   dist\RenderPassStudio\RenderPassStudio.exe
echo.
echo You can zip the whole dist\RenderPassStudio folder and send it.
echo First run will still create any missing project files.
echo.
pause
