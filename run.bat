@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:: Change directory to where the script is located
cd /d "%~dp0"

echo ============================================================
echo   Запуск YouTube Music Downloader
echo ============================================================

:: Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo [Ошибка] Виртуальное окружение .venv не найдено.
    echo Пожалуйста, убедитесь, что вы запустили настройку проекта.
    pause
    exit /b 1
)

:: Activate virtual environment and run the script
call .venv\Scripts\activate.bat
python download_music.py

echo.
echo Программа завершила работу.
pause
