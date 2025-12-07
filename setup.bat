@echo off
echo ================================================
echo   Enterprise Agent System - Setup
echo ================================================
echo.

echo [1/2] Installing Python dependencies...
py -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Python dependencies
    pause
    exit /b 1
)
echo Python dependencies installed!
echo.

echo [2/2] Installing Dashboard dependencies...
cd dashboard
call npm install
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Dashboard dependencies
    pause
    exit /b 1
)
cd ..
echo Dashboard dependencies installed!
echo.

echo ================================================
echo   Setup Complete!
echo ================================================
echo.
echo You can now run:
echo   - start_all.bat    (Start everything)
echo   - start_api.bat    (API only)
echo   - start_dashboard.bat (Dashboard only)
echo   - start_bot.bat    (Telegram bot only)
echo.
pause
