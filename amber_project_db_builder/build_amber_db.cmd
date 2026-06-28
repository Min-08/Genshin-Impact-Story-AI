@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 build_amber_db.py
) else (
  python build_amber_db.py
)
pause
