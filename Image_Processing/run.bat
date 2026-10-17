@echo off
title Image Processing DAA Server
color 0A
echo ===================================================
echo   Starting Image Processing DAA Web Server...
echo ===================================================
echo.
cd /d "%~dp0"

echo Opening browser at http://127.0.0.1:5000 ...
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:5000

echo Running Flask server (press Ctrl+C to stop)...
py app.py

pause
