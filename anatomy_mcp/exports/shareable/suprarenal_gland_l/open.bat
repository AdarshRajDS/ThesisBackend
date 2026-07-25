@echo off
cd /d "%~dp0"
echo Starting local viewer at http://127.0.0.1:5500/
echo Press Ctrl+C to stop.
start "" http://127.0.0.1:5500/
python -m http.server 5500
pause
