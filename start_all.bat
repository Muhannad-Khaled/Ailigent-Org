@echo off
echo ================================================
echo   Enterprise Agent System - Starting All
echo ================================================
echo.

echo Starting API Server...
start "API Server" cmd /k "cd /d %~dp0 && py -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 >nul

echo Starting Dashboard...
start "Dashboard" cmd /k "cd /d %~dp0\dashboard && npm run dev"
timeout /t 2 >nul

echo Starting Telegram Bot...
start "Telegram Bot" cmd /k "cd /d %~dp0 && py run_bot.py"

echo.
echo ================================================
echo   All services started!
echo ================================================
echo.
echo   API:       http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo   Dashboard: http://localhost:3000
echo   Telegram:  Send message to your bot
echo.
echo Close this window or press any key...
pause >nul
