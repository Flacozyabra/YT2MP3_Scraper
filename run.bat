@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Python virtual environment venv was not found in this folder.
    echo Please make sure the setup was completed successfully.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python yt2mp3_scraper.py

pause
