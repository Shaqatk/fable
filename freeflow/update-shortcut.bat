@echo off
REM Refresh the desktop shortcut icon (no reinstall needed).
cd /d "%~dp0"
set "FF_DIR=%~dp0"
set "FF_ICON=%FF_DIR%freeflow\assets\mic.ico,0"
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\FreeFlow.lnk'); $s.TargetPath = '%FF_DIR%.venv\Scripts\pythonw.exe'; $s.Arguments = '\"%FF_DIR%app.py\"'; $s.WorkingDirectory = '%FF_DIR%'; $s.IconLocation = '%FF_ICON%'; $s.Description = 'FreeFlow voice dictation'; $s.Save()"
echo Desktop shortcut updated.
pause
