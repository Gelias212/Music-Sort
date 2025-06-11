@echo off
title Music Library Organizer
echo Running Music Organizer...
echo.
echo Make sure to place this in your music library root folder
echo.

:: Set working directory to script location
cd /d "%~dp0"

:: Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo Please install Python from: https://www.python.org/downloads/
    echo Remember to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

:: Run the script with debug info
echo Current Directory: %cd%
echo.
python organize_music.py
pause