@echo off
REM Startup script for Basketball Stats Tracker bundled application
REM This script helps handle common issues with bundled PyInstaller applications

REM Get directory of this script
set "DIR=%~dp0"

REM Make data directory if it doesn't exist
if not exist "%DIR%data" mkdir "%DIR%data"

REM Run the bundled application with any arguments passed to this script
"%DIR%basketball-stats.exe" %*
