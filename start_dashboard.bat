@echo off
echo Starting Dashboard on http://localhost:3000
echo Press Ctrl+C to stop
echo.
cd /d %~dp0\dashboard
npm run dev
