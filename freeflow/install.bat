@echo off
REM FreeFlow installer: creates a virtualenv, installs dependencies,
REM and puts a "FreeFlow" shortcut on your Desktop.
cd /d "%~dp0"
echo.
echo === FreeFlow setup ===
echo.
where python >nul 2>nul || (echo Python 3.10+ is required. Install it from python.org and re-run. & pause & exit /b 1)

if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv || (echo Failed to create venv & pause & exit /b 1)
)
echo Installing dependencies (this can take a few minutes)...
.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet || (echo Dependency install failed & pause & exit /b 1)

echo Creating desktop shortcut...
set "FF_DIR=%~dp0"
set "FF_ICON=%FF_DIR%freeflow\assets\mic.ico,0"
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\FreeFlow.lnk'); $s.TargetPath = '%FF_DIR%.venv\Scripts\pythonw.exe'; $s.Arguments = '\"%FF_DIR%app.py\"'; $s.WorkingDirectory = '%FF_DIR%'; $s.IconLocation = '%FF_ICON%'; $s.Description = 'FreeFlow voice dictation'; $s.Save()"

echo.
echo Done! Launch FreeFlow from the desktop shortcut (or run FreeFlow.bat).
echo The first dictation downloads the speech model (~150 MB) - give it a minute.
echo.
pause
