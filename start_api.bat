@echo off
echo Starting API Server on http://localhost:8000
echo Press Ctrl+C to stop
echo.
cd /d %~dp0
py -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
