@echo off
setlocal
cd /d "%~dp0"
python scripts\lore_chat.py --auto-start-llm %*
exit /b %ERRORLEVEL%
