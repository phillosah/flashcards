@echo off
title FlashCards Web Server
cd /d "%~dp0"
echo Starting FlashCards on http://localhost:8000
echo Press Ctrl+C to stop.
echo.
start "" /b python server.py
timeout /t 2 /nobreak >nul
start "" http://localhost:8000
echo Server running. Close this window to stop.
pause >nul
